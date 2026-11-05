import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { EaAudit } from "@shared/quant-api";
import { EaAuditView } from "./EaAuditView";

/** Display boundary of the EA audit: the verdict, the stress figures and the limits are always shown as computed. */
function audit(overrides: Partial<EaAudit> = {}): EaAudit {
  return {
    analysis_version: "ea-audit/1",
    source: { format: "html", encoding: "utf-16", header: [], deals_read: 49, rows_rejected: 1,
      rejected_examples: [{ row: 4, reason: "séparateurs ambigus : '1,990.50'", cells: [] }], rows_ignored: 0 },
    period: { start: "2026-01-05T08:07:00+00:00", end: "2026-01-06T08:00:00+00:00" },
    symbols: ["XAUUSD"],
    contract: { contract_size: 100, note: "hypothèse à vérifier" },
    verdict: { code: "MARTINGALE", title: "Martingale détectée — risque de ruine", text: "L'EA augmente ses lots." },
    flags: [{ code: "LOT_ESCALATION", label: "Lots croissants", detail: "multiplicateur médian 2.00" }],
    counts: { stop_out_closes: 0, end_of_test_closes: 0, trading_deals: 48, balance_operations: 1, entries: 24, adds_to_open_stack: 18, adds_against_open_loss: 18,
      baskets_closed: 6, baskets_open_at_end: 0, inout_deals: 0, unmatched_close_volume: 0 },
    exposure: { max_positions_same_direction: 4, max_gross_lots: 0.15, min_entry_lot: 0.01, max_entry_lot: 0.08,
      median_add_ratio: 2, max_add_ratio: 2, median_first_lot_ratio_after_loss: null, median_first_lot_ratio_after_win: 1,
      worst_adverse_distance_while_adding: 15 },
    baskets: { count: 6, win_rate: 1, median_win: 30, median_loss: null, worst_loss: null, best_win: 31, net_total: 180,
      definition: "série" },
    out_deals: { count: 24, net_total: 180 },
    stress: { time: "2026-01-05T09:00:00+00:00", symbol: "XAUUSD", net_lots: 0.15, price: 1985, balance: 10000, positions: 4,
      equity_estimate: 9800, loss_per_price_unit: 15, adverse_move_to_lose_half: 320, adverse_move_to_zero: 653.33,
      direction: "baisse", note: "Stop-out ignoré." },
    thresholds: {},
    limits: ["Analyse du comportement visible, pas du code."],
    file: { name: "ReportTester.html", bytes: 1234 },
    stored: false,
    note: "rien n'est enregistré",
    ...overrides,
  };
}
const html = (a: EaAudit) => renderToStaticMarkup(<EaAuditView audit={a} />);

describe("EaAuditView", () => {
  it("shows the verdict code, the detected mechanism and the stress distances", () => {
    const out = html(audit());
    expect(out).toContain('data-verdict="MARTINGALE"');
    expect(out).toContain("Martingale détectée");
    expect(out).toContain('data-flag="LOT_ESCALATION"');
    expect(out).toMatch(/data-testid="ea-move-zero"[\s\S]*653,33/);
    expect(out).toContain("baisse");
  });

  it("never hides refused rows nor the limits of the analysis", () => {
    const out = html(audit());
    expect(out).toContain('data-testid="ea-rejected"');
    expect(out).toContain("séparateurs ambigus");
    expect(out).toContain("pas du code");
    expect(out).toContain("rien n&#x27;est enregistré");
  });

  it("a clean report is not presented as safe", () => {
    const out = html(audit({ verdict: { code: "NO_SIGNATURE", title: "Aucune signature", text: "Ce n'est pas une preuve de sécurité." },
      flags: [], stress: null }));
    expect(out).toContain('data-verdict="NO_SIGNATURE"');
    expect(out).toContain("pas une preuve de sécurité");
    expect(out).not.toContain('data-testid="ea-stress"');
  });
});
