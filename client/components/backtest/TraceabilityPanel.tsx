import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Download, RefreshCw, ShieldAlert } from "lucide-react";
import type { BacktestResponse, ExportName } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { quantApi } from "@/lib/quantApi";
import { fmtDateTime } from "@/lib/format";

const EXPORTS: Array<[ExportName, string]> = [
  ["trades.csv", "Trades CSV"], ["decisions.csv", "Décisions CSV"], ["equity.csv.gz", "Courbe CSV.gz"],
  ["metrics.json", "Métriques JSON"], ["manifest.json", "Manifeste JSON"],
];

function Row({ k, v, testId }: { k: string; v: React.ReactNode; testId?: string }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 border-b border-border/40 py-1.5 text-xs last:border-0">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="break-all font-mono" data-testid={testId}>{v}</dd>
    </div>
  );
}

export function TraceabilityPanel({ run }: { run: BacktestResponse }) {
  const { run_id: runId, manifest } = run;
  const repro = useMutation({ mutationFn: () => quantApi.reproduce(runId) });
  const w = manifest.evaluation_window;
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="space-y-3 rounded-xl border border-border/60 bg-card/80 p-4">
        <h3 className="text-sm font-semibold">Identité du run</h3>
        <dl>
          <Row k="Run" v={runId} />
          <Row k="Données" v={`${manifest.dataset.dataset_id} · ${manifest.dataset.symbol} ${manifest.dataset.timeframe}`} />
          <Row k="Stratégie" v={`${manifest.strategy.key} (spec ${manifest.strategy.spec_hash})`} />
          <Row k="Code moteur" v={`${manifest.code_hash} · ${manifest.engine_version}`} />
          <Row k="Empreinte résultats" v={manifest.result_hash} testId="result-hash" />
          <Row k="Période évaluée" v={w ? `${fmtDateTime(w.first_evaluated_bar_open)} → ${fmtDateTime(w.last_evaluated_bar_close)}` : "—"} />
          <Row k="Politique de risque" v={manifest.risk_policy ? `${manifest.risk_policy.mode}${manifest.risk_policy.enforced ? " (imposée)" : " (hypothèses)"}` : "—"} />
        </dl>
        <div className="flex flex-wrap gap-2 pt-1">
          {EXPORTS.map(([name, label]) => (
            <Button key={name} asChild variant="outline" size="sm">
              <a href={quantApi.exportUrl(runId, name)} download><Download className="mr-1.5 h-3.5 w-3.5" />{label}</a>
            </Button>
          ))}
        </div>
      </section>
      <section className="space-y-3 rounded-xl border border-border/60 bg-card/80 p-4">
        <h3 className="text-sm font-semibold">Vérification</h3>
        <p className="text-xs text-muted-foreground">
          « Reproduire » relit les fichiers stockés (empreintes SHA-256, cohérence journal ↔ courbe ↔ métriques), puis relance
          le moteur avec la même configuration et compare les empreintes.
        </p>
        <Button variant="secondary" size="sm" onClick={() => repro.mutate()} disabled={repro.isPending} data-testid="reproduce">
          <RefreshCw className={`mr-2 h-4 w-4 ${repro.isPending ? "animate-spin" : ""}`} />
          {repro.isPending ? "Vérification…" : "Reproduire"}
        </Button>
        {repro.data && (
          <p data-testid="reproduce-result"
            className={`flex items-start gap-2 rounded-lg border p-2 text-sm ${repro.data.identical
              ? "border-green-500/30 bg-green-500/10 text-green-300" : "border-red-500/30 bg-red-500/10 text-red-300"}`}>
            {repro.data.identical ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />}
            <span>
              {repro.data.identical ? "Résultats identiques" : "RÉSULTATS DIFFÉRENTS"} — artefacts stockés{" "}
              {repro.data.artifacts_intact ? "intacts" : "NON VÉRIFIÉS"} · recalcul{" "}
              {repro.data.deterministic ? "déterministe" : "DIFFÉRENT"} · empreinte {repro.data.stored_hash.slice(0, 16)}…
            </span>
          </p>
        )}
        {repro.isError && <p className="text-sm text-red-400">{(repro.error as Error).message}</p>}
        <details className="text-xs">
          <summary className="cursor-pointer font-medium">Hypothèses de simulation ({manifest.fill_assumptions.length})</summary>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-muted-foreground">
            {manifest.fill_assumptions.map((a) => <li key={a}>{a}</li>)}
          </ul>
        </details>
      </section>
    </div>
  );
}
