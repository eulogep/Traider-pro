#!/usr/bin/env node
/**
 * Screenshots for the README, taken from the STATIC SHOWCASE build (real pages, pre-computed engine results).
 * Build first: `pnpm build:showcase`. Writes PNG files to docs/images/ (or --out DIR).
 *
 * Usage:  node e2e/readme-screenshots.mjs [--out DIR]
 */
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { createServer as netServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist", "spa");
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const outArg = process.argv.indexOf("--out");
const OUT = outArg > 0 ? path.resolve(process.argv[outArg + 1]) : path.join(ROOT, "docs", "images");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".ico": "image/x-icon" };
const W = 1440, H = 900;

/** [file, route, element to frame (null = viewport), wait selector, optional action before the shot] */
const SHOTS = [
  ["accueil.png", "/", null, '[data-testid="home-lab-state"] dl'],
  ["bot-analysis.png", "/bot-analysis", null, '[data-testid="simulation-view"]'],
  ["risk-collapse.png", "/bot-analysis", '[data-testid="risk-collapse"]', '[data-testid="risk-collapse"] .recharts-line'],
  ["reconciliation-mt5.png", "/bot-analysis", '[data-testid="reconciliation"]', '[data-testid="reconciliation"] [data-recon]'],
  ["backtest.png", "/backtest", null, '[data-testid="results"] .recharts-line'],
  ["validation.png", "/research", null, '[data-testid="study-verdict"]'],
];

if (!existsSync(path.join(DIST, "showcase", "manifest.json"))) {
  console.error("dist/spa n'est pas une build vitrine : lancez d'abord « pnpm build:showcase ».");
  process.exit(2);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res) => { const s = netServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
const server = createServer((req, res) => {
  let file = path.join(DIST, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!file.startsWith(DIST) || !existsSync(file) || statSync(file).isDirectory()) file = path.join(DIST, "index.html");
  res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream" });
  res.end(readFileSync(file));
});
const tmp = mkdtempSync(path.join(tmpdir(), "ato-shots-"));
const procs = [];
let failed = false;
try {
  mkdirSync(OUT, { recursive: true });
  const [port, cdpPort] = [await freePort(), await freePort()];
  await new Promise((r) => server.listen(port, "127.0.0.1", r));
  procs.push(spawn(CHROME, ["--headless=new", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${path.join(tmp, "chrome")}`,
    "--no-first-run", "--no-default-browser-check", `--window-size=${W},${H}`, "--hide-scrollbars", "about:blank"], { stdio: "ignore" }));
  for (let t0 = Date.now(); ; await sleep(200)) {
    try { if ((await fetch(`http://127.0.0.1:${cdpPort}/json/version`)).ok) break; } catch { /* retry */ }
    if (Date.now() - t0 > 30000) throw new Error("Chrome ne démarre pas");
  }
  const page = (await (await fetch(`http://127.0.0.1:${cdpPort}/json/list`)).json()).find((p) => p.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let seq = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
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
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  for (const [file, route, frame, ready] of SHOTS) {
    await cdp("Page.navigate", { url: `http://127.0.0.1:${port}${route}` });
    await waitSel(ready);
    await sleep(900); // let charts finish their first paint
    let params = { format: "png" };
    if (frame) {
      const r = await js(`(() => { const b = document.querySelector(${JSON.stringify(frame)}).getBoundingClientRect();
        return { x: b.left + window.scrollX, y: b.top + window.scrollY, width: b.width, height: Math.min(b.height, 1400) }; })()`);
      params = { format: "png", captureBeyondViewport: true, clip: { ...r, scale: 1 } };
    }
    const { data } = await cdp("Page.captureScreenshot", params);
    writeFileSync(path.join(OUT, file), Buffer.from(data, "base64"));
    console.log(`OK  ${file}`);
  }
  ws.close();
} catch (e) {
  failed = true;
  console.error(`ÉCHEC  ${e}`);
} finally {
  for (const p of procs) p.kill();
  server.close();
  await sleep(400);
  try { rmSync(tmp, { recursive: true, force: true }); } catch { /* temp only */ }
}
process.exit(failed ? 1 : 0);
