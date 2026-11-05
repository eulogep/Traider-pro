import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Activity, CheckCircle2, Cpu, Database, FlaskConical, History, Play, Settings2, WifiOff } from "lucide-react";
import type { BacktestConfig } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Page, PageHeader } from "@/components/layout/Page";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { ConfigPanel } from "@/components/backtest/ConfigPanel";
import { DatasetPanel } from "@/components/backtest/DatasetPanel";
import { QuantApiError, quantApi } from "@/lib/quantApi";
import { fmtSignedMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

/** "Until D (included)": the evaluation ends when the last bar of D CLOSES, i.e. at D+1 00:00 UTC (B3 semantics). */
function endOfDayExclusive(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().replace(".000Z", "Z");
}

function Step({ n, label, done }: { n: number; label: string; done: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span className={cn("flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold",
        done ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground")}>
        {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : n}
      </span>
      <span className={done ? "text-foreground" : "text-muted-foreground"}>{label}</span>
    </li>
  );
}

/**
 * Backtesting — every figure on this page comes from the Python quant engine
 * (React → /api/v1 → FastAPI → engine). Nothing is computed or generated here.
 */
export default function Backtest() {
  const qc = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => quantApi.listDatasets(), enabled: online });
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => quantApi.listStrategies(), enabled: online });
  const defaults = useQuery({ queryKey: ["defaults"], queryFn: () => quantApi.getDefaults(), enabled: online });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => quantApi.listBacktests(), enabled: online });
  const policy = useQuery({ queryKey: ["risk-policy"], queryFn: () => quantApi.riskPolicy(), enabled: online });

  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [strategyKey, setStrategyKey] = useState<string | null>(null);
  const [config, setConfig] = useState<BacktestConfig | null>(null);
  const [tradeFrom, setTradeFrom] = useState("");
  const [tradeTo, setTradeTo] = useState("");
  const [params] = useSearchParams();
  // `?run=<id>` opens a stored run directly (links from the dashboard)
  const [runId, setRunId] = useState<string | null>(() => params.get("run"));

  useEffect(() => {
    if (!datasetId && datasets.data?.length) setDatasetId(datasets.data[0].dataset_id);
  }, [datasets.data, datasetId]);
  useEffect(() => {
    const first = strategies.data?.strategies.find((s) => s.runnable);
    if (!strategyKey && first) setStrategyKey(first.key);
  }, [strategies.data, strategyKey]);
  useEffect(() => {
    if (!config && defaults.data) setConfig(defaults.data);
  }, [defaults.data, config]);
  useEffect(() => {
    if (!runId && runs.data?.length) setRunId(runs.data[0].run_id);
  }, [runs.data, runId]);

  const selectStrategy = (key: string) => {
    setStrategyKey(key);
    if (config) setConfig({ ...config, strategy_params: {} }); // params belong to one strategy
  };

  const runMutation = useMutation({
    mutationFn: () => {
      if (!datasetId || !strategyKey || !config) throw new QuantApiError(400, "Sélectionnez des données et une stratégie.");
      return quantApi.runBacktest({
        dataset_id: datasetId,
        strategy_key: strategyKey,
        config: {
          ...config,
          trade_start: tradeFrom ? `${tradeFrom}T00:00:00Z` : null,
          trade_end: tradeTo ? endOfDayExclusive(tradeTo) : null,
        },
      });
    },
    onSuccess: (r) => {
      qc.setQueryData(["run", r.run_id], r);
      void qc.invalidateQueries({ queryKey: ["runs"] });
      setRunId(r.run_id);
    },
  });

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => quantApi.getBacktest(runId as string),
    enabled: online && !!runId,
  });

  const canRun = online && !!datasetId && !!strategyKey && !!config && !runMutation.isPending;
  const runError = runMutation.error as QuantApiError | null;
  const runButton = (testId: string, wide = false) => (
    <Button onClick={() => runMutation.mutate()} disabled={!canRun} data-testid={testId} className={cn(wide && "w-full")} size={wide ? "lg" : "default"}>
      {runMutation.isPending
        ? <><Activity className="mr-2 h-4 w-4 animate-spin" />Simulation en cours…</>
        : <><Play className="mr-2 h-4 w-4" />Lancer le backtest</>}
    </Button>
  );

  return (
    <Page wide>
      <PageHeader
        icon={FlaskConical}
        title="Backtesting"
        status="engine"
        description="Simulation historique calculée par le moteur Python — aucun ordre n'est transmis."
        actions={
          <>
            <span data-testid="engine-status"
              className={cn("inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
                online ? "border-green-500/40 bg-green-500/10 text-green-300" : "border-red-500/40 bg-red-500/10 text-red-300")}>
              {online ? <Cpu className="mr-1.5 h-3.5 w-3.5" /> : <WifiOff className="mr-1.5 h-3.5 w-3.5" />}
              {health.isLoading ? "Connexion au moteur…" : online
                ? `Moteur ${health.data.engine_version} · simulation`
                : "Moteur Python hors ligne"}
            </span>
            {runButton("run-backtest")}
          </>
        }
      />

        {health.isError && (
          <section data-testid="api-offline" className="mx-auto max-w-xl space-y-3 rounded-xl border border-red-500/40 bg-card p-6 text-sm">
            <p className="flex items-center gap-2 text-base font-semibold"><WifiOff className="h-5 w-5 text-red-400" />API Python injoignable</p>
            <p className="text-muted-foreground">Aucun résultat ne peut être affiché et aucun chiffre de remplacement n'est montré.</p>
            <p>Démarrez-la dans un second terminal : <code className="rounded bg-muted px-1.5 py-0.5">pnpm quant:api</code> (écoute 127.0.0.1:8765), puis :</p>
            <Button variant="outline" size="sm" onClick={() => void health.refetch()}>Réessayer</Button>
          </section>
        )}

        {online && (
          <div className="grid items-start gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
            {/* ---------------- configuration column */}
            <aside className="space-y-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto xl:pr-1">
              <DatasetPanel datasets={datasets.data ?? []} selectedId={datasetId} onSelect={setDatasetId} />
              {config && strategies.data ? (
                <ConfigPanel
                  strategies={strategies.data.strategies}
                  strategyKey={strategyKey}
                  onStrategy={selectStrategy}
                  config={config}
                  onConfig={setConfig}
                  tradeFrom={tradeFrom}
                  tradeTo={tradeTo}
                  onPeriod={(f, t) => { setTradeFrom(f); setTradeTo(t); }}
                  policy={policy.data}
                />
              ) : (
                <div className="h-64 animate-pulse rounded-xl bg-muted/40" />
              )}
              <div className="rounded-xl border border-border/60 bg-card p-3">{runButton("run-backtest-side", true)}</div>
            </aside>

            {/* ---------------- results column */}
            <main className="min-w-0 space-y-5">
              {runError && (
                <div role="alert" data-testid="run-error"
                  className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
                  <strong>Backtest refusé : </strong>{runError.message}
                  {Array.isArray(runError.detail) && (
                    <ul className="mt-1 list-disc pl-5">
                      {(runError.detail as Array<{ loc?: unknown[]; msg?: string }>).slice(0, 6).map((d, i) => (
                        <li key={i}>{(d.loc ?? []).join(" › ")} : {d.msg}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {(runs.data?.length ?? 0) > 0 && (
                <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/60 bg-card/60 px-3 py-2">
                  <History className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Run affiché</span>
                  <Select value={runId ?? undefined} onValueChange={setRunId}>
                    <SelectTrigger className="h-8 w-[40rem] max-w-full" data-testid="run-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {runs.data?.map((r) => (
                        <SelectItem key={r.run_id} value={r.run_id}>
                          {r.created_at.slice(0, 16).replace("T", " ")} · {r.strategy_key} · {r.data_kind} · {r.trades} trades
                          {r.account_currency ? ` · ${fmtSignedMoney(r.net_pnl, r.account_currency)}` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="ml-auto text-xs text-muted-foreground">{runs.data?.length} run(s) enregistré(s)</span>
                </div>
              )}

              {!runId && !runMutation.isPending && (
                <section data-testid="no-run" className="rounded-xl border border-dashed border-border p-8">
                  <h2 className="text-lg font-semibold">Aucun backtest pour l'instant</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Aucune performance n'est affichée tant qu'aucune simulation n'a été calculée par le moteur.
                  </p>
                  <ol className="mt-5 space-y-3">
                    <Step n={1} label="Choisir ou importer des données (ou générer la démo synthétique)" done={!!datasetId} />
                    <Step n={2} label="Choisir la stratégie et ses paramètres autorisés" done={!!strategyKey} />
                    <Step n={3} label="Vérifier capital, coûts et période" done={!!config} />
                    <Step n={4} label="Lancer le backtest" done={false} />
                  </ol>
                  <div className="mt-6 flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5"><Database className="h-3.5 w-3.5" />Données validées, jamais comblées</span>
                    <span className="flex items-center gap-1.5"><Settings2 className="h-3.5 w-3.5" />Paramètres bornés par la spécification</span>
                  </div>
                </section>
              )}
              {runMutation.isPending && !run.data && <div className="h-96 animate-pulse rounded-xl bg-muted/40" />}
              {run.isError && <p className="text-sm text-red-500">{(run.error as Error).message}</p>}
              {/* key = run id: pagination / verification verdict never leak from one run to another (M1) */}
              {run.data && <BacktestResults key={run.data.run_id} run={run.data} />}
            </main>
          </div>
        )}
    </Page>
  );
}
