import type { RequestHandler } from "express";

/**
 * Local-only guard for the legacy Express routes (Codex V0.3.1 counter-audit N10).
 *
 * Mirrors the Python API's LocalRequestGuard:
 *  - every /api request must target a loopback Host (blocks DNS-rebinding style access);
 *  - every mutation (anything but GET/HEAD/OPTIONS) must also come from a loopback Origin when one is sent,
 *    and carry `X-ATO-Request: 1` — a header a foreign web page cannot add to a "simple" cross-site request.
 * CORS alone is not a protection: a form POST from another site is executed even when its response is hidden.
 */
const LOOPBACK_HOST = /^(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$/i;
const LOOPBACK_ORIGIN = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$/i;
const SAFE = new Set(["GET", "HEAD", "OPTIONS"]);

export const localMutationGuard: RequestHandler = (req, res, next) => {
  if (!req.path.startsWith("/api/")) return next();
  const host = req.headers.host ?? "";
  if (!LOOPBACK_HOST.test(host)) {
    return res.status(403).json({ error: "Hôte non local refusé." });
  }
  if (SAFE.has(req.method)) return next();
  const origin = req.headers.origin;
  if (origin !== undefined && !LOOPBACK_ORIGIN.test(origin)) {
    return res.status(403).json({ error: "Origine non locale refusée." });
  }
  if (req.headers["x-ato-request"] !== "1") {
    return res.status(403).json({ error: "Mutation refusée : en-tête X-ATO-Request manquant." });
  }
  return next();
};
