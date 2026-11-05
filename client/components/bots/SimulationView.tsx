import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, FileText, FlaskConical, Layers, ListChecks, Microscope, Settings2, TrendingDown, XCircle } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ExternalSim, ExternalTrade, WhatIfQualification } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Callout, Facts, Section, Tile } from "@/components/layout/Page";
import { fmtDateTime, fmtNum, fmtPct, fmtShortDateTime } from "@/lib/format";
import { quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

const UNAVAILABLE = "—";
const money = (v: number | null | undefined) => (v == null ? UNAVAILABLE : fmtNum(v, 2));
const AXIS = { stroke: "hsl(var(--muted-foreground))", fontSize: 11 };
const TOOLTIP = { background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 };
const QUALIF: Record<WhatIfQualification, { label: string; cls: string }> = {
  exact: { label: "Recalcul exact des événements observés", cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" },
  approximation: { label: "Approximation conditionnelle — pas un backtest du robot modifié", cls: "border-amber-500/40 bg-amber-500/10 text-amber-300" },
  non_simulable: { label: "Non simulable avec les données disponibles", cls: "border-red-500/40 bg-red-500/10 text-red-300" },
};
const STATUS_CLS: Record<string, string> = {
  validé: "text-emerald-300", partiel: "text-amber-300", écarts: "text-red-300",
};

function TradesTable({ trades, testId }: { trades: ExternalTrade[]; testId?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs" data-testid={testId}>
        <thead className="text-left text-muted-foreground">
          <tr>
            <th className="py-1 pr-2">Ouverture (deal)</th><th className="pr-2">Sens</th><th className="pr-2 text-right">Lots</th>
            <th className="pr-2 text-right">Prix d'entrée</th><th className="pr-2">Clôture (deal)</th><th className="pr-2 text-right">Prix de sortie</th>
            <th className="pr-2 text-right">Résultat net</th><th>Motif</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={`${t.entry_deal}-${t.exit_deal}`} className="border-t border-border/40">
              <td className="py-1 pr-2">{fmtShortDateTime(t.entry_time)} (#{t.entry_deal})</td>
              <td className="pr-2">{t.side}</td>
              <td className="pr-2 text-right">{fmtNum(t.volume, 2)}</td>
              <td className="pr-2 text-right">{fmtNum(t.entry_price, 2)}</td>
              <td className="pr-2">{fmtShortDateTime(t.exit_time)} (#{t.exit_deal})</td>
              <td className="pr-2 text-right">{fmtNum(t.exit_price, 2)}</td>
              <td className={cn("pr-2 text-right", t.net < 0 ? "text-red-300" : "text-emerald-300")}>{money(t.net)}</td>
              <td>{t.close_reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WhatIfPanel({ sim }: { sim: ExternalSim }) {
  const rules = useQuery({ queryKey: ["what-if-rules"], queryFn: () => quantApi.whatIfRules() });
  const [rule, setRule] = useState("exposure_cap");
  const [value, setValue] = useState("");
  const run = useMutation({
    mutationFn: () => quantApi.runWhatIf(sim.sim_id, rule, value.trim() === "" ? undefined : Number(value.replace(",", "."))),
  });
  const current = rules.data?.find((r) => r.rule === rule);
  const r = run.data;
  return (
    <Section title="Hypothèses de réduction du risque" icon={FlaskConical} testId="what-if"
      description="Règles alternatives appliquées aux opérations observées. Chaque résultat est qualifié : exact, approximation conditionnelle ou non simulable.">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_140px_auto] sm:items-end">
        <div className="space-y-1.5">
          <Label>Règle</Label>
          <Select value={rule} onValueChange={(v) => { setRule(v); run.reset(); }}>
            <SelectTrigger data-testid="what-if-rule"><SelectValue /></SelectTrigger>
            <SelectContent>
              {rules.data?.map((x) => <SelectItem key={x.rule} value={x.rule}>{x.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="what-if-value">Valeur {current?.unit ? `(${current.unit})` : ""}</Label>
          <Input id="what-if-value" inputMode="decimal" placeholder={current?.default != null ? String(current.default) : "—"}
            value={value} onChange={(e) => setValue(e.target.value)} disabled={current?.default == null} />
        </div>
        <Button onClick={() => run.mutate()} disabled={run.isPending} data-testid="run-what-if">Calculer</Button>
      </div>
      {run.isError && <p className="mt-2 text-sm text-red-400" role="alert">{(run.error as Error).message}</p>}
      {r && (
        <div className="mt-4 space-y-3" data-testid="what-if-result" data-qualification={r.qualification}>
          <div className={cn("rounded-md border px-3 py-2 text-sm font-medium", QUALIF[r.qualification].cls)}>{QUALIF[r.qualification].label}</div>
          {r.result && (
            <div className="grid gap-3 sm:grid-cols-3">
              <Tile label="Résultat net (observé → règle)" value={`${money(r.baseline.net)} → ${money(r.result.net)}`} />
              <Tile label="Drawdown réalisé max." value={`${fmtPct(r.baseline.max_realised_dd_pct, 1)} → ${fmtPct(r.result.max_realised_dd_pct, 1)}`} />
              <Tile label="Trades conservés" value={`${r.result.kept_trades} (retirés : ${r.result.removed_trades})`}
                sub={r.result.stop_out_kept ? "le stop-out observé reste dans le parcours" : "aucun stop-out dans le parcours conservé"} />
            </div>
          )}
          <p className="text-sm">{r.explanation}</p>
          {r.caveats.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">{r.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
          )}
          {r.what_to_do && <p className="text-xs text-muted-foreground"><strong>Pour aller plus loin :</strong> {r.what_to_do}</p>}
        </div>
      )}
    </Section>
  );
}

/** Display only — every number is computed by the Python engine (external_lab/). */
export function SimulationView({ sim }: { sim: ExternalSim }) {
  const [allDeals, setAllDeals] = useState(false);
  const env = sim.environment;
  const c = sim.collapse;
  const rec = sim.recomputed;
  const curve = sim.timeline.filter((p) => p.equity_est != null);
  const exposure = sim.timeline.filter((p) => p.long_lots != null).map((p) => ({ t: p.t, lots: (p.long_lots ?? 0) + (p.short_lots ?? 0) }));
  const deals = allDeals ? sim.deals : sim.deals.slice(0, 120);
  const riskNames = new Set(sim.risk_inputs.map((i) => i.name));
  return (
    <div className="space-y-6" data-testid="simulation-view" data-sim={sim.sim_id}>
      <Callout tone="warn" title="Simulation externe importée — pas un backtest du moteur">
        Rapport du Strategy Tester MT5 traité comme des données. Le robot (.ex5) n'est ni exécuté ni lu : tout ce qui concerne sa logique
        interne est une hypothèse. Un historique de simulation ne prouve aucune rentabilité future.
      </Callout>

      <Section title={sim.robot.name ?? "Robot non identifié"} icon={FileText}
        description={sim.robot.self_identification ? `S'identifie comme « ${sim.robot.self_identification} »` : undefined}>
        <Facts cols={3} items={[
          ["Serveur", `${env.server ?? UNAVAILABLE}${env.build ? ` (build ${env.build})` : ""}`],
          ["Instrument / unité", `${env.symbol ?? UNAVAILABLE} · ${env.timeframe ?? UNAVAILABLE}`],
          ["Période demandée", env.requested_period ?? UNAVAILABLE],
          ["Période observée", `${fmtDateTime(sim.period.first_deal)} → ${fmtDateTime(sim.period.last_deal)}`],
          ["Capital initial", `${money(env.initial_deposit)} ${env.currency ?? ""}`],
          ["Levier", env.leverage ?? UNAVAILABLE],
          ["Qualité d'historique", env.history_quality ?? UNAVAILABLE],
          ["Modélisation", env.modelling ?? "non indiquée dans le rapport"],
          ["Taille de contrat", `${fmtNum(sim.contract_size.value, 0)} (${sim.contract_size.source})`],
          ["Source", `${sim.source.name} · ${sim.source.format.toUpperCase()} · SHA-256 ${sim.source.sha256.slice(0, 12)}…`],
          ["Ordres / deals / positions / trades", `${sim.counts.orders} / ${sim.counts.trading_deals} / ${sim.counts.positions_opened} / ${sim.counts.trades}`],
          ["Validation des données", <span key="v" data-testid="sim-validation" className={STATUS_CLS[sim.validation.status]}>{sim.validation.status}</span>],
        ]} />
      </Section>

      {sim.period.ends_early && (
        <div data-testid="period-divergence">
          <Callout tone="danger" title="La simulation s'arrête avant la date demandée">
            {sim.period.evidence.join(" ")} {sim.period.interpretation}
          </Callout>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Tile label="Résultat net" value={money(rec.net_profit)} tone={(rec.net_profit ?? 0) < 0 ? "down" : "up"} testId="sim-net" />
        <Tile label="Trades gagnants" value={fmtPct(rec.profit_trades_pct, 1)} sub={`${rec.profit_trades} sur ${rec.total_trades}`} />
        <Tile label="Gain moyen / perte moyenne" value={`${money(rec.average_profit_trade)} / ${money(rec.average_loss_trade)}`} />
        <Tile label="Drawdown du solde max." value={fmtPct(rec.balance_dd_maximal_pct, 2)} sub={money(rec.balance_dd_maximal)} tone="down" />
      </div>

      {c && (
        <Section title="Risk Collapse Analysis" icon={TrendingDown} testId="risk-collapse"
          description="Comment une simulation longtemps gagnante peut s'effondrer quand le risque se concentre.">
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-semibold">Constats (dans le rapport)</h3>
              <ul className="space-y-1.5 text-sm" data-testid="collapse-observed">
                {sim.findings.observed.map((o) => <li key={o.fact} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />{o.fact}</li>)}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">Hypothèses sur le fonctionnement du robot (à confirmer)</h3>
              <ul className="space-y-2 text-sm" data-testid="collapse-hypotheses">
                {sim.findings.hypotheses.map((h) => (
                  <li key={h.statement} className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2">
                    <span className="mr-2 rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-300">{h.status}</span>
                    {h.statement}
                    <span className="mt-1 block text-xs text-muted-foreground">Indice : {h.evidence}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">{sim.findings.note}</p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="mb-1 text-sm font-semibold">Solde réalisé et équité estimée</h3>
              <p className="mb-2 text-xs text-muted-foreground">Équité estimée aux seuls instants d'opération (au prix du deal) : l'écart montre les pertes latentes que le solde ne voit pas.</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={curve} margin={{ left: 4, right: 8, top: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="t" tickFormatter={(t: string) => t.slice(5, 10).replace("-", "/")} minTickGap={48} {...AXIS} />
                    <YAxis width={64} tickFormatter={(x: number) => fmtNum(x, 0)} {...AXIS} />
                    <Tooltip contentStyle={TOOLTIP} labelFormatter={(t) => fmtDateTime(String(t))} formatter={(v: number) => money(v)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="stepAfter" dataKey="balance" name="Solde réalisé" stroke="#38bdf8" dot={false} isAnimationActive={false} />
                    <Line type="linear" dataKey="equity_est" name="Équité estimée" stroke="#f87171" dot={false} strokeWidth={1.5} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <h3 className="mb-1 text-sm font-semibold">Exposition ouverte et taille des lots</h3>
              <p className="mb-2 text-xs text-muted-foreground">Lots ouverts après chaque opération ; la taille des positions grandit avec le solde.</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={exposure} margin={{ left: 4, right: 8, top: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="t" tickFormatter={(t: string) => t.slice(5, 10).replace("-", "/")} minTickGap={48} {...AXIS} />
                    <YAxis width={40} {...AXIS} />
                    <Tooltip contentStyle={TOOLTIP} labelFormatter={(t) => fmtDateTime(String(t))} formatter={(v: number) => fmtNum(v, 2)} />
                    <Line type="stepAfter" dataKey="lots" name="Lots ouverts" stroke="#fbbf24" dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <h3 className="mb-2 mt-6 text-sm font-semibold">
            Séquence de l'effondrement : {c.losing_trades} pertes, {money(c.losing_total)}, {fmtNum(c.lots_involved, 2)} lots
          </h3>
          <TradesTable trades={c.trades} testId="collapse-trades" />
        </Section>
      )}

      <Section title="Rapprochement avec le résumé MT5" icon={ListChecks} testId="reconciliation"
        description="Chaque indicateur affiché par MT5 est recalculé à partir des deals ; tolérance = l'arrondi du chiffre MT5.">
        {sim.reconciliation.length === 0 ? (
          <p className="text-sm text-muted-foreground">Résumé MT5 absent de cette source : rapprochement impossible.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-left text-muted-foreground"><tr><th className="py-1 pr-2">Indicateur</th><th className="pr-2 text-right">MT5</th><th className="pr-2 text-right">Recalculé</th><th>État</th></tr></thead>
              <tbody>
                {sim.reconciliation.map((r) => (
                  <tr key={r.metric} className="border-t border-border/40" data-recon={r.status}>
                    <td className="py-1 pr-2">{r.label}{r.metric.includes(".") ? ` (${r.metric.split(".")[1]})` : ""}</td>
                    <td className="pr-2 text-right">{fmtNum(r.reported, 2)}</td>
                    <td className="pr-2 text-right">{r.computed == null ? UNAVAILABLE : fmtNum(r.computed, 2)}</td>
                    <td className={r.status === "concordant" ? "text-emerald-300" : "text-red-300"}>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <ul className="mt-4 space-y-1 text-xs">
          {sim.validation.checks.map((k) => (
            <li key={k.check} className="flex items-center gap-2">
              {k.ok === true ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : k.ok === false ? <XCircle className="h-3.5 w-3.5 text-red-400" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />}
              {k.check} — {k.detail}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-muted-foreground">{sim.pairing.note}</p>
      </Section>

      <WhatIfPanel sim={sim} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Plus grosses pertes" icon={TrendingDown}>
          <TradesTable trades={sim.largest_losses} testId="largest-losses" />
        </Section>
        <Section title="Performance par mois" icon={Microscope}>
          <table className="w-full text-xs" data-testid="monthly">
            <thead className="text-left text-muted-foreground"><tr><th className="py-1">Mois</th><th className="text-right">Trades</th><th className="text-right">Gagnants</th><th className="text-right">Net</th><th className="text-right">Pire trade</th></tr></thead>
            <tbody>
              {sim.monthly.map((m) => (
                <tr key={m.month} className="border-t border-border/40">
                  <td className="py-1">{m.month}</td><td className="text-right">{m.trades}</td><td className="text-right">{m.wins}</td>
                  <td className={cn("text-right", m.net < 0 ? "text-red-300" : "text-emerald-300")}>{money(m.net)}</td>
                  <td className="text-right">{money(m.worst)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      </div>

      <Section title="Paramètres d'origine du robot" icon={Settings2} description="Copiés tels quels du rapport ; ceux qui touchent au risque sont surlignés.">
        <div className="grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2" data-testid="robot-inputs">
          {sim.inputs.map((i, k) => (
            <div key={`${i.name}-${k}`} className={cn("flex justify-between gap-3 border-b border-border/30 py-0.5", riskNames.has(i.name) && "text-amber-300")}>
              <span className="truncate">{i.name}</span><span className="truncate text-right">{i.value || UNAVAILABLE}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Deals (exécutions)" icon={Layers} description="Un deal BUY peut fermer une position SELL : seule la colonne Direction dit s'il ouvre ou s'il ferme.">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="deals-table">
            <thead className="text-left text-muted-foreground">
              <tr><th className="py-1 pr-2">Heure</th><th className="pr-2">Deal</th><th className="pr-2">Type</th><th className="pr-2">Direction</th><th className="pr-2 text-right">Volume</th><th className="pr-2 text-right">Prix</th><th className="pr-2 text-right">Profit</th><th className="pr-2 text-right">Solde</th><th>Commentaire</th></tr>
            </thead>
            <tbody>
              {deals.map((d) => (
                <tr key={d.seq} className="border-t border-border/40">
                  <td className="py-0.5 pr-2">{fmtShortDateTime(d.time)}</td><td className="pr-2">{d.deal}</td><td className="pr-2">{d.type}</td>
                  <td className="pr-2">{d.direction === "in" ? "ouverture" : d.direction === "out" ? "clôture" : d.direction === "inout" ? "retournement" : ""}</td>
                  <td className="pr-2 text-right">{d.type === "balance" ? "" : fmtNum(d.volume, 2)}</td>
                  <td className="pr-2 text-right">{d.type === "balance" ? "" : fmtNum(d.price, 2)}</td>
                  <td className="pr-2 text-right">{money(d.profit)}</td><td className="pr-2 text-right">{money(d.balance)}</td><td>{d.comment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sim.deals.length > 120 && (
          <Button variant="outline" size="sm" className="mt-3" onClick={() => setAllDeals((x) => !x)}>
            {allDeals ? "Afficher moins" : `Afficher les ${sim.deals.length} deals`}
          </Button>
        )}
      </Section>

      <Callout tone="info" title="Ce que ces fichiers permettent — et ne permettent pas — de conclure">
        <ul className="list-disc space-y-1 pl-4">{sim.limits.map((l) => <li key={l}>{l}</li>)}</ul>
      </Callout>
    </div>
  );
}
