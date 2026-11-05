import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, History, Microscope, Play } from "lucide-react";
import type { VerdictCode } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Callout, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { StudyView } from "@/components/research/StudyView";
import { QuantApiError, quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

const VERDICT_LABEL: Record<VerdictCode, string> = {
  EDGE: "indice (expérimental)",
  NO_EDGE: "non démontré",
  NEGATIVE: "perte mesurée",
  INSUFFICIENT: "insuffisant",
  INVALID: "invalide",
};

/**
 * Validation & prediction — out-of-sample edge studies computed by the Python research layer
 * (labels → walk-forward model → bootstrap verdict). Nothing is computed here; nothing is traded.
 */
export default function Research() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => quantApi.listDatasets(), enabled: online });
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => quantApi.listStrategies(), enabled: online });
  const studies = useQuery({ queryKey: ["studies"], queryFn: () => quantApi.listEdgeStudies(), enabled: online });
  const runnable = (strategies.data?.strategies ?? []).filter((s) => s.runnable);

  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [strategyKey, setStrategyKey] = useState<string | null>(null);
  const [horizon, setHorizon] = useState("240");
  const [folds, setFolds] = useState("4");
  const studyId = params.get("study") ?? studies.data?.find((s) => s.verdict != null)?.study_id ?? null;

  useEffect(() => {
    if (!datasetId && datasets.data?.length) setDatasetId(datasets.data[0].dataset_id);
  }, [datasets.data, datasetId]);
  useEffect(() => {
    if (!strategyKey && runnable.length) setStrategyKey(runnable[0].key);
  }, [runnable, strategyKey]);

  const study = useQuery({ queryKey: ["study", studyId], queryFn: () => quantApi.getEdgeStudy(studyId as string), enabled: online && !!studyId });
  const runStudy = useMutation({
    mutationFn: () => {
      if (!datasetId || !strategyKey) throw new QuantApiError(400, "Choisissez des données et une stratégie.");
      return quantApi.runEdgeStudy({ dataset_id: datasetId, strategy_key: strategyKey, horizon_bars: Number(horizon), folds: Number(folds) });
    },
    onSuccess: (s) => {
      qc.setQueryData(["study", s.study_id], s);
      void qc.invalidateQueries({ queryKey: ["studies"] });
      setParams({ study: s.study_id });
    },
  });
  const selectedDs = datasets.data?.find((d) => d.dataset_id === datasetId);
  const prior = (studies.data ?? []).filter((s) => s.dataset_id === datasetId || s.dataset_id == null).length;

  return (
    <Page wide>
      <PageHeader
        icon={Microscope}
        title="Validation & prédiction"
        status="engine"
        description="Mesure expérimentale, sur des périodes jamais vues, de l'espérance des signaux candidats d'une stratégie — et de la capacité d'un modèle à classer ces signaux. Le verdict dit « non démontré » chaque fois que c'est le cas."
      />
      <Callout tone="info" title="Ce que cette page peut — et ne peut pas — dire">
        Aucun outil ne prédit le marché avec certitude. Cette page mesure une espérance par signal candidat avec sa marge d'erreur,
        hors échantillon et coûts supposés inclus. La méthode statistique est <strong>expérimentale</strong> (validation en cours) :
        un « indice d'avantage » n'est pas une preuve, les scores du modèle ne sont pas des probabilités calibrées, et l'analyse des
        signaux n'est pas une performance de portefeuille exécutable.
      </Callout>
      {health.isError && <OfflineNotice />}

      {online && (
        <div className="grid items-start gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <Section title="Nouvelle étude" icon={Play}>
              {datasets.data?.length === 0 ? (
                <p className="text-sm text-muted-foreground" data-testid="research-no-dataset">
                  Aucun jeu de données. Importez un historique dans <Link to="/backtest" className="underline">Backtests</Link>.
                </p>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Label>Jeu de données</Label>
                    <Select value={datasetId ?? undefined} onValueChange={setDatasetId}>
                      <SelectTrigger data-testid="research-dataset"><SelectValue placeholder="Choisir…" /></SelectTrigger>
                      <SelectContent>
                        {datasets.data?.map((d) => (
                          <SelectItem key={d.dataset_id} value={d.dataset_id}>{d.name} · {d.rows.toLocaleString("fr-FR")} bougies</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedDs?.kind === "synthetic" && <p className="text-xs text-red-300">Données synthétiques : test de la méthode uniquement.</p>}
                  </div>
                  <div className="space-y-1.5">
                    <Label>Stratégie</Label>
                    <Select value={strategyKey ?? undefined} onValueChange={setStrategyKey}>
                      <SelectTrigger data-testid="research-strategy"><SelectValue placeholder="Choisir…" /></SelectTrigger>
                      <SelectContent>
                        {runnable.map((s) => <SelectItem key={s.key} value={s.key}>{s.spec.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="horizon">Horizon (bougies)</Label>
                      <Input id="horizon" type="number" min={1} max={5000} value={horizon} onChange={(e) => setHorizon(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="folds">Fenêtres de test</Label>
                      <Input id="folds" type="number" min={2} max={12} value={folds} onChange={(e) => setFolds(e.target.value)} />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Coûts, contrat et paramètres : valeurs par défaut du moteur.
                    {prior > 0 && <> Déjà {prior} étude(s) sur ces données : le niveau de confiance exigé sera relevé.</>}
                  </p>
                  <Button className="w-full" onClick={() => runStudy.mutate()} disabled={runStudy.isPending || !datasetId || !strategyKey}
                    data-testid="run-study">
                    {runStudy.isPending ? <><Activity className="mr-2 h-4 w-4 animate-spin" />Étude en cours…</> : <><Play className="mr-2 h-4 w-4" />Lancer l'étude</>}
                  </Button>
                  {runStudy.isError && <p className="text-sm text-red-400" role="alert">{(runStudy.error as Error).message}</p>}
                </div>
              )}
            </Section>

            {(studies.data?.length ?? 0) > 0 && (
              <Section title="Études enregistrées" icon={History}>
                <ul className="-mx-2 space-y-1" data-testid="studies-list">
                  {studies.data?.map((s) => (
                    <li key={s.study_id}>
                      <button type="button" onClick={() => setParams({ study: s.study_id })}
                        className={cn("w-full rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-muted/50",
                          s.study_id === studyId && "bg-primary/10")}>
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium">{s.dataset_name}</span>
                          <span className={cn("shrink-0 rounded px-1.5 text-[11px]",
                            s.verdict == null || s.verdict === "INVALID" || s.verdict === "NEGATIVE" ? "bg-red-500/15 text-red-300"
                              : s.verdict === "EDGE" ? "bg-sky-500/15 text-sky-300" : "bg-muted text-muted-foreground")}>
                            {s.verdict == null ? "refusée" : VERDICT_LABEL[s.verdict]}
                          </span>
                        </span>
                        <span className="block truncate text-xs text-muted-foreground" title={s.integrity_error}>
                          {s.verdict == null ? "intégrité non vérifiée — non affichée"
                            : `${s.created_at.slice(0, 16).replace("T", " ")} · ${s.n_oos ?? 0} signaux testés`}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </aside>

          <main className="min-w-0">
            {runStudy.isPending && !study.data && <div className="h-96 animate-pulse rounded-xl bg-muted/40" />}
            {study.isError && <p className="text-sm text-red-400">{(study.error as Error).message}</p>}
            {study.data ? (
              <StudyView key={study.data.study_id} study={study.data} />
            ) : (
              !runStudy.isPending && (
                <section data-testid="no-study" className="rounded-xl border border-dashed border-border p-8 text-sm text-muted-foreground">
                  <p className="text-base font-semibold text-foreground">Aucune étude pour l'instant</p>
                  <p className="mt-1">Choisissez un jeu de données et une stratégie, puis lancez l'étude. Plus l'historique est long,
                    plus la mesure est précise : visez plusieurs mois de M1 réel.</p>
                </section>
              )
            )}
          </main>
        </div>
      )}
    </Page>
  );
}
