#!/usr/bin/env node
/**
 * Browser user journey (real Chrome, headless, Chrome DevTools Protocol — no extra dependency):
 *   empty state → "Générer la démo synthétique" → "Lancer le backtest" → results visible
 *   → displayed KPIs equal the API's metrics → "Reproduire" → identical.
 *
 * Starts its own Python API (temporary data dir) + Vite dev server on free local ports.
 * Usage:  node e2e/backtest-flow.mjs [--screenshot out.png] [--tabs-dir DIR] [--api-down]
 *   --tabs-dir: also capture one screenshot per results tab (performance, trades, rejections, trace).
 *   --api-down: do not start the Python API and check the page shows an explicit offline state, no figures.
 * Env:    CHROME=/path/to/chrome (default: macOS Google Chrome)
 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { createServer as netServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PYTHON = path.join(ROOT, "quant", ".venv", "bin", "python");
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const shotArg = process.argv.indexOf("--screenshot");
const SHOT = shotArg > 0 ? process.argv[shotArg + 1] : null;
const API_DOWN = process.argv.includes("--api-down");
const tabsArg = process.argv.indexOf("--tabs-dir");
const TABS_DIR = tabsArg > 0 ? process.argv[tabsArg + 1] : null;

const freePort = () =>
  new Promise((res) => {
    const s = netServer();
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => res(p));
    });
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

const tmp = mkdtempSync(path.join(tmpdir(), "ato-e2e-"));
const procs = [];
const cleanup = async () => {
  for (const p of procs) p.kill();
  await sleep(800); // let Chrome release its profile before deleting the temp dir
  try { rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 }); } catch { /* temp dir only */ }
};
const results = [];
const check = (name, ok, info = "") => {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${info ? ` — ${info}` : ""}`);
};

try {
  const [apiPort, vitePort, cdpPort] = [await freePort(), await freePort(), await freePort()];
  if (!API_DOWN) {
    procs.push(spawn(PYTHON, ["-m", "ai_trader_optimizer.api"], {
      cwd: path.join(ROOT, "quant"), stdio: "ignore",
      env: { ...process.env, ATO_DATA_DIR: path.join(tmp, "lab"), ATO_API_PORT: String(apiPort), ATO_API_LOG_LEVEL: "warning" },
    }));
    await waitHttp(`http://127.0.0.1:${apiPort}/api/v1/health`);
  }
  procs.push(spawn(path.join(ROOT, "node_modules", ".bin", "vite"), ["--port", String(vitePort), "--strictPort", "--host", "127.0.0.1"], {
    cwd: ROOT, stdio: "ignore", env: { ...process.env, QUANT_API_URL: `http://127.0.0.1:${apiPort}` },
  }));
  const app = `http://127.0.0.1:${vitePort}`;
  await waitHttp(`${app}/`);
  procs.push(spawn(CHROME, ["--headless=new", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${path.join(tmp, "chrome")}`,
    "--no-first-run", "--no-default-browser-check", "--window-size=1400,2200", "about:blank"], { stdio: "ignore" }));
  await waitHttp(`http://127.0.0.1:${cdpPort}/json/version`);
  const pages = await (await fetch(`http://127.0.0.1:${cdpPort}/json/list`)).json();
  const ws = new WebSocket(pages.find((p) => p.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let seq = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  });
  const cdp = (method, params = {}) => new Promise((res, rej) => {
    const id = ++seq;
    pending.set(id, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
  const js = async (expr) => (await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.value;
  const waitSel = async (sel, ms = 30000) => {
    const t0 = Date.now();
    while (!(await js(`!!document.querySelector(${JSON.stringify(sel)})`))) {
      if (Date.now() - t0 > ms) throw new Error(`timeout waiting for ${sel}`);
      await sleep(150);
    }
  };
  const text = (sel) => js(`document.querySelector(${JSON.stringify(sel)})?.innerText ?? null`);
  const click = (sel) => js(`(() => { const b = document.querySelector(${JSON.stringify(sel)}); if (!b || b.disabled) return false; b.click(); return true; })()`);
  const consoleErrors = [];
  await cdp("Runtime.enable");
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.method === "Runtime.exceptionThrown") consoleErrors.push(m.params.exceptionDetails.text);
  });

  await cdp("Page.enable");
  await cdp("Page.navigate", { url: `${app}/backtest` });
  await waitSel('[data-testid="engine-status"]');
  if (API_DOWN) {
    await waitSel('[data-testid="api-offline"]');
    check("offline API → explicit offline state", true);
    check("offline API → no KPI, no results, no run button action",
      !(await js(`!!document.querySelector('[data-testid^="kpi-"], [data-testid="results"]')`)) &&
      (await js(`document.querySelector('[data-testid="run-backtest"]').disabled`)));
    check("offline API → status says offline", (await text('[data-testid="engine-status"]')).includes("hors ligne"));
    await cdp("Page.navigate", { url: `${app}/bot-analysis` });
    await waitSel('[data-testid="api-offline-notice"]');
    check("offline API → Bot Analysis says offline, shows no simulation and no import form",
      !(await js(`!!document.querySelector('[data-testid="simulation-view"], [data-testid="bot-file"]')`)));
    throw new Error("__done__");
  }
  await waitSel('[data-testid="no-dataset"]');
  check("empty lab shows an explicit empty state (no fake figures)", !!(await text('[data-testid="no-run"]')));
  check("engine status comes from the Python API", /Moteur backtest-engine\/.+simulation/.test(await text('[data-testid="engine-status"]')));

  check("click « Générer la démo synthétique »", await click('[data-testid="create-demo"]'));
  await waitSel('[data-testid="dataset-select"]');
  await waitSel('[data-testid="strategy-select"]');
  await sleep(300);
  check("click « Lancer le backtest »", await click('[data-testid="run-backtest"]'));
  await waitSel('[data-testid="results"]', 60000);
  await waitSel('.recharts-line', 30000); // "Performance" tab is the default view
  check("equity curve rendered", true);
  check("drawdown chart rendered (engine series)", await js(`!!document.querySelector('.recharts-area')`));
  check("R-per-trade chart rendered", await js(`!!document.querySelector('.recharts-bar-rectangle')`));

  const runId = await text('[data-testid="run-id"]');
  const api = await (await fetch(`http://127.0.0.1:${apiPort}/api/v1/backtests/${runId}`)).json();
  const m = api.metrics;
  const fr = (v, d) => v.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const kpi = async (id) => (await text(`[data-testid="${id}"]`)).replace(/\s+/g, " ");
  check("synthetic results are flagged", !!(await text('[data-testid="synthetic-warning"]')));
  check("trades KPI = API metrics.trades", (await kpi("kpi-trades")).toLowerCase().includes(`transactions ${m.trades}`), `${m.trades}`);
  const nbsp = (s) => s.replace(/[  ]/g, " ");
  check("net P&L KPI = API metrics.net_pnl", nbsp(await kpi("kpi-pnl")).includes(nbsp(fr(Math.abs(m.net_pnl), 2))), `${m.net_pnl}`);
  check("win rate KPI = API metrics.win_rate_pct", nbsp(await kpi("kpi-winrate")).includes(nbsp(fr(m.win_rate_pct, 1))), `${m.win_rate_pct}`);
  check("profit factor KPI = API metrics.profit_factor", nbsp(await kpi("kpi-pf")).includes(nbsp(fr(m.profit_factor, 2))), `${m.profit_factor}`);
  check("drawdown KPI = API metrics.max_dd_mtm_pct", nbsp(await kpi("kpi-dd")).includes(nbsp(fr(m.max_dd_mtm_pct, 2))), `${m.max_dd_mtm_pct}`);
  // open the "Transactions" tab like a user (Radix tabs activate on mousedown / focus)
  await js(`(() => { const t = document.querySelector('[data-testid="tab-trades"]');
    t.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0 })); t.focus(); })()`);
  await waitSel('[data-testid="trades-table"]', 15000);
  const rows = await js(`document.querySelectorAll('[data-testid="trades-table"] tbody tr').length`);
  check("trade journal rendered", rows === Math.min(25, m.trades), `${rows} lignes`);
  check("result hash shown = API", (await text('[data-testid="result-hash"]')) === api.manifest.result_hash);

  check("click « Reproduire »", await click('[data-testid="reproduce"]'));
  await waitSel('[data-testid="reproduce-result"]');
  const verdict = await text('[data-testid="reproduce-result"]');
  check("reproduction identical, artefacts intact, deterministic",
    verdict.startsWith("Résultats identiques") && verdict.includes("intacts") && verdict.includes("déterministe"));
  check("risk policy shown as research hypotheses (not an enforced policy)",
    (await text('[data-testid="risk-summary"]')).includes("mode recherche"));

  // M1: a second run must not inherit the first run's UI state (reproduction verdict, pagination)
  await js(`(() => { const el = document.getElementById('param-rr');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, '2');
    el.dispatchEvent(new Event('input', { bubbles: true })); })()`);
  await sleep(200);
  check("click « Lancer le backtest » (2nd run, rr = 2)", await click('[data-testid="run-backtest"]'));
  const t0 = Date.now();
  while ((await text('[data-testid="run-id"]')) === runId && Date.now() - t0 < 30000) await sleep(150);
  const runId2 = await text('[data-testid="run-id"]');
  check("second run displayed", runId2 && runId2 !== runId, runId2);
  check("previous reproduction verdict not carried over (M1)", !(await js(`!!document.querySelector('[data-testid="reproduce-result"]')`)));
  // the collection is now verified run by run (N1): wait for the refreshed list instead of reading it mid-refresh
  let runList = "";
  for (const t1 = Date.now(); Date.now() - t1 < 15000; await sleep(200)) {
    runList = await js(`document.querySelector('[data-testid="run-select"]')?.innerText ?? ""`);
    if (/USD/.test(runList)) break;
  }
  check("run list amounts carry their currency (M2)", /USD/.test(runList), runList.replace(/\s+/g, " ").slice(0, 80));
  check("no uncaught browser exception", consoleErrors.length === 0, consoleErrors.join(" | "));

  if (TABS_DIR) {
    for (const tab of ["performance", "trades", "rejections", "trace"]) {
      await js(`(() => { const t = document.querySelector('[data-testid="tab-${tab}"]');
        t.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0 })); t.focus(); })()`);
      await sleep(600);
      const { data } = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
      writeFileSync(path.join(TABS_DIR, `tab-${tab}.png`), Buffer.from(data, "base64"));
    }
    console.log(`tab screenshots: ${TABS_DIR}`);
  }
  if (SHOT) {
    const { data } = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    writeFileSync(SHOT, Buffer.from(data, "base64"));
    console.log(`screenshot: ${SHOT}`);
  }
  ws.close();
} catch (e) {
  if (String(e) !== "Error: __done__") check("journey completed", false, String(e));
} finally {
  await cleanup();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
