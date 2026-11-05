#!/usr/bin/env node
/**
 * Tour of every page (real Chrome, headless, Chrome DevTools Protocol — no extra dependency).
 *
 * Seeds its own Python API (temporary data dir) with one synthetic dataset and one backtest, then checks that:
 *   - each page renders its engine-backed content and the figures equal the API's;
 *   - no page shows the old invented figures, asks for a password or offers a trading switch;
 *   - each page fits a phone width (no horizontal scroll) and throws no browser exception.
 * Usage:  node e2e/pages-tour.mjs [--shots-dir DIR]
 * Env:    CHROME=/path/to/chrome (default: macOS Google Chrome)
 */
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer as netServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PYTHON = path.join(ROOT, "quant", ".venv", "bin", "python");
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const shotsArg = process.argv.indexOf("--shots-dir");
const SHOTS = shotsArg > 0 ? process.argv[shotsArg + 1] : null;

/** Texts of the former demo pages that must never come back (invented figures, fake connectivity). */
const FORBIDDEN = ["78.4%", "82.3%", "XGBoost", "temps réel", "Emergency Stop", "Connected", "+$", "prêts à passer en réel"];

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

const tmp = mkdtempSync(path.join(tmpdir(), "ato-tour-"));
const procs = [];
const cleanup = async () => {
  for (const p of procs) p.kill();
  await sleep(800);
  try { rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 }); } catch { /* temp dir only */ }
};
const results = [];
const check = (name, ok, info = "") => {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${info ? ` — ${info}` : ""}`);
};

try {
  const [apiPort, vitePort, cdpPort] = [await freePort(), await freePort(), await freePort()];
  procs.push(spawn(PYTHON, ["-m", "ai_trader_optimizer.api"], {
    cwd: path.join(ROOT, "quant"), stdio: "ignore",
    env: { ...process.env, ATO_DATA_DIR: path.join(tmp, "lab"), ATO_API_PORT: String(apiPort), ATO_API_LOG_LEVEL: "warning",
      ATO_MT5_DIR: path.join(tmp, "no-mt5-terminal") }, // hermetic: never reads the owner's real MT5 folder
  }));
  const api = `http://127.0.0.1:${apiPort}/api/v1`;
  await waitHttp(`${api}/health`);
  const post = async (p, body) => {
    const r = await fetch(`${api}${p}`, { method: "POST", headers: { "Content-Type": "application/json", "X-ATO-Request": "1" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`${p} → ${r.status} ${await r.text()}`);
    return r.json();
  };
  const demo = await post("/datasets/demo", { seed: 42, days: 60 }); // long enough for an out-of-sample study
  const strategies = (await (await fetch(`${api}/strategies`)).json()).strategies;
  const runnable = strategies.find((s) => s.runnable);
  const run = await post("/backtests", { dataset_id: demo.dataset.dataset_id, strategy_key: runnable.key });
  const health = await (await fetch(`${api}/health`)).json();
  const runs = await (await fetch(`${api}/backtests`)).json();

  procs.push(spawn(path.join(ROOT, "node_modules", ".bin", "vite"), ["--port", String(vitePort), "--strictPort", "--host", "127.0.0.1"], {
    cwd: ROOT, stdio: "ignore", env: { ...process.env, QUANT_API_URL: `http://127.0.0.1:${apiPort}` },
  }));
  const app = `http://127.0.0.1:${vitePort}`;
  await waitHttp(`${app}/`);
  procs.push(spawn(CHROME, ["--headless=new", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${path.join(tmp, "chrome")}`,
    "--no-first-run", "--no-default-browser-check", "--window-size=1400,1800", "about:blank"], { stdio: "ignore" }));
  await waitHttp(`http://127.0.0.1:${cdpPort}/json/version`);
  const pages = await (await fetch(`http://127.0.0.1:${cdpPort}/json/list`)).json();
  const ws = new WebSocket(pages.find((p) => p.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let seq = 0;
  const pending = new Map();
  const consoleErrors = [];
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === "Runtime.exceptionThrown") consoleErrors.push(msg.params.exceptionDetails.text);
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error")
      consoleErrors.push(msg.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300));
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
  const nbsp = (s) => (s ?? "").replace(/[  ]/g, " ").replace(/\s+/g, " ");
  const fr = (v, d) => v.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const shot = async (name) => {
    if (!SHOTS) return;
    const { data } = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    writeFileSync(path.join(SHOTS, `${name}.png`), Buffer.from(data, "base64"));
  };
  await cdp("Runtime.enable");
  await cdp("Page.enable");

  const visit = async (route, ready) => {
    await cdp("Page.navigate", { url: `${app}${route}` });
    await waitSel(ready);
    await sleep(500);
  };
  const generic = async (label) => {
    const body = await js("document.body.innerText");
    const found = FORBIDDEN.filter((f) => body.includes(f));
    check(`${label}: no invented figure / fake connectivity`, found.length === 0, found.join(", "));
    check(`${label}: no password field, no trading switch`,
      await js(`!document.querySelector('input[type=password], [role=switch]')`));
  };

  // ---- home
  await visit("/", '[data-testid="home-lab-state"] dl');
  await generic("home");
  const lab = nbsp(await text('[data-testid="home-lab-state"]'));
  check("home: lab state = API (1 dataset, 1 run)", /^.*\b1 Jeux de données 1 Backtests enregistrés/.test(lab), lab.slice(0, 90));
  check("home: sidebar shows the real engine status", (await text('[data-testid="shell-engine-status"]')).includes("en ligne"));
  await shot("home");

  // ---- dashboard
  await visit("/dashboard", '[data-testid="runs-table"]');
  await generic("dashboard");
  check("dashboard: one row per stored run", (await js(`document.querySelectorAll('[data-testid="runs-table"] tbody tr').length`)) === runs.length);
  check("dashboard: last P&L tile = API run net_pnl",
    nbsp(await text('[data-testid="dash-last-pnl"]')).includes(nbsp(fr(Math.abs(runs[0].net_pnl), 2))), `${runs[0].net_pnl}`);
  check("dashboard: synthetic-only runs are flagged", !!(await text('[data-testid="dash-synthetic-only"]')));
  await waitSel(".recharts-line", 15000);
  check("dashboard: equity chart rendered", true);
  await shot("dashboard");
  await js(`document.querySelector('[data-testid="runs-table"] tbody tr').click()`);
  await waitSel('[data-testid="run-id"]');
  check("dashboard → run row opens that run in Backtests", (await text('[data-testid="run-id"]')) === run.run_id && (await js("location.pathname")) === "/backtest");

  // ---- robustness tab of the run
  await js(`(() => { const t = document.querySelector('[data-testid="tab-robustness"]');
    t.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0 })); t.focus(); })()`);
  await waitSel('[data-testid="robustness"]', 20000);
  const rob = await (await fetch(`${api}/backtests/${run.run_id}/robustness`)).json();
  check("backtest: robustness tab = API bootstrap", nbsp(await text('[data-testid="robustness"]')).includes(nbsp(fr(Math.abs(rob.expectancy_r.value), 3))),
    `${rob.expectancy_r.value}`);

  // ---- validation (edge study launched from the UI)
  await visit("/research", '[data-testid="run-study"]');
  await generic("validation");
  await js(`document.querySelector('[data-testid="run-study"]').click()`);
  await waitSel('[data-testid="study-verdict"]', 90000);
  const sid = await text('[data-testid="study-id"]');
  const st = await (await fetch(`${api}/research/edge-studies/${sid}`)).json();
  check("validation: verdict shown = API study verdict",
    (await js(`document.querySelector('[data-testid="study-verdict"]').dataset.code`)) === st.result.verdict.code, st.result.verdict.code);
  check("validation: synthetic prices → no edge claimed", st.result.verdict.code !== "EDGE");
  check("validation: no trade opinion without a demonstrated edge",
    !(await js(`!!document.querySelector('[data-testid="study-opinion"]')`)) || (await text('[data-testid="study-opinion"]')) === "NE PAS TRADER");
  check("validation: walk-forward folds listed", (await js(`document.querySelectorAll('[data-testid="study-folds"] tbody tr').length`)) === st.result.folds.length);
  await shot("validation");

  // ---- EA audit (MT5 report uploaded through the file input; constructed martingale-grid deal list)
  await visit("/ea-audit", '[data-testid="run-ea-audit"]');
  await generic("ea-audit");
  const eaRows = [];
  let eaT = Date.UTC(2026, 0, 5, 8, 0), eaN = 0, eaBal = 10000;
  const eaRow = (type, dir, vol, price, profit) => {
    eaT += 7 * 60000; eaN += 1; eaBal += profit;
    const t = new Date(eaT).toISOString().replace("T", " ").slice(0, 19).replace(/-/g, ".");
    eaRows.push([t, eaN, type === "balance" ? "" : "XAUUSD", type, dir, type === "balance" ? "" : vol.toFixed(2),
      type === "balance" ? "" : price.toFixed(2), eaN, "0.00", "0.00", profit.toFixed(2), eaBal.toFixed(2), ""]);
  };
  eaRow("balance", "", 0, 0, 10000); eaBal = 10000;
  for (let k = 0; k < 6; k++) {
    const base = 2000 + 3 * k, lots = [0.01, 0.02, 0.04, 0.08];
    lots.forEach((v, i) => eaRow("buy", "in", v, base - 5 * i, 0));
    lots.forEach((v, i) => eaRow("sell", "out", v, base - 8, (base - 8 - (base - 5 * i)) * v * 100));
  }
  const eaHead = ["Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price", "Order", "Commission", "Swap", "Profit", "Balance", "Comment"];
  const eaHtml = `<html><table><tr><td colspan="13">Deals</td></tr><tr>${eaHead.map((h) => `<td>${h}</td>`).join("")}</tr>` +
    eaRows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("") + "</table></html>";
  await js(`(() => { const dt = new DataTransfer(); dt.items.add(new File([${JSON.stringify(eaHtml)}], "ReportTester-tour.html", { type: "text/html" }));
    const i = document.querySelector('[data-testid="ea-file"]'); i.files = dt.files; i.dispatchEvent(new Event("change", { bubbles: true })); })()`);
  await sleep(300);
  await js(`document.querySelector('[data-testid="run-ea-audit"]').click()`);
  await waitSel('[data-testid="ea-verdict"]', 30000);
  const eaForm = new FormData();
  eaForm.append("file", new Blob([eaHtml], { type: "text/html" }), "ReportTester-tour.html");
  const eaApi = await (await fetch(`${api}/ea-reports/analyze`, { method: "POST", body: eaForm, headers: { "X-ATO-Request": "1" } })).json();
  check("ea-audit: verdict shown = API verdict (martingale grid detected)",
    (await js(`document.querySelector('[data-testid="ea-verdict"]').dataset.verdict`)) === eaApi.verdict.code && eaApi.verdict.code === "MARTINGALE",
    eaApi.verdict?.code);
  check("ea-audit: stress distance shown = API value",
    nbsp(await text('[data-testid="ea-move-zero"]')).includes(nbsp(fr(eaApi.stress.adverse_move_to_zero, 2))), `${eaApi.stress?.adverse_move_to_zero}`);
  check("ea-audit: every detected mechanism listed",
    (await js(`document.querySelectorAll('[data-testid="ea-flags"] [data-flag]').length`)) === eaApi.flags.length);
  await shot("ea-audit");

  // ---- Bot Analysis (external MT5 simulation lab) — real reference report uploaded through the UI
  await visit("/bot-analysis", '[data-testid="bot-file"]');
  await generic("bot-analysis");
  check("bot-analysis: empty catalogue shows an explicit empty state", !!(await text('[data-testid="bot-empty"]')));
  const refB64 = readFileSync(path.join(ROOT, "quant/tests/fixtures/mt5/Gold_Grid_V370_MT5_Baseline_2026.html")).toString("base64");
  await js(`(() => { const b = atob(${JSON.stringify(refB64)}); const u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    const dt = new DataTransfer(); dt.items.add(new File([u], "Gold_Grid_V370_MT5_Baseline_2026.html", { type: "text/html" }));
    const i = document.querySelector('[data-testid="bot-file"]'); i.files = dt.files; i.dispatchEvent(new Event("change", { bubbles: true })); })()`);
  await sleep(300);
  await js(`document.querySelector('[data-testid="bot-import"]').click()`);
  await waitSel('[data-testid="simulation-view"]', 60000);
  const simId = await js(`document.querySelector('[data-testid="simulation-view"]').dataset.sim`);
  const extSim = await (await fetch(`${api}/external-sims/${simId}`)).json();
  check("bot-analysis: imported reference report validated against the MT5 summary",
    extSim.validation.status === "validé" && extSim.reconciliation.every((r) => r.status === "concordant") &&
    (await js(`document.querySelectorAll('[data-testid="reconciliation"] [data-recon="concordant"]').length`)) === extSim.reconciliation.length,
    `${extSim.validation?.status} ${extSim.reconciliation?.length}`);
  check("bot-analysis: net result shown = recomputed from deals = MT5 (−5 238,26)",
    nbsp(await text('[data-testid="sim-net"]')).includes(nbsp(fr(extSim.recomputed.net_profit, 2))) && Math.abs(extSim.recomputed.net_profit + 5238.26) < 0.01);
  check("bot-analysis: the ten final losses are listed (−51 990,13)",
    (await js(`document.querySelectorAll('[data-testid="collapse-trades"] tbody tr').length`)) === 10 && Math.abs(extSim.collapse.losing_total + 51990.13) < 0.01);
  check("bot-analysis: period divergence (requested 31/10, last deal 30/07) is stated", !!(await text('[data-testid="period-divergence"]')));
  check("bot-analysis: hypotheses shown apart from observed facts",
    (await js(`document.querySelectorAll('[data-testid="collapse-hypotheses"] li').length`)) === extSim.findings.hypotheses.length &&
    (await js(`document.querySelectorAll('[data-testid="collapse-observed"] li').length`)) === extSim.findings.observed.length);
  await js(`document.querySelector('[data-testid="run-what-if"]').click()`);
  await waitSel('[data-testid="what-if-result"]', 30000);
  check("bot-analysis: what-if result carries its qualification (approximation, not a backtest)",
    (await js(`document.querySelector('[data-testid="what-if-result"]').dataset.qualification`)) === "approximation");
  await shot("bot-analysis");

  // ---- strategies
  await visit("/optimizer", '[data-testid="strategy-detail"]');
  await generic("strategies");
  check("strategies: one card per engine strategy", (await js(`document.querySelectorAll('[data-testid^="strategy-card-"]').length`)) === strategies.length);
  const pilot = strategies.find((s) => s.spec.category === "pilot_trader");
  if (pilot) {
    await js(`document.querySelector('[data-testid="strategy-card-${pilot.spec.id}"]').click()`);
    await waitSel('[data-testid="open-questions"]');
    check("strategies: pilot draft lists the trader's open questions",
      (await js(`document.querySelectorAll('[data-testid="open-questions"] li').length`)) === pilot.spec.open_questions.length);
  }
  check("strategies: optimisation prerequisites reflect the lab (no historical data yet)",
    (await js(`document.querySelectorAll('[data-testid="optimization-prerequisites"] .text-primary').length`)) === 0);
  await shot("strategies");

  // ---- instruments
  await visit("/trading", '[data-testid="engine-contract"]');
  await generic("instruments");
  check("instruments: engine contract shown", (await text('[data-testid="engine-contract"]')).includes("XAUUSD"));
  check("instruments: MT5 export guide shown", !!(await text('[data-testid="mt5-export-guide"]')));
  await shot("instruments");

  // ---- execution
  await visit("/automation", '[data-testid="execution-locks"] li');
  await generic("execution");
  const locks = await text('[data-testid="execution-locks"]');
  check("execution: locks read from the engine", locks.includes(health.execution_mode) && locks.includes("désactivé"));
  check("execution: Risk Guardian profile shown", !!(await text('[data-testid="policy-mode"]')));
  await shot("execution");

  // ---- settings
  await visit("/settings", '[data-testid="settings-engine"]');
  await generic("settings");
  check("settings: engine identity = API health", (await text('[data-testid="settings-engine"]')).includes(health.code_hash));
  check("settings: defaults and risk profile shown", !!(await text('[data-testid="settings-defaults"]')) && !!(await text('[data-testid="settings-risk"]')));
  await shot("settings");

  // ---- 404
  await visit("/nulle-part", '[data-testid="not-found"]');
  check("unknown route → French 404", (await text('[data-testid="not-found"]')).includes("n'existe pas"));

  // ---- phone width
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  const overflow = [];
  for (const [route, ready] of [["/", '[data-testid="home-lab-state"] dl'], ["/dashboard", '[data-testid="runs-table"]'],
    ["/backtest", '[data-testid="results"]'], ["/research", '[data-testid="study-verdict"]'], ["/ea-audit", '[data-testid="run-ea-audit"]'], ["/bot-analysis", '[data-testid="simulation-view"]'], ["/optimizer", '[data-testid="strategy-detail"]'], ["/trading", '[data-testid="engine-contract"]'],
    ["/automation", '[data-testid="execution-locks"] li'], ["/settings", '[data-testid="settings-engine"]']]) {
    await visit(route, ready);
    if (await js("document.documentElement.scrollWidth > window.innerWidth + 1")) overflow.push(route);
    await shot(`mobile${route === "/" ? "-home" : route.replace("/", "-")}`);
  }
  check("every page fits a 390 px phone (no horizontal scroll)", overflow.length === 0, overflow.join(", "));
  check("no uncaught browser exception", consoleErrors.length === 0, consoleErrors.join(" | "));
  if (SHOTS) console.log(`screenshots: ${SHOTS}`);
  ws.close();
} catch (e) {
  check("tour completed", false, String(e));
} finally {
  await cleanup();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
