import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { EdgeStudy } from "@shared/quant-api";
import { StudyView } from "./StudyView";

/** UI boundary of the v0.4.1 safety rules: the page never upgrades an opinion and always says "experimental". */
function study(overrides: Partial<EdgeStudy["final_model"]["opinion"]> = {}, code: EdgeStudy["result"]["verdict"]["code"] = "NO_EDGE"): EdgeStudy {
  return {
    study_id: "0123456789abcdef", identity: {}, created_at: "2026-11-04T12:00:00+00:00", software_version: "0.4.1",
    engine_version: "backtest-engine/0.3.1", code_hash: "x", method_status: "experimental", execution_mode: "simulation",
    scope: "signaux candidats", numerical_issues: [],
    dataset: { dataset_id: "d", name: "DÉMO", kind: "synthetic", symbol: "XAUUSD-DEMO", timeframe: "M1", start: "", end: "" },
    strategy: { key: "k", name: "Baseline", params: {}, illustrative: true },
    settings: { horizon_bars: 240, folds: 4, initial_train_fraction: 0.5, l2: 1, n_boot: 2000, min_train: 100 },
    costs: { spread: 0.3, slippage: 0.05, commission_per_lot_per_side: 3 },
    feature_set: "price-action-v1", features: [], signals: { candidates: 10, labelled: 5, exit_reasons: {} },
    multiple_testing: { family: "f", studies_in_family: 1, alpha: 0.05, rule: "r", registry_entry: "h" },
    result: { folds: [], n_oos: 0, verdict: { code, confidence: "95,0 %", title: "T", text: "X" } },
    final_model: {
      status: "ok", weights: [],
      opinion: { opinion: "NE PAS TRADER", reasons: ["raison"], role: "entraînement", signal_time: "2026-11-04T12:00:00+00:00",
        direction: "BUY", score: null, threshold: null, ...overrides },
    },
  } as EdgeStudy;
}
const html = (s: EdgeStudy) => renderToStaticMarkup(<StudyView study={s} />);

describe("StudyView safety boundary", () => {
  it("always shows the experimental status and the candidate-vs-portfolio distinction", () => {
    const out = html(study());
    expect(out).toContain('data-testid="study-experimental"');
    expect(out).toContain("pas une performance de portefeuille exécutable");
  });

  it("never displays an unknown or legacy opinion such as PRENDRE: it falls back to NE PAS TRADER", () => {
    const out = html(study({ opinion: "PRENDRE" as never, score: 0.99 }, "EDGE"));
    expect(out).not.toContain(">PRENDRE<");
    expect(out).toMatch(/data-testid="study-opinion"[^>]*>NE PAS TRADER</);
  });

  it("presents the score as non-calibrated and shows the refusal reasons and the signal role", () => {
    const out = html(study({ score: 0.7, threshold: 0.5, role: "nouveau", reasons: ["aucun seuil de filtre validé"] }));
    expect(out).toContain("Score du modèle (non calibré)");
    expect(out).not.toContain("Probabilité de gain");
    expect(out).toContain("aucun seuil de filtre validé");
    expect(out).toContain("nouveau — résultat encore inconnu");
  });

  it("renders an INVALID verdict without any opinion upgrade", () => {
    const out = html(study({ reasons: ["étude invalide : aucun avis"], role: null, signal_time: null }, "INVALID"));
    expect(out).toContain('data-code="INVALID"');
    expect(out).toMatch(/data-testid="study-opinion"[^>]*>NE PAS TRADER</);
  });
});
