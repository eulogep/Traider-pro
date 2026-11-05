#!/usr/bin/env node
/**
 * Local production topology check (I10) — requires `pnpm build` first.
 *   Python API (temp data dir) + `node dist/server/node-build.mjs` (= pnpm start) on free local ports,
 *   then real HTTP calls through the production server: SPA, health, demo dataset, backtest, results,
 *   foreign-origin mutation refused. Nothing is deployed; everything listens on 127.0.0.1.
 * Usage: pnpm build && node e2e/production-smoke.mjs
 */
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { createServer as netServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PYTHON = path.join(ROOT, "quant", ".venv", "bin", "python");
const BUILD = path.join(ROOT, "dist", "server", "node-build.mjs");
const freePort = () => new Promise((res) => {
  const s = netServer();
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); });
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitHttp(url, ms = 30000) {
  const t0 = Date.now();
  for (;;) {
    try { if ((await fetch(url)).ok) return; } catch { /* retry */ }
    if (Date.now() - t0 > ms) throw new Error(`timeout ${url}`);
    await sleep(200);
  }
}
const results = [];
const check = (name, ok, info = "") => {
  results.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${info ? ` — ${info}` : ""}`);
};

if (!existsSync(BUILD)) {
  console.error("dist/server/node-build.mjs absent : lancez d'abord `pnpm build`.");
  process.exit(2);
}
const tmp = mkdtempSync(path.join(tmpdir(), "ato-prod-"));
const procs = [];
try {
  const [apiPort, webPort] = [await freePort(), await freePort()];
  procs.push(spawn(PYTHON, ["-m", "ai_trader_optimizer.api"], {
    cwd: path.join(ROOT, "quant"), stdio: "ignore",
    env: { ...process.env, ATO_DATA_DIR: path.join(tmp, "lab"), ATO_API_PORT: String(apiPort), ATO_API_LOG_LEVEL: "warning" },
  }));
  await waitHttp(`http://127.0.0.1:${apiPort}/api/v1/health`);
  procs.push(spawn(process.execPath, [BUILD], {
    cwd: ROOT, stdio: "ignore",
    env: { ...process.env, PORT: String(webPort), QUANT_API_URL: `http://127.0.0.1:${apiPort}` },
  }));
  const web = `http://localhost:${webPort}`;
  await waitHttp(`http://127.0.0.1:${webPort}/`);
  const origin = { Origin: web };
  const post = (p, body, extra = {}) => fetch(`${web}${p}`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-ATO-Request": "1", ...origin, ...extra },
    body: JSON.stringify(body),
  });

  check("built SPA served on /backtest", (await fetch(`${web}/backtest`)).status === 200);
  const h = await (await fetch(`${web}/api/v1/health`)).json();
  check("/api/v1/health relayed to Python", h.execution_mode === "simulation" && h.order_routes === 0, h.engine_version);
  const demo = await post("/api/v1/datasets/demo", { seed: 42, days: 5 });
  const ds = (await demo.json()).dataset;
  check("POST demo dataset through production server", demo.status === 201 && ds.kind === "synthetic");
  const bt = await post("/api/v1/backtests", { dataset_id: ds.dataset_id, strategy_key: "baseline.ema_trend_3bars@1.0.0" });
  const run = await bt.json();
  check("POST backtest through production server", bt.status === 201 && run.metrics.trades >= 0, `${run.metrics?.trades} trades`);
  const trades = await (await fetch(`${web}/api/v1/backtests/${run.run_id}/trades`)).json();
  check("results readable and consistent", trades.length === run.metrics.trades);
  const rep = await post(`/api/v1/backtests/${run.run_id}/reproduce`, {});
  const repBody = await rep.json();
  check("reproduce: deterministic and artefacts intact", repBody.deterministic && repBody.artifacts_intact);
  const evil = await post("/api/v1/datasets/demo", { seed: 7 }, { Origin: "https://evil.example" });
  check("foreign-origin mutation refused (403)", evil.status === 403);
  const noHeader = await fetch(`${web}/api/v1/datasets/demo`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  check("mutation without X-ATO-Request refused (403)", noHeader.status === 403);
  check("Express mock routes still served", (await fetch(`${web}/api/ping`)).status === 200);
} catch (e) {
  check("production smoke completed", false, String(e));
} finally {
  for (const p of procs) p.kill();
  await sleep(300);
  rmSync(tmp, { recursive: true, force: true });
}
const failed = results.filter((ok) => !ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
