import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Bot, HardDrive, History, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Callout, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { SimulationView } from "@/components/bots/SimulationView";
import { fmtDateTime, fmtNum, fmtPct } from "@/lib/format";
import { QuantApiError, quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

/**
 * External Bot Analysis & Optimization Lab — MT5 Strategy Tester reports of closed robots (.ex5), imported as
 * DATA, verified against MT5's own summary, stored immutably and analysed. Nothing is executed or traded.
 */
export default function BotAnalysis() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const sims = useQuery({ queryKey: ["external-sims"], queryFn: () => quantApi.listExternalSims(), enabled: online });
  const mt5 = useQuery({ queryKey: ["mt5-local-files"], queryFn: () => quantApi.listMt5Files(), enabled: online });
  const [file, setFile] = useState<File | null>(null);
  const verified = (sims.data?.simulations ?? []).filter((s) => s.integrity === "vérifiée");
  const simId = params.get("sim") ?? verified[0]?.sim_id ?? null;
  const sim = useQuery({ queryKey: ["external-sim", simId], queryFn: () => quantApi.getExternalSim(simId as string), enabled: online && !!simId });

  const onImported = (r: { sim_id: string }) => {
    void qc.invalidateQueries({ queryKey: ["external-sims"] });
    setParams({ sim: r.sim_id });
  };
  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new QuantApiError(400, "Choisissez un rapport MT5.");
      return quantApi.importExternalSim(file, file.name);
    },
    onSuccess: onImported,
  });
  const fromMt5 = useMutation({ mutationFn: (id: string) => quantApi.importExternalSimFromMt5(id), onSuccess: onImported });
  const lastImport = upload.data ?? fromMt5.data;
  const byRobot = new Map<string, typeof verified>();
  for (const s of verified) byRobot.set(s.robot ?? "Robot non identifié", [...(byRobot.get(s.robot ?? "Robot non identifié") ?? []), s]);
  const refused = (sims.data?.simulations ?? []).filter((s) => s.integrity === "refusée");

  return (
    <Page wide>
      <PageHeader icon={Bot} title="Bot Analysis" status="engine"
        description="Laboratoire d'analyse de robots MT5 externes à partir de leurs rapports de simulation : rapprochement avec MT5, causes des pertes, effondrement du risque et hypothèses de réduction du risque." />
      <Callout tone="info" title="Ce que fait ce laboratoire">
        Il lit les rapports du Strategy Tester (HTML, Excel, CSV, ZIP) comme des données, vérifie chaque chiffre contre le résumé MT5
        et conserve chaque import comme une référence immuable. Il n'exécute jamais un .ex5, ne se connecte à aucun courtier et
        n'envoie aucun ordre. Une simulation importée n'est pas un backtest du moteur, et rien ici ne démontre une rentabilité.
      </Callout>
      {health.isError && <OfflineNotice />}

      {online && (
        <div className="grid items-start gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <Section title="Importer un rapport" icon={Upload}>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="bot-file">Rapport MT5 (.html, .xlsx, .csv, .zip)</Label>
                  <Input id="bot-file" type="file" accept=".html,.htm,.xlsx,.csv,.zip" data-testid="bot-file"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                </div>
                <Button className="w-full" onClick={() => upload.mutate()} disabled={!file || upload.isPending} data-testid="bot-import">
                  {upload.isPending ? <><Activity className="mr-2 h-4 w-4 animate-spin" />Import et vérification…</> : "Importer"}
                </Button>
                {(upload.isError || fromMt5.isError) && (
                  <p className="text-sm text-red-400" role="alert">{((upload.error ?? fromMt5.error) as Error).message}</p>
                )}
                {lastImport && (
                  <p className="text-xs text-muted-foreground" data-testid="bot-import-outcome">
                    Simulation {lastImport.outcome} ({lastImport.sim_id}) — données {lastImport.validation.status}.
                  </p>
                )}
              </div>
            </Section>

            {mt5.data?.available && mt5.data.files.length > 0 && (
              <Section title="Depuis votre terminal MT5" icon={HardDrive} description="Lecture seule des rapports présents sur cet ordinateur.">
                <ul className="-mx-2 space-y-1" data-testid="bot-mt5-files">
                  {mt5.data.files.map((f) => (
                    <li key={f.id}>
                      <button type="button" disabled={f.too_large || fromMt5.isPending} onClick={() => fromMt5.mutate(f.id)}
                        className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/60 disabled:opacity-50">
                        <span className="block truncate font-medium">{f.name}</span>
                        <span className="block text-xs text-muted-foreground">{f.folder} · {(f.bytes / 1024).toFixed(0)} Ko</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            <Section title="Robots et simulations" icon={History}>
              {verified.length === 0 ? (
                <p className="text-sm text-muted-foreground" data-testid="bot-empty">
                  Aucune simulation importée. Importez le rapport HTML ou Excel d'un test du Strategy Tester.
                </p>
              ) : (
                <div className="space-y-4" data-testid="bot-list">
                  {[...byRobot.entries()].map(([robot, list]) => (
                    <div key={robot}>
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{robot}</p>
                      <ul className="-mx-2 space-y-1">
                        {list.map((s) => (
                          <li key={s.sim_id}>
                            <button type="button" onClick={() => setParams({ sim: s.sim_id })} data-testid={`bot-sim-${s.sim_id}`}
                              className={cn("w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/60", s.sim_id === simId && "bg-muted")}>
                              <span className="block truncate">{s.symbol} {s.timeframe} · {s.source_format?.toUpperCase()} · net {fmtNum(s.net_profit, 0)}</span>
                              <span className="block text-xs text-muted-foreground">
                                DD {fmtPct(s.balance_dd_maximal_pct, 1)} · {s.validation} · {s.imported_at ? fmtDateTime(s.imported_at) : ""}
                                {(s.same_test_sources ?? 1) > 1 && " · même test, plusieurs sources"}
                                {s.contradictory && " · CONTRADICTOIRE"}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
              {refused.length > 0 && (
                <p className="mt-3 text-xs text-red-300" data-testid="bot-refused">{refused.length} simulation(s) refusée(s) : intégrité non vérifiée.</p>
              )}
            </Section>
          </aside>
          <div>
            {sim.isError && <Callout tone="danger" title="Simulation refusée">{(sim.error as Error).message}</Callout>}
            {sim.data ? <SimulationView sim={sim.data} /> : verified.length > 0 && !sim.isError && (
              <p className="text-sm text-muted-foreground">Chargement…</p>
            )}
          </div>
        </div>
      )}
    </Page>
  );
}
