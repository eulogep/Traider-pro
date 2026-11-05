// Codex V0.3.1 counter-audit N10: a cross-site "simple" POST could reset the settings file.
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type { AddressInfo } from "node:net";
import { request } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

let port = 0;
let dir = "";
let close: () => void = () => {};

beforeAll(async () => {
  dir = mkdtempSync(path.join(tmpdir(), "ato-guard-"));
  process.chdir(dir);
  const { createServer } = await import("./index");
  const server = createServer().listen(0, "127.0.0.1");
  await new Promise((r) => server.once("listening", r));
  port = (server.address() as AddressInfo).port;
  close = () => server.close();
});
afterAll(() => close());

const sentinel = () => path.join(dir, "data", "settings.json");
function plant() {
  mkdirSync(path.join(dir, "data"), { recursive: true });
  writeFileSync(sentinel(), JSON.stringify({ darkMode: true }));
}

/** raw request so that Host can be forged (fetch does not allow it) */
function send(method: string, p: string, headers: Record<string, string>, body = ""): Promise<number> {
  return new Promise((resolve, reject) => {
    const req = request({ host: "127.0.0.1", port, method, path: p, headers: { ...headers, "Content-Length": Buffer.byteLength(body) } },
      (res) => { res.resume(); res.on("end", () => resolve(res.statusCode ?? 0)); });
    req.on("error", reject);
    req.end(body);
  });
}

describe("legacy Express mutations are local-only (N10)", () => {
  it("refuses a cross-site form POST to /api/settings/reset and keeps the file", async () => {
    plant();
    const status = await send("POST", "/api/settings/reset", {
      Host: `127.0.0.1:${port}`, Origin: "https://evil.example", "Content-Type": "application/x-www-form-urlencoded",
    });
    expect(status).toBe(403);
    expect(existsSync(sentinel())).toBe(true);
  });

  it("refuses a forged Host even with the local header", async () => {
    plant();
    const status = await send("POST", "/api/settings/reset", { Host: "evil.example", "X-ATO-Request": "1" });
    expect(status).toBe(403);
    expect(existsSync(sentinel())).toBe(true);
  });

  it("refuses a local mutation without X-ATO-Request", async () => {
    plant();
    expect(await send("POST", "/api/settings/reset", { Host: `127.0.0.1:${port}` })).toBe(403);
    expect(existsSync(sentinel())).toBe(true);
  });

  it("accepts the local UI's mutation (loopback Host, local Origin, header)", async () => {
    plant();
    const status = await send("POST", "/api/settings/reset", {
      Host: `localhost:${port}`, Origin: `http://localhost:${port}`, "X-ATO-Request": "1",
    });
    expect(status).toBe(200);
  });

  it("keeps GET working for a loopback Host", async () => {
    expect(await send("GET", "/api/ping", { Host: `127.0.0.1:${port}` })).toBe(200);
  });
});
