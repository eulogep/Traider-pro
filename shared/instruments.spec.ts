import { describe, expect, it } from "vitest";
import { INSTRUMENTS, positionProfit, spreadInPoints } from "./instruments";
import { SECRET_SETTING_KEYS, stripSecrets } from "./security";

describe("positionProfit", () => {
  it("BUY XAUUSD uses 100 oz per lot", () => {
    expect(positionProfit("BUY", 2000, 2001.5, 0.1, INSTRUMENTS.XAUUSD)).toBeCloseTo(15);
  });
  it("SELL profits when the closing ASK is below the entry", () => {
    expect(positionProfit("SELL", 2000, 1998, 0.1, INSTRUMENTS.XAUUSD)).toBeCloseTo(20);
    expect(positionProfit("SELL", 2000, 2002, 0.1, INSTRUMENTS.XAUUSD)).toBeCloseTo(-20);
  });
  it("EURUSD uses 100 000 units per lot (was 100 in the mock: 1000x too small)", () => {
    expect(positionProfit("BUY", 1.08, 1.081, 1, INSTRUMENTS.EURUSD)).toBeCloseTo(100);
  });
  it("USDJPY P&L is converted from JPY to USD", () => {
    // 1 lot, +0.50 JPY = 50 000 JPY = 50 000 / 150.5 USD
    expect(positionProfit("BUY", 150, 150.5, 1, INSTRUMENTS.USDJPY)).toBeCloseTo(50_000 / 150.5);
  });
  it("refuses to guess: unknown instrument or impossible conversion -> null", () => {
    expect(positionProfit("BUY", 1, 1.1, 1, undefined)).toBeNull();
    expect(positionProfit("BUY", 1.08, 1.09, 1, INSTRUMENTS.EURUSD, "GBP")).toBeNull();
    expect(positionProfit("BUY", 1.08, 1.09, 0, INSTRUMENTS.EURUSD)).toBeNull();
  });
});

describe("spreadInPoints", () => {
  it("depends on the instrument digits", () => {
    expect(spreadInPoints(1985.45, 1985.65, INSTRUMENTS.XAUUSD)).toBe(20);
    expect(spreadInPoints(1.0875, 1.0876, INSTRUMENTS.EURUSD)).toBe(10);
    expect(spreadInPoints(149.82, 149.84, INSTRUMENTS.USDJPY)).toBe(20);
  });
});

describe("stripSecrets", () => {
  it("removes every credential field and keeps the rest", () => {
    const out = stripSecrets({ mt5Password: "x", telegramToken: "y", darkMode: true, mt5Login: "1" });
    for (const k of SECRET_SETTING_KEYS) expect(out).not.toHaveProperty(k);
    expect(out).toEqual({ darkMode: true, mt5Login: "1" });
  });
});
