// I10: the production relay forwards /api/v1 untouched (method, path, headers, full body) even though
// the Express app parses JSON for its own routes, and fails closed when the Python API is down.
import http from "node:http";
import type { AddressInfo } from "node:net";
import express from "express";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { quantProxy } from "./quantProxy";
import { createServer } from "./index";

let upstream: http.Server;
let front: http.Server;
let base = "";
let upstreamUrl = "";

const listen = (srv: http.Server) =>
  new Promise<string>((resolve) =>
    srv.listen(0, "127.0.0.1", () => resolve(`http://127.0.0.1:${(srv.address() as AddressInfo).port}`)),
  );

beforeAll(async () => {
  upstream = http.createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      res.writeHead(201, { "content-type": "application/json", "x-upstream": "python" });
      res.end(JSON.stringify({ method: req.method, url: req.url, body, ato: req.headers["x-ato-request"] ?? null }));
    });
  });
  upstreamUrl = await listen(upstream);
  const app = express();
  app.use("/api/v1", quantProxy(upstreamUrl));
  app.use(createServer()); // has express.json(): must not see /api/v1 bodies
  front = http.createServer(app);
  base = await listen(front);
});

afterAll(() => {
  front?.close();
  upstream?.close();
});

describe("production /api/v1 relay", () => {
  it("forwards JSON POST bodies, path, query and headers untouched", async () => {
    const payload = JSON.stringify({ dataset_id: "a".repeat(16), strategy_key: "x@1.0.0" });
    const r = await fetch(`${base}/api/v1/backtests?x=1`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-ATO-Request": "1" },
      body: payload,
    });
    expect(r.status).toBe(201);
    expect(r.headers.get("x-upstream")).toBe("python");
    expect(await r.json()).toEqual({ method: "POST", url: "/api/v1/backtests?x=1", body: payload, ato: "1" });
  });

  it("leaves the other Express routes working", async () => {
    expect((await fetch(`${base}/api/ping`)).status).toBe(200);
  });

  it("answers 502 when the Python API is down, without inventing data", async () => {
    const app = express();
    app.use("/api/v1", quantProxy("http://127.0.0.1:1"));
    const srv = http.createServer(app);
    const url = await listen(srv);
    const r = await fetch(`${url}/api/v1/health`);
    srv.close();
    expect(r.status).toBe(502);
    expect((await r.json()).error).toMatch(/injoignable/);
  });

  it("refuses a non-loopback target", () => {
    expect(() => quantProxy("http://192.168.1.10:8765")).toThrow(/locale/);
    expect(() => quantProxy("https://example.com")).toThrow();
  });
});
