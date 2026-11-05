/**
 * Instrument contract specifications and P&L in account currency.
 * HYPOTHESES — typical CFD/FX values, to be checked against the broker.
 * Unknown instrument or impossible conversion => null (never a guessed number).
 */
export type Side = "BUY" | "SELL";

export interface InstrumentSpec {
  symbol: string;
  contractSize: number; // base units per 1.00 lot
  baseCurrency: string;
  quoteCurrency: string;
  digits: number;
}

export const INSTRUMENTS: Record<string, InstrumentSpec> = {
  XAUUSD: { symbol: "XAUUSD", contractSize: 100, baseCurrency: "XAU", quoteCurrency: "USD", digits: 2 },
  EURUSD: { symbol: "EURUSD", contractSize: 100_000, baseCurrency: "EUR", quoteCurrency: "USD", digits: 5 },
  GBPUSD: { symbol: "GBPUSD", contractSize: 100_000, baseCurrency: "GBP", quoteCurrency: "USD", digits: 5 },
  AUDUSD: { symbol: "AUDUSD", contractSize: 100_000, baseCurrency: "AUD", quoteCurrency: "USD", digits: 5 },
  USDJPY: { symbol: "USDJPY", contractSize: 100_000, baseCurrency: "USD", quoteCurrency: "JPY", digits: 3 },
  USDCHF: { symbol: "USDCHF", contractSize: 100_000, baseCurrency: "USD", quoteCurrency: "CHF", digits: 5 },
};

/** Spread expressed in points (1 point = 10^-digits). */
export function spreadInPoints(bid: number, ask: number, spec: InstrumentSpec): number {
  return Math.round((ask - bid) * 10 ** spec.digits);
}

/**
 * P&L of a position in account currency.
 * BUY closes at BID, SELL closes at ASK: pass the relevant `closePrice`.
 * Conversion: quote = account -> as is; base = account -> divide by the close price
 * (e.g. USDJPY P&L in JPY / USDJPY = USD); otherwise null (no FX rate available).
 */
export function positionProfit(
  side: Side,
  openPrice: number,
  closePrice: number,
  volumeLots: number,
  spec: InstrumentSpec | undefined,
  accountCurrency = "USD",
): number | null {
  if (!spec || !(volumeLots > 0) || !(closePrice > 0) || !(openPrice > 0)) return null;
  const direction = side === "BUY" ? 1 : -1;
  const inQuote = direction * (closePrice - openPrice) * volumeLots * spec.contractSize;
  if (spec.quoteCurrency === accountCurrency) return inQuote;
  if (spec.baseCurrency === accountCurrency) return inQuote / closePrice;
  return null;
}
