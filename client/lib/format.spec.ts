import { describe, expect, it } from "vitest";
import { UNAVAILABLE, fmtDateTime, fmtShortDateTime, fmtMoney, fmtNum, fmtPct, fmtSignedMoney, fmtValue } from "./format";

describe("display formatting of engine values", () => {
  it("never turns a missing metric into a number", () => {
    for (const v of [null, undefined, Number.NaN, Infinity]) {
      expect(fmtPct(v)).toBe(UNAVAILABLE);
      expect(fmtNum(v)).toBe(UNAVAILABLE);
      expect(fmtMoney(v)).toBe(UNAVAILABLE);
    }
    expect(fmtDateTime(null)).toBe(UNAVAILABLE);
  });

  it("keeps the sign and the value it is given", () => {
    expect(fmtSignedMoney(31.79)).toMatch(/^\+31,79\sUSD$/);
    expect(fmtSignedMoney(-23.21)).toMatch(/^−23,21\sUSD$/);
    expect(fmtPct(41.666, 1)).toMatch(/^41,7\s%$/);
    expect(fmtNum(0)).toBe("0,00");
  });

  it("shows timestamps in UTC", () => {
    expect(fmtDateTime("2026-09-07T12:01:00+00:00")).toBe("2026-09-07 12:01 UTC");
  });

  it("compact table dates stay UTC and never invent a value", () => {
    expect(fmtShortDateTime("2026-09-07T12:01:00+00:00")).toBe("09-07 12:01");
    expect(fmtShortDateTime("2026-09-07T14:01:00+02:00")).toBe("09-07 12:01");
    expect(fmtShortDateTime(null)).toBe(UNAVAILABLE);
  });

  it("plain engine values keep every decimal, in French notation", () => {
    expect(fmtValue(0.25)).toBe("0,25");
    expect(fmtValue(0.05)).toBe("0,05");
    expect(fmtValue(null)).toBe(UNAVAILABLE);
    expect(fmtValue(Number.NaN)).toBe(UNAVAILABLE);
  });
});
