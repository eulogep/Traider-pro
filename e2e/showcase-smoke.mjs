#!/usr/bin/env node
/**
 * Static SHOWCASE check: serves dist/spa exactly like Netlify (static files + SPA fallback, NO API, NO Python) and
 * drives Chrome through every page. Build first: `pnpm build:showcase`.
 *
 * Usage:  node e2e/showcase-smoke.mjs [--shots-dir DIR]
 */
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { createServer as netServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist", "spa");
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const shotsArg = process.argv.indexOf("--shots-dir");
const SHOTS = shotsArg > 0 ? process.argv[shotsArg + 1] : null;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".csv": "text/csv", ".gz": "application/gzip", ".txt": "text/plain" };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res) => { const s = netServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
const results = [];
const check = (name, ok, info = "") => { results.push({ name, ok }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${info ? ` — ${info}` : ""}`); };

if (!existsSync(path.join(DIST, "showcase", "manifest.json"))) {
  console.error("dist/spa n'est pas une build vitrine : lancez d'abord « pnpm build:showcase ».");
  process.exit(2);
}
const manifest = JSON.parse(readFileSync(path.join(DIST, "showcase", "manifest.json"), "utf8"));
const sim = JSON.parse(readFileSync(path.join(DIST, "showcase", `external-sims__${manifest.content.external_simulations[0]}.json`), "utf8"));

// Netlify-like static server: file if it exists, otherwise index.html (SPA fallback). /api/* is NOT served.
const apiHits = [];
const server = createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (url.startsWith("/api/")) apiHits.push(url);
  let file = path.join(DIST, url);
  if (!file.startsWith(DIST) || !existsSync(file) || statSync(file).isDirectory()) file = path.join(DIST, "index.html");
  res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream" });
  res.end(readFileSync(file));
});
const tmp = mkdtempSync(path.join(tmpdir(), "ato-showcase-"));
const procs = [];
try {
  const [port, cdpPort] = [await freePort(), await freePort()];
  await new Promise((r) => server.listen(port, "127.0.0.1", r));
  const app = `http://127.0.0.1:${port}`;
  procs.push(spawn(CHROME, ["--headless=new", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${path.join(tmp, "chrome")}`,
    "--no-first-run", "--no-default-browser-check", "--window-size=1400,1800", "about:blank"], { stdio: "ignore" }));
  for (let t0 = Date.now(); ; await sleep(200)) {
    try { if ((await fetch(`http://127.0.0.1:${cdpPort}/json/version`)).ok) break; } catch { /* retry */ }
    if (Date.now() - t0 > 30000) throw new Error("Chrome ne démarre pas");
  }
  const page = (await (await fetch(`http://127.0.0.1:${cdpPort}/json/list`)).json()).find((p) => p.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let seq = 0;
  const pending = new Map();
  const errors = [];
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.text);
  });
  const cdp = (method, params = {}) => new Promise((res, rej) => {
    const id = ++seq;
    pending.set(id, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
  const js = async (e) => (await cdp("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result.value;
  const waitSel = async (sel, ms = 20000) => {
    for (const t0 = Date.now(); !(await js(`!!document.querySelector(${JSON.stringify(sel)})`)); await sleep(150))
      if (Date.now() - t0 > ms) throw new Error(`timeout ${sel}`);
  };
  const text = (sel) => js(`document.querySelector(${JSON.stringify(sel)})?.innerText ?? ""`);
  const nb = (s) => (s ?? "").replace(/[  ]/g, " ");
  const visit = async (route, ready) => { await cdp("Page.navigate", { url: `${app}${route}` }); await waitSel(ready); await sleep(400); };
  const shot = async (name) => {
    if (!SHOTS) return;
    const { data } = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    writeFileSync(path.join(SHOTS, `${name}.png`), Buffer.from(data, "base64"));
  };
  await cdp("Runtime.enable");
  await cdp("Page.enable");

  const pages = [["/", '[data-testid="home-lab-state"] dl'], ["/dashboard", '[data-testid="runs-table"]'],
    ["/backtest", '[data-testid="results"]'], ["/research", '[data-testid="study-verdict"]'],
    ["/bot-analysis", '[data-testid="simulation-view"]'], ["/ea-audit", '[data-testid="run-ea-audit"]'],
    ["/optimizer", '[data-testid="strategy-detail"]'], ["/trading", '[data-testid="engine-contract"]'],
    ["/automation", '[data-testid="execution-locks"] li'], ["/settings", '[data-testid="settings-engine"]']];
  for (const [route, ready] of pages) {
    await visit(route, ready);  // direct navigation = deep link: the SPA fallback must serve it
    const ok = (await js(`!!document.querySelector('[data-testid="showcase-banner"]')`)) &&
      !(await js(`!!document.querySelector('[data-testid="api-offline-notice"], [data-testid="api-offline"]')`));
    check(`${route}: page servie en lien direct, bandeau vitrine, aucune mention « API injoignable »`, ok);
    await shot(`showcase${route === "/" ? "-home" : route.replace("/", "-")}`);
  }

  await visit("/bot-analysis", '[data-testid="simulation-view"]');
  check("bot-analysis : résultat net pré-calculé affiché (−5 238,26)", nb(await text('[data-testid="sim-net"]')).includes("5 238,26"));
  check("bot-analysis : les dix pertes finales sont listées",
    (await js(`document.querySelectorAll('[data-testid="collapse-trades"] tbody tr').length`)) === 10 && sim.collapse.losing_trades === 10);
  await js(`document.querySelector('[data-testid="run-what-if"]').click()`);
  await waitSel('[data-testid="what-if-result"]');
  check("bot-analysis : hypothèse pré-calculée affichée avec sa qualification",
    (await js(`document.querySelector('[data-testid="what-if-result"]').dataset.qualification`)) === "approximation");
  await js(`(() => { const dt = new DataTransfer(); dt.items.add(new File(["x"], "r.html")); const i = document.querySelector('[data-testid="bot-file"]');
    i.files = dt.files; i.dispatchEvent(new Event("change", { bubbles: true })); })()`);
  await sleep(200);
  await js(`document.querySelector('[data-testid="bot-import"]').click()`);
  await sleep(600);
  check("bot-analysis : un import est refusé avec un message « lecture seule »",
    (await js(`[...document.querySelectorAll('[role="alert"]')].some((e) => e.innerText.includes("lecture seule"))`)));

  await visit("/research", '[data-testid="study-verdict"]');
  await js(`document.querySelector('[data-testid="run-study"]').click()`);
  await sleep(600);
  check("validation : lancer une étude est refusé (lecture seule)",
    (await js(`[...document.querySelectorAll('[role="alert"]')].some((e) => e.innerText.includes("lecture seule"))`)));

  const exp = await fetch(`${app}/showcase/exports/${manifest.content.backtest}/trades.csv`);
  check("backtest : l'export CSV du run est téléchargeable", exp.ok && (await exp.text()).startsWith("trade_id") );

  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  const overflow = [];
  for (const [route, ready] of pages) {
    await visit(route, ready);
    if (await js("document.documentElement.scrollWidth > window.innerWidth + 1")) overflow.push(route);
  }
  check("toutes les pages tiennent sur un téléphone de 390 px", overflow.length === 0, overflow.join(", "));
  check("aucune requête vers /api/ (pas de serveur derrière la vitrine)", apiHits.length === 0, apiHits.slice(0, 3).join(", "));
  check("aucune exception JavaScript", errors.length === 0, errors.slice(0, 3).join(" | "));
  ws.close();
} catch (e) {
  check("parcours terminé", false, String(e));
} finally {
  for (const p of procs) p.kill();
  server.close();
  await sleep(500);
  try { rmSync(tmp, { recursive: true, force: true }); } catch { /* temp only */ }
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
