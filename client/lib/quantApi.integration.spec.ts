/**
 * End-to-end contract test: TypeScript client → Vite dev server (proxy /api/v1, Express bypass)
 * → real FastAPI process → real Python engine. Uses a throw-away data directory and the
 * deterministic synthetic demo dataset (seed 42) — no broker, no network beyond 127.0.0.1.
 *
 * Skipped (with a visible reason) only if the Python environment `quant/.venv` is missing.
 */
import { spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { createServer as createNetServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { ViteDevServer } from "vite";
import { QuantApiError, createQuantClient, type QuantClient } from "./quantApi";

const ROOT = path.resolve(__dirname, "../..");
const PYTHON = path.join(ROOT, "quant", ".venv", "bin", "python");
const HAS_PYTHON = existsSync(PYTHON);
const BASELINE = "baseline.ema_trend_3bars@1.0.0";

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createNetServer();
    srv.once("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const port = (srv.address() as { port: number }).port;
      srv.close(() => resolve(port));
    });
  });
}

async function waitFor(url: string, timeoutMs = 30_000): Promise<void> {
  const start = Date.now();
  for (;;) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      /* not up yet */
    }
    if (Date.now() - start > timeoutMs) throw new Error(`timeout waiting for ${url}`);
    await new Promise((r) => setTimeout(r, 200));
  }
}

function csv(rows: Array<[string, number, number, number, number]>): Blob {
  const body = ["timestamp,open,high,low,close", ...rows.map((r) => r.join(","))].join("\n");
  return new Blob([body], { type: "text/csv" });
}

function minuteBars(n: number): Array<[string, number, number, number, number]> {
  const t0 = Date.parse("2026-09-07T12:00:00Z");
  return Array.from({ length: n }, (_, i) => {
    const p = 3900 + i * 0.01;
    return [new Date(t0 + i * 60_000).toISOString().replace(".000", ""), p, p + 0.2, p - 0.2, p];
  });
}

describe.skipIf(!HAS_PYTHON)("React client ↔ Vite proxy ↔ FastAPI ↔ Python engine", () => {
  let api: ChildProcess;
  let vite: ViteDevServer;
  let dataDir: string;
  let base: string;
  let client: QuantClient;

  beforeAll(async () => {
    dataDir = mkdtempSync(path.join(tmpdir(), "ato-int-"));
    const apiPort = await freePort();
    api = spawn(PYTHON, ["-m", "ai_trader_optimizer.api"], {
      cwd: path.join(ROOT, "quant"),
      env: { ...process.env, ATO_DATA_DIR: dataDir, ATO_API_PORT: String(apiPort), ATO_API_LOG_LEVEL: "warning" },
      stdio: "ignore",
    });
    await waitFor(`http://127.0.0.1:${apiPort}/api/v1/health`);

    process.env.QUANT_API_URL = `http://127.0.0.1:${apiPort}`;
    const { createServer } = await import("vite");
    const vitePort = await freePort();
    vite = await createServer({
      configFile: path.join(ROOT, "vite.config.ts"),
      server: { port: vitePort, strictPort: true, host: "127.0.0.1" },
      logLevel: "silent",
    });
    await vite.listen();
    base = `http://127.0.0.1:${vitePort}`;
    client = createQuantClient(base);
  }, 60_000);

  afterAll(async () => {
    await vite?.close();
    api?.kill();
    rmSync(dataDir, { recursive: true, force: true });
  });

  it("reaches the Python engine through the Vite proxy, simulation only", async () => {
    const h = await client.health();
    expect(h.execution_mode).toBe("simulation");
    expect(h.live_trading_enabled).toBe(false);
    expect(h.order_routes).toBe(0);
    // Express mock routes still answer (not broken by the proxy)
    expect((await fetch(`${base}/api/ping`)).status).toBe(200);
  });

  it("runs a full backtest from the client and gets consistent, persisted results", async () => {
    const demo = await client.createDemoDataset(42, 10);
    expect(demo.dataset.kind).toBe("synthetic");
    const again = await client.createDemoDataset(42, 10);
    expect(again.dataset.dataset_id).toBe(demo.dataset.dataset_id); // deterministic demo data

    const { strategies } = await client.listStrategies();
    expect(strategies.find((s) => s.key === BASELINE)?.runnable).toBe(true);
    expect(strategies.find((s) => s.key.startsWith("pilot."))?.runnable).toBe(false);

    const config = await client.getDefaults();
    config.initial_equity = 20_000;
    config.costs.spread = 0.35;
    const res = await client.runBacktest({ dataset_id: demo.dataset.dataset_id, strategy_key: BASELINE, config });
    const m = res.metrics;
    expect(res.manifest.config.initial_equity).toBe(20_000); // user parameters reached the engine
    expect(res.manifest.config.costs.spread).toBe(0.35);
    expect(m.initial_equity).toBe(20_000);
    expect(m.data_kind).toBe("synthetic");
    expect(m.trades).toBeGreaterThan(0);

    const trades = await client.getTrades(res.run_id);
    expect(trades).toHaveLength(m.trades);
    const sum = trades.reduce((s, t) => s + t.net_pnl, 0);
    expect(sum).toBeCloseTo(m.net_pnl, 6);
    expect(trades[trades.length - 1].equity_after).toBeCloseTo(m.final_equity, 6);
    const wins = trades.filter((t) => t.net_pnl > 0).length;
    expect((100 * wins) / trades.length).toBeCloseTo(m.win_rate_pct as number, 6);

    // risk rules held on every simulated trade
    const pct = config.risk.risk_per_trade_pct / 100;
    let equityBefore = config.initial_equity;
    for (const t of trades) {
      expect(t.planned_risk).toBeLessThanOrEqual(equityBefore * pct + 1e-9);
      equityBefore = t.equity_after;
    }

    const eq = await client.getEquity(res.run_id, 300);
    expect(eq.points[eq.points.length - 1].closed_equity).toBeCloseTo(m.final_equity, 6);

    const stored = await client.getBacktest(res.run_id);
    expect(stored.metrics).toEqual(m); // what is shown later = what was returned now

    const rep = await client.reproduce(res.run_id);
    expect(rep.identical).toBe(true);
    expect(rep.deterministic).toBe(true);
    expect(rep.artifacts_intact).toBe(true);
    expect(rep.stored_hash).toHaveLength(64);
    const same = await client.runBacktest({ dataset_id: demo.dataset.dataset_id, strategy_key: BASELINE, config });
    expect(same.run_id).toBe(res.run_id);
    expect(same.manifest.result_hash).toBe(res.manifest.result_hash);

    const exported = await (await fetch(client.exportUrl(res.run_id, "trades.csv"))).text();
    expect(exported.trim().split("\n")).toHaveLength(trades.length + 1);
  }, 60_000);

  it("rejects invalid user parameters without storing a fake result", async () => {
    const demo = await client.createDemoDataset(42, 10);
    const before = (await client.listBacktests()).length;
    const config = await client.getDefaults();
    config.strategy_params = { rr: 99 };
    await expect(
      client.runBacktest({ dataset_id: demo.dataset.dataset_id, strategy_key: BASELINE, config }),
    ).rejects.toMatchObject({ status: 422 });
    config.strategy_params = {};
    config.costs.spread = -1;
    const err = await client
      .runBacktest({ dataset_id: demo.dataset.dataset_id, strategy_key: BASELINE, config })
      .catch((e: unknown) => e);
    expect(err).toBeInstanceOf(QuantApiError);
    expect((err as QuantApiError).status).toBe(422);
    expect((await client.listBacktests()).length).toBe(before);
  });

  it("imports a valid CSV and refuses a corrupted one as a whole", async () => {
    const ok = await client.importDataset({
      file: csv(minuteBars(600)), filename: "xau.csv", name: "XAU test", symbol: "XAUUSD",
      source: "integration test", kind: "historical",
    });
    expect(ok.dataset.kind).toBe("historical");
    expect(ok.dataset.rows).toBe(600);

    const count = (await client.listDatasets()).length;
    const rows = minuteBars(50);
    rows[10][0] = rows[9][0]; // duplicated timestamp
    const caught: unknown = await client
      .importDataset({ file: csv(rows), filename: "bad.csv", name: "bad", symbol: "XAUUSD", source: "t", kind: "historical" })
      .then(() => null, (e: unknown) => e);
    expect(caught).toBeInstanceOf(QuantApiError);
    const err = caught as QuantApiError;
    expect(err.status).toBe(422);
    const issues = (err.detail as { issues: Array<{ code: string }> }).issues;
    expect(issues.some((i) => i.code === "DUPLICATED_TIMESTAMP")).toBe(true);
    expect((await client.listDatasets()).length).toBe(count);
  });

  it("refuses mutations from foreign origins or without the local header, writing nothing (I4)", async () => {
    const before = (await client.listDatasets()).length;
    const noHeader = await fetch(`${base}/api/v1/datasets/demo`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seed: 99 }),
    });
    expect(noHeader.status).toBe(403);
    const foreign = await fetch(`${base}/api/v1/datasets/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-ATO-Request": "1", Origin: "https://evil.example" },
      body: JSON.stringify({ seed: 98 }),
    });
    expect(foreign.status).toBe(403);
    expect((await client.listDatasets()).length).toBe(before);
  });

  it("exposes no way to send an order", async () => {
    // openapi.json is not proxied (only /api/v1 is): read it from the API process directly
    const direct = (await (await fetch(`${process.env.QUANT_API_URL}/openapi.json`)).json()) as {
      paths: Record<string, Record<string, unknown>>;
    };
    const paths = Object.keys(direct.paths);
    expect(paths.length).toBeGreaterThan(10);
    // Owner authorisation 2026-11-05: READ-ONLY access to the local MT5 terminal's report files. Exactly these
    // paths may mention mt5; every other mt5 path and any order / execute / position / broker / login path stays banned.
    const mt5ReadOnly = new Set(["/api/v1/mt5/local-files", "/api/v1/mt5/local-files/{file_id}/analyze",
      "/api/v1/external-sims/from-mt5/{file_id}"]);
    for (const p of paths) {
      expect(p).not.toMatch(/order|execute|position|broker|login/i);
      if (/mt5/i.test(p)) expect(mt5ReadOnly.has(p)).toBe(true);
    }
  });
});

if (!HAS_PYTHON) {
  console.warn(`[integration] SKIPPED: ${PYTHON} not found — run "cd quant && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'"`);
}
