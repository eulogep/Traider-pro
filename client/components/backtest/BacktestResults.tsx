import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, BarChart3, Dices, Fingerprint, ListOrdered, ShieldX } from "lucide-react";
import type { BacktestResponse } from "@shared/quant-api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { quantApi } from "@/lib/quantApi";
import { fmtDateTime } from "@/lib/format";
import { KindBadge } from "./DatasetPanel";
import { PerformanceCharts } from "./PerformanceCharts";
import { RejectionsPanel } from "./RejectionsPanel";
import { RobustnessPanel } from "./RobustnessPanel";
import { ResultsSummary } from "./ResultsSummary";
import { TraceabilityPanel } from "./TraceabilityPanel";
import { TradesTable } from "./TradesTable";

/** Every figure below comes from the Python engine (persisted, verified run). Nothing is computed here. */
export function BacktestResults({ run }: { run: BacktestResponse }) {
  const { run_id: runId, metrics: m, manifest } = run;
  const cur = manifest.config.account_currency;
  const trades = useQuery({ queryKey: ["trades", runId], queryFn: () => quantApi.getTrades(runId) });
  const rows = trades.data ?? [];

  return (
    <div className="space-y-5" data-testid="results">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <KindBadge kind={manifest.data_kind} />
        <span className="text-sm font-medium">
          {manifest.strategy.name} <span className="text-muted-foreground">v{manifest.strategy.version}</span>
        </span>
        <span className="text-xs text-muted-foreground">
          {manifest.dataset.name} · calculé le {fmtDateTime(manifest.created_at)} · run <code data-testid="run-id">{runId}</code>
        </span>
      </div>

      {manifest.data_kind === "synthetic" && (
        <div role="alert" data-testid="synthetic-warning"
          className="flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" />
          <span><strong>Données synthétiques (fausses cotations).</strong> Ces résultats vérifient le logiciel ; ils ne disent
            rien du marché réel et ne doivent jamais être présentés comme une performance.</span>
        </div>
      )}
      {manifest.data_kind === "historical" && (
        <div className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          Historique déclaré par l'utilisateur · simulation sur bougies OHLC avec coûts fixes hypothétiques : ce n'est pas une
          exécution réelle et cela ne garantit aucun résultat futur.
        </div>
      )}

      <ResultsSummary m={m} currency={cur} />
      {manifest.risk_policy && (
        <p className="text-xs text-muted-foreground" data-testid="risk-policy-note">
          Politique de risque : {manifest.risk_policy.note}
          {manifest.risk_policy.differs_from_saved_profile ? " Ce run diffère du profil enregistré." : ""}
        </p>
      )}

      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 md:w-auto">
          <TabsTrigger value="performance" data-testid="tab-performance">
            <BarChart3 className="mr-1.5 h-4 w-4" />Performance
          </TabsTrigger>
          <TabsTrigger value="trades" data-testid="tab-trades">
            <ListOrdered className="mr-1.5 h-4 w-4" />Transactions ({m.trades})
          </TabsTrigger>
          <TabsTrigger value="rejections" data-testid="tab-rejections">
            <ShieldX className="mr-1.5 h-4 w-4" />Signaux refusés ({m.signals_rejected})
          </TabsTrigger>
          <TabsTrigger value="robustness" data-testid="tab-robustness">
            <Dices className="mr-1.5 h-4 w-4" />Robustesse
          </TabsTrigger>
          <TabsTrigger value="trace" data-testid="tab-trace">
            <Fingerprint className="mr-1.5 h-4 w-4" />Traçabilité
          </TabsTrigger>
        </TabsList>
        <TabsContent value="performance">
          <PerformanceCharts runId={runId} m={m} currency={cur} trades={rows} />
        </TabsContent>
        <TabsContent value="trades">
          {trades.isLoading && <div className="h-40 animate-pulse rounded-lg bg-muted/40" />}
          {trades.isError && <p className="text-sm text-red-500">{(trades.error as Error).message}</p>}
          {trades.data && <TradesTable trades={rows} currency={cur} />}
        </TabsContent>
        <TabsContent value="rejections">
          <RejectionsPanel m={m} />
        </TabsContent>
        <TabsContent value="robustness">
          <RobustnessPanel runId={runId} currency={cur} />
        </TabsContent>
        {/* forceMount: the verification verdict survives tab switches; it is reset per run by the parent `key` (M1) */}
        <TabsContent value="trace" forceMount className="data-[state=inactive]:hidden">
          <TraceabilityPanel run={run} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
