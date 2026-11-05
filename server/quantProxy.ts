/**
 * Production relay /api/v1 -> Python quant API (I10). Streams the request and the response
 * untouched (no body parsing), so it must be mounted BEFORE express.json().
 * Only a loopback target is accepted: the engine is never reached over the network.
 */
import http from "node:http";
import type { RequestHandler } from "express";

const LOOPBACK = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

export function quantProxy(
  target: string = process.env.QUANT_API_URL ?? "http://127.0.0.1:8765",
): RequestHandler {
  const url = new URL(target);
  if (url.protocol !== "http:" || !LOOPBACK.has(url.hostname)) {
    throw new Error(`QUANT_API_URL doit être une adresse locale http (reçu ${target})`);
  }
  const hostname = url.hostname.replace(/^\[|\]$/g, "");
  return (req, res) => {
    const upstream = http.request(
      { hostname, port: url.port || 80, method: req.method, path: req.originalUrl, headers: req.headers },
      (up) => {
        res.writeHead(up.statusCode ?? 502, up.headers);
        up.pipe(res);
      },
    );
    upstream.on("error", () => {
      if (!res.headersSent) {
        res.status(502).json({
          error: "API Python injoignable. Lancez-la avec « pnpm quant:api ».",
          detail: null,
        });
      } else {
        res.end();
      }
    });
    req.pipe(upstream);
  };
}
