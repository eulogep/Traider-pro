// Non-regression: credentials sent to /api/settings were written in clear to data/settings.json.
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type { AddressInfo } from "node:net";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const payload = {
  darkMode: false, colorTheme: "professional", chartStyle: "line", dashboardLayout: "grid",
  language: "fr", timezone: "UTC", currency: "USD", numberFormat: "eu",
  defaultRisk: 1, defaultStopLoss: 20, defaultTakeProfit: 40, defaultPositionSize: "auto",
  slippageTolerance: 1, oneClickTrading: false, aiSignalValidation: false, aiConfidenceThreshold: 70,
  optimizationFrequency: "manual", modelSelection: "auto", learningMode: false,
  mt5Server: "demo", mt5Login: "1", mt5Password: "SECRET-PASSWORD", enableEA: false,
  allowAutoTrading: false, realtimeDataFeed: false, updateFrequency: 1,
  tradeExecution: false, profitLossTargets: false, aiSignals: false, systemErrors: false,
  marketNews: false, inAppNotifications: false, emailAlerts: false, pushNotifications: false,
  emailAddress: "", phoneNumber: "", telegramToken: "SECRET-TOKEN",
  twoFactorAuth: false, sessionTimeout: 30, ipWhitelist: false, allowedIPs: "",
  automaticBackups: false, backupFrequency: "daily", backupLocation: "local",
};

let base = "";
let dir = "";
let close: () => void = () => {};

beforeAll(async () => {
  dir = mkdtempSync(path.join(tmpdir(), "ato-settings-"));
  process.chdir(dir); // SETTINGS_FILE is resolved from the cwd at import time
  const { createServer } = await import("./index");
  const server = createServer().listen(0, "127.0.0.1");
  await new Promise((r) => server.once("listening", r));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  close = () => server.close();
});
afterAll(() => close());

describe("/api/settings never stores or returns credentials", () => {
  it("POST strips secrets before writing the file", async () => {
    const res = await fetch(`${base}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-ATO-Request": "1" },
      body: JSON.stringify(payload),
    });
    expect(res.status).toBe(200);
    const stored = readFileSync(path.join(dir, "data", "settings.json"), "utf-8");
    expect(stored).not.toContain("SECRET");
    expect(JSON.parse(stored).mt5Login).toBe("1");
  });

  it("GET purges secrets left in an old file", async () => {
    mkdirSync(path.join(dir, "data"), { recursive: true });
    writeFileSync(path.join(dir, "data", "settings.json"), JSON.stringify(payload));
    const body = await (await fetch(`${base}/api/settings`)).text();
    expect(body).not.toContain("SECRET");
  });

  it("CORS does not allow arbitrary websites", async () => {
    const res = await fetch(`${base}/api/settings`, { headers: { Origin: "https://evil.example" } });
    expect(res.headers.get("access-control-allow-origin")).toBeNull();
    const ok = await fetch(`${base}/api/ping`, { headers: { Origin: "http://localhost:8080" } });
    expect(ok.headers.get("access-control-allow-origin")).toBe("http://localhost:8080");
  });
});
