import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ExternalSim, ExternalTrade } from "@shared/quant-api";
import { SimulationView } from "./SimulationView";

const trade = (n: number, net: number, reason: ExternalTrade["close_reason"]): ExternalTrade => ({
  trade_no: n, side: "BUY", symbol: "XAUUSD", volume: 0.95, entry_deal: String(600 + n), entry_time: "2026-07-29T22:20:00+00:00",
  entry_price: 4090, exit_deal: String(620 + n), exit_time: "2026-07-30T01:00:00+00:00", exit_price: 4027.47,
  exit_comment: reason === "stop-out" ? "so 12.43%" : "end of test", close_reason: reason, profit: net, swap: 0, commission: 0, net,
});

function sim(overrides: Partial<ExternalSim> = {}): ExternalSim {
  const losses = [trade(0, -6776.72, "stop-out"), trade(1, -3598.41, "fin du test")];
  return {
    sim_id: "a45999a0c4a1b14f", kind: "simulation externe", identity: {}, test_key: "t", config_key: "c",
    source: { name: "Gold_Grid_V370_MT5_Baseline_2026.html", sha256: "9048261e1d5016dd".padEnd(64, "0"), format: "html", encoding: "utf-16", report_file: "x", archive_members: [] },
    declared_manifest: null,
    robot: { name: "Gold Grid Strategy V3.70 EA", self_identification: "Quantum Queen MT5 v3.70", declared_version: "3.70", website: null },
    environment: { server: "MetaQuotes-Demo", build: "6275", company: "MetaQuotes Ltd.", symbol: "XAUUSD", timeframe: "M15",
      requested_period: "M15 (2026.01.01 - 2026.10.31)", initial_deposit: 10000, currency: "USD", leverage: "1:100",
      history_quality: "100%", bars: "13195", ticks: "1", modelling: null },
    inputs: [{ name: "InpDDMode", value: "0" }, { name: "InpPanel", value: "1" }],
    risk_inputs: [{ name: "InpDDMode", value: "0" }],
    reported: {}, recomputed: { net_profit: -5238.26, profit_trades_pct: 82.8, profit_trades: 260, total_trades: 314,
      average_profit_trade: 224.97, average_loss_trade: -1180.18, balance_dd_maximal_pct: 91.61, balance_dd_maximal: 51990.13 },
    reconciliation: [{ metric: "net_profit", label: "Total Net Profit", reported: -5238.26, computed: -5238.26, tolerance: 0.005, status: "concordant" }],
    validation: { status: "validé", checks: [{ check: "résumé MT5 ↔ deals", ok: true, detail: "23/23" }], rejected_rows: [], duplicates: [] },
    period: { requested_raw: "M15 (2026.01.01 - 2026.10.31)", requested_start: "2026-01-01", requested_end: "2026-10-31",
      first_deal: "2026-01-07T08:00:00+00:00", last_deal: "2026-07-30T01:00:00+00:00", ends_early: true,
      evidence: ["Dernière opération le 2026-07-30 01:00, fin demandée le 2026-10-31."], interpretation: "Hypothèse : arrêt après stop-out." },
    contract_size: { value: 100, source: "déduite des profits MT5" },
    counts: { orders: 628, deals: 629, trading_deals: 628, positions_opened: 314, closing_deals: 314, trades: 314, balance_operations: 1 },
    pairing: { rule: "match", closes_checked: 314, closes_matched: 314, unmatched_close_volume: 0, note: "pas d'identifiant de position", alternatives: {} },
    deals: [{ seq: 0, time: "2026-01-01T00:00:00+00:00", deal: "1", symbol: "", type: "balance", direction: "", volume: 0, price: 0, commission: 0, swap: 0, profit: 10000, balance: 10000, comment: "" },
      { seq: 1, time: "2026-01-07T08:02:00+00:00", deal: "3", symbol: "XAUUSD", type: "buy", direction: "out", volume: 0.17, price: 4453.1, commission: 0, swap: 0, profit: 20.91, balance: 10020.91, comment: "" }],
    trades: losses, timeline: [], lot_progression: [], monthly: [{ month: "2026-07", trades: 10, wins: 0, net: -51990.13, worst: -6776.72, lots: 9.38 }],
    collapse: { peak_time: "2026-07-29T22:32:00+00:00", peak_balance: 56751.87, trough_time: "2026-07-30T01:00:00+00:00", trough_balance: 4761.74,
      drawdown: 51990.13, drawdown_pct: 91.61, losing_trades: 10, losing_total: -51990.13, lots_involved: 9.38, entries_involved: 10,
      close_reasons: { "stop-out": 5, "fin du test": 5 }, trades: losses, first_entry: null, last_entry: null },
    largest_losses: losses,
    behaviour: { verdict: { code: "STOP_OUT", title: "Compte liquidé", text: "" }, flags: [], stress: null,
      exposure: {} as ExternalSim["behaviour"]["exposure"] },
    findings: { observed: [{ fact: "10 pertes clôturées pour -51 990.13", source: "deals" }],
      hypotheses: [{ statement: "Le contrôle de drawdown du robot était désactivé.", evidence: "InpDDMode=0", status: "hypothèse" }], note: "Constats vs hypothèses." },
    availability: { position_ids: false }, limits: ["Le code .ex5 n'est ni exécuté ni lu."],
    ...overrides,
  };
}
const html = (s: ExternalSim) =>
  renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}><SimulationView sim={s} /></QueryClientProvider>);

describe("SimulationView (Bot Analysis)", () => {
  it("separates observed facts from hypotheses in the Risk Collapse Analysis", () => {
    const out = html(sim());
    expect(out).toContain('data-testid="risk-collapse"');
    expect(out).toMatch(/data-testid="collapse-observed"[\s\S]*51 990.13/);
    expect(out).toMatch(/data-testid="collapse-hypotheses"[\s\S]*hypothèse[\s\S]*contrôle de drawdown/);
    expect(out).toMatch(/data-testid="collapse-trades"[\s\S]*stop-out[\s\S]*fin du test/);
  });

  it("states the period divergence, the data validation and that it is not an engine backtest", () => {
    const out = html(sim());
    expect(out).toContain('data-testid="period-divergence"');
    expect(out).toContain("pas un backtest du moteur");
    expect(out).toMatch(/data-testid="sim-validation"[^>]*>validé/);
    expect(out).toContain('data-recon="concordant"');
    expect(out).toContain("ni exécuté ni lu");
  });

  it("says when the MT5 summary is missing instead of inventing a reconciliation", () => {
    const out = html(sim({ reconciliation: [], collapse: null, period: { ...sim().period, ends_early: false } }));
    expect(out).toContain("rapprochement impossible");
    expect(out).not.toContain('data-testid="risk-collapse"');
    expect(out).not.toContain('data-testid="period-divergence"');
  });

  it("labels closing deals as closings — a BUY deal can close a SELL position", () => {
    const out = html(sim());
    expect(out).toMatch(/<td[^>]*>buy<\/td><td[^>]*>clôture<\/td>/);
  });
});
