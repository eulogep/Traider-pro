import { describe, expect, it } from "vitest";
import { createQuantClient, QuantApiError, showcaseFile } from "./quantApi";

/** Same cases as quant/tests/test_showcase.py: the TypeScript and Python naming rules must never diverge. */
const CASES: Array<[string, string]> = [
  ["/health", "/showcase/health.json"],
  ["/backtests/010f866522a4cdf7/equity?max_points=1500", "/showcase/backtests__010f866522a4cdf7__equity--max_points-1500.json"],
  ["/external-sims/a45999a0c4a1b14f/what-if?rule=max_positions", "/showcase/external-sims__a45999a0c4a1b14f__what-if--rule-max_positions.json"],
  ["/x?a=1&b=2", "/showcase/x--a-1_b-2.json"],
];

describe("static showcase mode", () => {
  it("maps every API path to the file written by the Python exporter", () => {
    for (const [path, file] of CASES) expect(showcaseFile(path)).toBe(file);
  });

  it("reads pre-computed files and refuses every mutation", async () => {
    const calls: string[] = [];
    const fake = (async (url: string) => {
      calls.push(url);
      return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
    }) as unknown as typeof fetch;
    const api = createQuantClient("", fake, true);
    expect(await api.health()).toEqual({ status: "ok" });
    expect(calls).toEqual(["/showcase/health.json"]);
    await expect(api.createDemoDataset()).rejects.toBeInstanceOf(QuantApiError);
    await expect(api.importExternalSim(new Blob(["x"]), "r.html")).rejects.toThrow(/lecture seule/);
    expect(calls).toHaveLength(1); // no request at all for a refused mutation
    expect(api.exportUrl("010f866522a4cdf7", "trades.csv")).toBe("/showcase/exports/010f866522a4cdf7/trades.csv");
  });

  it("is off by default: the normal build still talks to the real API", async () => {
    const calls: string[] = [];
    const fake = (async (url: string) => { calls.push(url); return new Response("{}", { status: 200 }); }) as unknown as typeof fetch;
    await createQuantClient("", fake).health();
    expect(calls).toEqual(["/api/v1/health"]);
  });
});
