/**
 * Contract of the Python quant API v1 (quant/src/ai_trader_optimizer/api).
 *
 * The React app DISPLAYS these values; it never computes financial figures.
 * Shapes mirror the pydantic models / engine outputs. They are checked end-to-end
 * against the real Python API by `client/lib/quantApi.integration.spec.ts`.
 */

export type DataKind = "synthetic" | "historical" | "demo_account";

export interface Health {
  status: "ok";
  software_version: string;
  engine_version: string;
  code_hash: string;
  execution_mode: "simulation";
  live_trading_enabled: false;
  demo_trading_enabled: false;
  order_routes: 0;
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  symbol: string;
  timeframe: string;
  kind: DataKind;
  source: string;
  rows: number;
  start: string;
  end: string;
  imported_at: string | null;
}

export interface QualityIssue {
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
  rows: number[];
}

export interface QualityReport {
  ok: boolean;
  rows_raw: number;
  rows_valid: number;
  timeframe: string | null;
  detected_format: string;
  start: string | null;
  end: string | null;
  issues: QualityIssue[];
  gaps_count: number;
  gaps_by_category: Record<string, number>;
  stats: Record<string, unknown>;
}

export interface DatasetMeta extends Omit<DatasetSummary, "imported_at"> {
  price_side: "bid" | "mid";
  source_timezone: string;
  raw_sha256: string | null;
  imported_at: string | null;
  notes: string;
  quality: QualityReport;
}

export interface DatasetCreated {
  dataset: DatasetMeta;
  quality: QualityReport;
}

export interface ParamSpec {
  type: "int" | "float" | "choice" | "bool";
  default: number | string | boolean;
  min: number | null;
  max: number | null;
  choices: Array<string | number> | null;
  description: string;
  editable: boolean;
}

export interface TradingHours {
  timezone: string;
  sessions: string[];
  weekdays: number[];
}

export interface StrategySpec {
  id: string;
  name: string;
  version: string;
  owner: string;
  category: "baseline" | "pilot_trader" | "third_party";
  status: "draft" | "active" | "archived";
  illustrative: boolean;
  usage_rights: string;
  implementation: string | null;
  description: string;
  market: Record<string, string>;
  timeframes: { execution: string; context: string[] };
  trading_hours: TradingHours;
  rules: Record<"buy" | "sell" | "wait" | "invalidation" | "exit", string[]>;
  params: Record<string, ParamSpec>;
  position_scaling: string;
  open_questions: string[];
}

export interface StrategyItem {
  key: string;
  runnable: boolean;
  problems: string[];
  spec: StrategySpec;
}

export interface ExecutionCosts {
  spread: number;
  slippage: number;
  commission_per_lot_per_side: number;
}

export interface ContractSpec {
  symbol: string;
  contract_size: number | null;
  min_lot: number | null;
  lot_step: number | null;
  max_lot: number | null;
  quote_currency: string | null;
  source: string;
}

export interface RiskConfig {
  risk_per_trade_pct: number;
  max_open_positions: number;
  max_daily_loss_pct: number;
  max_drawdown_pct: number;
  max_trades_per_day: number;
  max_losses_per_day: number | null;
  max_consecutive_losses: number | null;
  consecutive_loss_scope: "day" | "run";
  stop_after_daily_win: boolean;
  daily_limit_includes_planned_risk: boolean;
  drawdown_limit_includes_planned_risk: boolean;
  day_timezone: string;
  allow_martingale: false;
}

export interface BacktestConfig {
  initial_equity: number;
  account_currency: string;
  costs: ExecutionCosts;
  contract: ContractSpec;
  risk: RiskConfig;
  strategy_params: Record<string, number | string | boolean>;
  trading_hours: TradingHours | null;
  trade_start: string | null;
  trade_end: string | null;
  same_bar_policy: "stop_first";
  close_at_session_end: boolean;
  max_bars_in_trade: number | null;
}

export interface BacktestRequest {
  dataset_id: string;
  strategy_key: string;
  config?: BacktestConfig;
  label?: string;
}

export interface Metrics {
  initial_equity: number;
  final_equity: number;
  net_pnl: number;
  return_pct: number;
  trades: number;
  win_rate_pct: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  expectancy_r: number | null;
  payoff_ratio: number | null;
  max_dd_closed_pct: number;
  max_dd_mtm_pct: number;
  total_costs: number;
  commission_total: number;
  spread_cost_total: number;
  slippage_cost_total: number;
  pnl_before_costs?: number;
  losses_beyond_planned_risk?: number;
  signals: number;
  signals_entered: number;
  signals_rejected: number;
  rejection_reasons: Record<string, number>;
  exit_reasons: Record<string, number>;
  sample_sufficient: boolean;
  sample_note?: string;
  drawdown_note: string;
  unavailable: Record<string, string>;
  data_kind: DataKind;
}

export interface Manifest {
  run_id: string;
  created_at: string;
  software_version: string;
  engine_version: string;
  code_hash: string;
  execution_mode: "simulation";
  data_kind: DataKind;
  dataset: Omit<DatasetMeta, "quality">;
  strategy: {
    key: string;
    id: string;
    version: string;
    name: string;
    spec_hash: string;
    category: string;
    illustrative: boolean;
    params: Record<string, number | string | boolean>;
  };
  trading_hours: TradingHours;
  config: BacktestConfig;
  risk_policy?: RiskPolicy;
  evaluation_window: {
    trade_start: string | null;
    trade_end: string | null;
    first_evaluated_bar_open: string | null;
    last_evaluated_bar_close: string | null;
  };
  fill_assumptions: string[];
  result_hash: string;
}

export interface BacktestResponse {
  run_id: string;
  manifest: Manifest;
  metrics: Metrics;
}

export interface RunSummary {
  run_id: string;
  /** currency of the amounts of this run (M2); null = unknown -> amounts are not shown */
  account_currency: string | null;
  created_at: string;
  label: string;
  dataset_id: string;
  data_kind: DataKind;
  strategy_key: string;
  /** null when the run failed verification ("refusée"): no figure is shown for it */
  result_hash: string | null;
  integrity: "vérifiée" | "refusée";
  integrity_error?: string | null;
  trades: number | null;
  net_pnl: number | null;
  win_rate_pct: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  max_dd_mtm_pct: number | null;
}

export interface Trade {
  trade_id: number;
  decision_id: number;
  direction: "BUY" | "SELL";
  signal_time: string;
  entry_time: string;
  exit_time: string;
  bars_held: number;
  lots: number;
  entry_price: number;
  exit_price: number;
  stop_loss: number;
  take_profit: number | null;
  planned_risk: number;
  price_pnl: number;
  commission: number;
  net_pnl: number;
  r_multiple: number | null;
  spread_cost: number;
  slippage_cost: number;
  exit_reason: string;
  /** MAE/MFE are proven lower bounds on OHLC data (order inside a bar is unknown) */
  excursion_basis: "lower_bound_ohlc";
  mae_price: number;
  mfe_price: number;
  mae_r: number | null;
  mfe_r: number | null;
  gap_during_trade: boolean;
  equity_after: number;
}

export interface Decision {
  decision_id: number;
  signal_time: string;
  decision_time: string;
  entry_bar_time: string;
  direction: "BUY" | "SELL";
  strategy_reason: string;
  outcome: "ENTERED" | "REJECTED";
  reasons: string | null;
  lots: number;
  planned_risk: number;
  trade_id: number | null;
  [feature: `f_${string}`]: number | string | null;
}

export interface EquityPoint {
  timestamp: string;
  closed_equity: number;
  mtm_equity: number;
  position: number;
  /** drawdown of the MTM equity vs its running peak, %, <= 0 — computed by the Python engine */
  drawdown_mtm_pct: number;
}

export interface RiskPolicy {
  mode: "research" | "supervised";
  /** true only in supervised mode: the saved profile is enforced server-side (requests may only be stricter) */
  enforced: boolean;
  differs_from_saved_profile: boolean;
  saved_profile: RiskConfig;
  note: string;
}

export interface RiskPolicyInfo {
  mode: "research" | "supervised";
  enforced: boolean;
  saved_profile: RiskConfig;
}

export interface ReproduceResult {
  /** deterministic AND artifacts_intact */
  identical: boolean;
  /** re-running the engine gives the same result fingerprint (SHA-256, 64 hex) */
  deterministic: boolean;
  /** stored artefacts passed verification (a corrupted run is answered with HTTP 409 instead) */
  artifacts_intact: boolean;
  stored_hash: string;
  new_hash: string;
}

export type ExportName =
  | "trades.csv"
  | "decisions.csv"
  | "equity.csv.gz"
  | "metrics.json"
  | "manifest.json";

export interface ApiErrorBody {
  error: string;
  detail?: unknown;
}

/* ------------------------------------------------------------------ research layer (v0.4) */
/** [low, high] confidence bounds; null when unavailable */
export type Interval = [number | null, number | null];
export type Rating = "positif" | "négatif" | "non démontré" | "indisponible";
export type VerdictCode = "EDGE" | "NO_EDGE" | "NEGATIVE" | "INSUFFICIENT" | "INVALID";

export interface EdgeStudyRequest {
  dataset_id: string;
  strategy_key: string;
  config?: BacktestConfig;
  horizon_bars?: number;
  folds?: number;
  initial_train_fraction?: number;
}
export interface StudyFold {
  fold: number;
  test_start: string;
  test_end: string;
  n_train: number;
  n_validation?: number;
  n_test: number;
  skipped?: string;
  invalid?: string;
  threshold?: number | null;
  taken?: number;
  baseline_mean_r?: number;
  filtered_mean_r?: number | null;
  auc?: number | null;
}
export interface StudyVerdict {
  code: VerdictCode;
  confidence: string;
  title: string;
  text: string;
}
export interface MeanEstimate {
  mean_r: number | null;
  ci: Interval;
  win_rate?: number | null;
  /** share of bootstrap draws above zero — NOT the probability that the true expectancy is positive */
  share_of_draws_positive?: number;
  rating: Rating;
}
export interface StudyInference {
  method: string;
  n_units: number | null;
  n_units_taken: number | null;
  block_length: number | null;
  [key: string]: unknown;
}
export interface StudyResult {
  folds: StudyFold[];
  n_oos: number;
  n_taken?: number;
  coverage?: number;
  inference?: StudyInference;
  baseline?: MeanEstimate;
  filtered?: MeanEstimate;
  improvement?: MeanEstimate;
  auc?: { value: number | null; ci: Interval; rating: Rating };
  brier?: { model: number | null; reference: number | null; skill: number | null; note?: string };
  calibration?: Array<{ n: number; mean_predicted: number; observed_rate: number }>;
  cumulative?: Array<{ t: string; baseline_r: number; filtered_r: number }>;
  verdict: StudyVerdict;
}
export type OpinionCode = "NE PAS TRADER" | "IGNORER" | "FAVORABLE — EXPÉRIMENTAL";
export type SignalRole = "entraînement" | "résolu" | "non exploitable" | "nouveau" | null;
/** Prospective opinion on the latest signal: refused unless its outcome is still unknown and every gate passes. */
export interface SignalOpinion {
  opinion: OpinionCode;
  reasons: string[];
  role: SignalRole;
  signal_time: string | null;
  direction?: "BUY" | "SELL";
  decision_time?: string;
  trained_on?: number;
  train_until?: string | null;
  /** model score — NOT calibrated, not a probability of winning */
  score: number | null;
  score_kind?: string;
  threshold?: number | null;
  out_of_domain?: boolean;
}
export interface EdgeStudy {
  study_id: string;
  identity: Record<string, unknown>;
  created_at: string;
  software_version: string;
  engine_version: string;
  code_hash: string;
  method_status: "experimental" | string;
  execution_mode: "simulation";
  scope: string;
  dataset: { dataset_id: string; name: string; kind: DataKind; symbol: string; timeframe: string; start: string; end: string; raw_sha256?: string | null };
  strategy: { key: string; name: string; params: Record<string, number | string | boolean>; illustrative: boolean };
  settings: { horizon_bars: number; folds: number; initial_train_fraction: number; l2: number; n_boot: number; min_train: number };
  costs: ExecutionCosts;
  feature_set: string;
  features: Array<{ feature: string; label: string }>;
  signals: { candidates: number; labelled: number; exit_reasons: Record<string, number> };
  multiple_testing: { family: string; studies_in_family: number; alpha: number; rule: string; registry_entry: string };
  result: StudyResult;
  final_model: {
    status: "ok" | "invalide" | "absent";
    error?: string;
    scope?: string;
    trained_on?: number;
    base_rate?: number;
    weights: Array<{ feature: string; label: string; weight: number }>;
    opinion: SignalOpinion;
  };
  numerical_issues: string[];
}
export interface EdgeStudySummary {
  study_id: string;
  created_at: string;
  dataset_id: string | null;
  dataset_name: string;
  data_kind: DataKind | null;
  strategy_key: string | null;
  /** null when the stored study was refused by the integrity check */
  verdict: VerdictCode | null;
  n_oos: number | null;
  integrity: "vérifiée" | "refusée";
  integrity_error?: string;
}
export interface Robustness {
  n_trades: number;
  min_trades: number;
  confidence: number;
  n_boot: number;
  sufficient: boolean;
  note?: string;
  rating?: "insuffisant" | Rating;
  expectancy_r?: { value: number; ci: Interval; p_positive: number };
  expectancy_money?: { value: number; ci: Interval };
  win_rate?: { value: number; ci: Interval };
  max_drawdown_pct?: { actual: number; median: number; p95: number; worst: number; limit: number; p_breach_limit: number };
}

// ---------------------------------------------------------------- EA audit (offline MT5 report, v0.4.1+)
export type EaVerdictCode = "STOP_OUT" | "MARTINGALE" | "GRID" | "RISK_SIGNS" | "NO_SIGNATURE" | "INSUFFICIENT";
export interface EaFlag {
  code: "STOP_OUT" | "END_OF_TEST_CLOSE" | "STACKING" | "AVERAGING_DOWN" | "LOT_ESCALATION" | "MARTINGALE_AFTER_LOSS" | "ASYMMETRIC" | "OPEN_AT_END";
  label: string;
  detail: string;
}
export interface EaStress {
  time: string;
  symbol: string;
  net_lots: number;
  price: number;
  balance: number;
  positions: number;
  equity_estimate: number;
  loss_per_price_unit: number;
  adverse_move_to_lose_half: number;
  adverse_move_to_zero: number;
  direction: "baisse" | "hausse";
  note: string;
}
/** Behavioural audit computed by the Python engine (ea_audit/) — nothing is stored, nothing is traded. */
export interface EaAudit {
  analysis_version: string;
  source: { format: "html" | "csv"; encoding: string; header: string[]; deals_read: number; rows_rejected: number;
    rejected_examples: Array<{ row: number; reason: string; cells: string[] }>; rows_ignored: number };
  period: { start: string; end: string } | null;
  symbols: string[];
  contract: { contract_size: number; note: string };
  verdict: { code: EaVerdictCode; title: string; text: string };
  flags: EaFlag[];
  counts: { stop_out_closes: number; end_of_test_closes: number; trading_deals: number; balance_operations: number; entries: number; adds_to_open_stack: number;
    adds_against_open_loss: number; baskets_closed: number; baskets_open_at_end: number; inout_deals: number;
    unmatched_close_volume: number };
  exposure: { max_positions_same_direction: number; max_gross_lots: number; min_entry_lot: number | null;
    max_entry_lot: number | null; median_add_ratio: number | null; max_add_ratio: number | null;
    median_first_lot_ratio_after_loss: number | null; median_first_lot_ratio_after_win: number | null;
    worst_adverse_distance_while_adding: number };
  baskets: { count: number; win_rate: number | null; median_win: number | null; median_loss: number | null;
    worst_loss: number | null; best_win: number | null; net_total: number; definition: string };
  out_deals: { count: number; net_total: number };
  stress: EaStress | null;
  thresholds: Record<string, number>;
  limits: string[];
  file: { name: string; bytes: number };
  stored: false;
  note: string;
}
/** Files found (read-only) in the MT5 terminal installed on this machine. */
export interface Mt5LocalFile {
  id: string;
  name: string;
  folder: string;
  bytes: number;
  too_large: boolean;
  modified: string;
}
export interface Mt5LocalFiles {
  available: boolean;
  root: string | null;
  files: Mt5LocalFile[];
  note: string;
}

// ---------------------------------------------------------------- External Bot Lab (v0.5): imported MT5 simulations
export type ExternalValidation = "validé" | "partiel" | "écarts";
export interface ExternalSimSummary {
  sim_id: string;
  integrity: "vérifiée" | "refusée";
  integrity_error?: string;
  imported_at: string | null;
  robot?: string | null;
  self_identification?: string | null;
  symbol?: string | null;
  timeframe?: string | null;
  server?: string | null;
  requested_period?: string | null;
  observed_period?: [string | null, string | null];
  ends_early?: boolean;
  net_profit?: number | null;
  total_trades?: number | null;
  balance_dd_maximal_pct?: number | null;
  collapse_drawdown?: number | null;
  behaviour?: EaVerdictCode;
  validation?: ExternalValidation;
  source_name?: string;
  source_format?: string;
  config_key?: string;
  test_key?: string;
  same_test_sources?: number;
  contradictory?: boolean;
}
export interface ExternalSimList {
  simulations: ExternalSimSummary[];
  robots: Array<{ robot: string; simulations: number }>;
  log_error: string | null;
}
export interface ExternalTrade {
  trade_no: number;
  side: "BUY" | "SELL";
  symbol: string;
  volume: number;
  entry_deal: string;
  entry_time: string;
  entry_price: number;
  exit_deal: string;
  exit_time: string;
  exit_price: number;
  exit_comment: string;
  close_reason: "stop-out" | "fin du test" | "take-profit" | "stop-loss" | "robot";
  profit: number;
  swap: number;
  commission: number;
  net: number;
}
export interface ExternalDeal {
  seq: number;
  time: string;
  deal: string;
  symbol: string;
  type: "buy" | "sell" | "balance" | "other";
  direction: "in" | "out" | "inout" | "";
  volume: number;
  price: number;
  commission: number;
  swap: number;
  profit: number;
  balance: number | null;
  comment: string;
}
export interface ExternalReconRow {
  metric: string;
  label: string;
  reported: number;
  computed: number | null;
  tolerance: number;
  status: "concordant" | "écart" | "non calculable";
}
export interface ExternalTimelinePoint {
  t: string;
  balance: number;
  equity_est: number | null;
  long_lots: number | null;
  short_lots: number | null;
  event: string;
}
export interface ExternalCollapse {
  peak_time: string;
  peak_balance: number;
  trough_time: string;
  trough_balance: number;
  drawdown: number;
  drawdown_pct: number | null;
  losing_trades: number;
  losing_total: number;
  lots_involved: number;
  entries_involved: number;
  close_reasons: Record<string, number>;
  trades: ExternalTrade[];
  first_entry: string | null;
  last_entry: string | null;
}
export interface ExternalSim {
  sim_id: string;
  kind: string;
  identity: Record<string, unknown>;
  test_key: string;
  config_key: string;
  source: { name: string; sha256: string; format: string; encoding: string; report_file: string; archive_members: Array<{ name: string; bytes: number }> };
  declared_manifest: { file: string; readable: boolean; content?: Record<string, unknown> } | null;
  robot: { name: string | null; self_identification: string | null; declared_version: string | null; website: string | null };
  environment: { server: string | null; build: string | null; company: string | null; symbol: string | null; timeframe: string | null;
    requested_period: string | null; initial_deposit: number | null; currency: string | null; leverage: string | null;
    history_quality: string | null; bars: string | null; ticks: string | null; modelling: string | null };
  inputs: Array<{ name: string; value: string }>;
  risk_inputs: Array<{ name: string; value: string }>;
  reported: Record<string, { label: string; raw: string; value: number | null; pct: number | null }>;
  recomputed: Record<string, number | null>;
  reconciliation: ExternalReconRow[];
  validation: { status: ExternalValidation; checks: Array<{ check: string; ok: boolean | null; detail: string }>;
    rejected_rows: Array<{ table: string; row: number; reason: string }>; duplicates: string[] };
  period: { requested_raw: string; requested_start: string | null; requested_end: string | null; first_deal: string | null;
    last_deal: string | null; ends_early: boolean; evidence: string[]; interpretation: string };
  contract_size: { value: number; source: string; samples?: number };
  counts: { orders: number; deals: number; trading_deals: number; positions_opened: number; closing_deals: number; trades: number; balance_operations: number };
  pairing: { rule: string; closes_checked: number; closes_matched: number; unmatched_close_volume: number; note: string; alternatives: Record<string, number> };
  deals: ExternalDeal[];
  trades: ExternalTrade[];
  timeline: ExternalTimelinePoint[];
  lot_progression: Array<{ t: string; lot: number; balance_before: number; lot_per_10k: number | null }>;
  monthly: Array<{ month: string; trades: number; wins: number; net: number; worst: number; lots: number }>;
  collapse: ExternalCollapse | null;
  largest_losses: ExternalTrade[];
  behaviour: Pick<EaAudit, "verdict" | "flags" | "stress" | "exposure">;
  findings: { observed: Array<{ fact: string; source: string }>; hypotheses: Array<{ statement: string; evidence: string; status: string }>; note: string };
  availability: Record<string, boolean | null | string>;
  limits: string[];
}
export type WhatIfQualification = "exact" | "approximation" | "non_simulable";
export interface WhatIfRule {
  rule: string;
  label: string;
  unit: string;
  default: number | null;
}
export interface WhatIfResult {
  rule: string;
  label: string;
  value: number | null;
  unit: string;
  qualification: WhatIfQualification;
  baseline: { net: number; final_balance: number; max_realised_dd: number; max_realised_dd_pct: number; lowest_balance: number };
  result: null | { net: number; final_balance: number; max_realised_dd: number; max_realised_dd_pct: number; lowest_balance: number;
    kept_trades: number; removed_trades: number; stop_out_kept: boolean; triggered_at?: string | null };
  explanation: string;
  caveats: string[];
  what_to_do: string | null;
}
export interface ExternalImportResult {
  outcome: "créée" | "déjà importée";
  sim_id: string;
  validation: ExternalSim["validation"];
}
