/**
 * Single HTTP client for the Python quant API (v1). The browser reaches it through the
 * Vite dev proxy (`/api/v1` → 127.0.0.1:8765); tests pass an absolute base URL.
 * No financial computation happens here.
 */
import type {
  ApiErrorBody,
  BacktestConfig,
  BacktestRequest,
  BacktestResponse,
  DatasetCreated,
  DatasetMeta,
  DatasetSummary,
  Decision,
  EaAudit,
  ExternalImportResult,
  ExternalSim,
  ExternalSimList,
  Mt5LocalFiles,
  WhatIfResult,
  WhatIfRule,
  EdgeStudy,
  EdgeStudyRequest,
  EdgeStudySummary,
  EquityPoint,
  ExportName,
  Health,
  ReproduceResult,
  RiskPolicyInfo,
  Robustness,
  RunSummary,
  StrategyItem,
  Trade,
} from "@shared/quant-api";

export class QuantApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "QuantApiError";
  }
}

export interface ImportDatasetInput {
  file: Blob;
  filename: string;
  name: string;
  symbol: string;
  source: string;
  kind: "historical" | "synthetic";
  priceSide?: "bid" | "mid";
  sourceTimezone?: string;
  expectedTimeframe?: string;
  notes?: string;
}

export function createQuantClient(baseUrl = "", fetchImpl: typeof fetch = fetch) {
  const root = `${baseUrl}/api/v1`;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetchImpl(`${root}${path}`, init);
    } catch (cause) {
      throw new QuantApiError(
        0,
        "API Python injoignable. Lancez-la avec « pnpm quant:api » (127.0.0.1:8765).",
        String(cause),
      );
    }
    const text = await res.text();
    let body: unknown = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = null;
    }
    if (!res.ok) {
      const err = body as ApiErrorBody | null;
      const message =
        res.status === 502 || res.status === 504 || (res.status === 500 && !err)
          ? "API Python injoignable. Lancez-la avec « pnpm quant:api » (127.0.0.1:8765)."
          : err?.error ?? `Erreur HTTP ${res.status}`;
      throw new QuantApiError(res.status, message, err?.detail);
    }
    return body as T;
  }

  // Every mutation carries X-ATO-Request: the API refuses mutations without it (a foreign web page
  // cannot add a custom header without a CORS preflight, which the API denies).
  const LOCAL = { "X-ATO-Request": "1" } as const;
  const json = (method: "POST", payload: unknown): RequestInit => ({
    method,
    headers: { "Content-Type": "application/json", ...LOCAL },
    body: JSON.stringify(payload),
  });

  return {
    health: () => request<Health>("/health"),
    listDatasets: () => request<DatasetSummary[]>("/datasets"),
    getDataset: (id: string) => request<DatasetMeta>(`/datasets/${encodeURIComponent(id)}`),
    createDemoDataset: (seed = 42, days = 10) =>
      request<DatasetCreated>("/datasets/demo", json("POST", { seed, days })),
    importDataset: (input: ImportDatasetInput) => {
      const form = new FormData();
      form.append("file", input.file, input.filename);
      form.append("name", input.name);
      form.append("symbol", input.symbol);
      form.append("source", input.source);
      form.append("kind", input.kind);
      form.append("price_side", input.priceSide ?? "bid");
      if (input.sourceTimezone) form.append("source_timezone", input.sourceTimezone);
      if (input.expectedTimeframe) form.append("expected_timeframe", input.expectedTimeframe);
      form.append("notes", input.notes ?? "");
      return request<DatasetCreated>("/datasets/import", { method: "POST", body: form, headers: LOCAL });
    },
    listStrategies: () =>
      request<{ strategies: StrategyItem[]; errors: Record<string, string> }>("/strategies"),
    getDefaults: () => request<BacktestConfig>("/settings/defaults"),
    rejectionLabels: () => request<Record<string, string>>("/reference/rejection-reasons"),
    riskPolicy: () => request<RiskPolicyInfo>("/settings/risk-policy"),
    runBacktest: (req: BacktestRequest) =>
      request<BacktestResponse>("/backtests", json("POST", req)),
    listBacktests: () => request<RunSummary[]>("/backtests"),
    getBacktest: (runId: string) =>
      request<BacktestResponse>(`/backtests/${encodeURIComponent(runId)}`),
    getTrades: (runId: string) =>
      request<Trade[]>(`/backtests/${encodeURIComponent(runId)}/trades`),
    getDecisions: (runId: string, outcome?: "ENTERED" | "REJECTED") =>
      request<{ total: number; items: Decision[] }>(
        `/backtests/${encodeURIComponent(runId)}/decisions${outcome ? `?outcome=${outcome}` : ""}`,
      ),
    getEquity: (runId: string, maxPoints = 1500) =>
      request<{ total_points: number; points: EquityPoint[] }>(
        `/backtests/${encodeURIComponent(runId)}/equity?max_points=${maxPoints}`,
      ),
    reproduce: (runId: string) =>
      request<ReproduceResult>(
        `/backtests/${encodeURIComponent(runId)}/reproduce`,
        { method: "POST", headers: LOCAL },
      ),
    getRobustness: (runId: string) =>
      request<Robustness>(`/backtests/${encodeURIComponent(runId)}/robustness`),
    runEdgeStudy: (req: EdgeStudyRequest) => request<EdgeStudy>("/research/edge-studies", json("POST", req)),
    analyzeEaReport: (file: Blob, filename: string, contractSize?: number) => {
      const form = new FormData();
      form.append("file", file, filename);
      if (contractSize != null) form.append("contract_size", String(contractSize));
      return request<EaAudit>("/ea-reports/analyze", { method: "POST", body: form, headers: LOCAL });
    },
    listMt5Files: () => request<Mt5LocalFiles>("/mt5/local-files"),
    importExternalSim: (file: Blob, filename: string) => {
      const form = new FormData();
      form.append("file", file, filename);
      return request<ExternalImportResult>("/external-sims", { method: "POST", body: form, headers: LOCAL });
    },
    importExternalSimFromMt5: (id: string) =>
      request<ExternalImportResult>(`/external-sims/from-mt5/${encodeURIComponent(id)}`, { method: "POST", headers: LOCAL }),
    listExternalSims: () => request<ExternalSimList>("/external-sims"),
    getExternalSim: (id: string) => request<ExternalSim>(`/external-sims/${encodeURIComponent(id)}`),
    whatIfRules: () => request<WhatIfRule[]>("/external-sims/what-if-rules"),
    runWhatIf: (id: string, rule: string, value?: number) =>
      request<WhatIfResult>(
        `/external-sims/${encodeURIComponent(id)}/what-if?rule=${encodeURIComponent(rule)}${value != null ? `&value=${value}` : ""}`,
      ),
    analyzeMt5File: (id: string, contractSize?: number) =>
      request<EaAudit>(
        `/mt5/local-files/${encodeURIComponent(id)}/analyze${contractSize != null ? `?contract_size=${contractSize}` : ""}`,
        { method: "POST", headers: LOCAL },
      ),
    listEdgeStudies: () => request<EdgeStudySummary[]>("/research/edge-studies"),
    getEdgeStudy: (id: string) => request<EdgeStudy>(`/research/edge-studies/${encodeURIComponent(id)}`),
    exportUrl: (runId: string, name: ExportName) =>
      `${root}/backtests/${encodeURIComponent(runId)}/export/${name}`,
  };
}

export type QuantClient = ReturnType<typeof createQuantClient>;

export const quantApi = createQuantClient();
