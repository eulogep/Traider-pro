import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Brain, Crosshair, FlaskConical, Gauge, Layers, ListOrdered, Microscope, Scale, Sigma } from "lucide-react";
import type { EdgeStudy, Interval, OpinionCode, Rating, VerdictCode } from "@shared/quant-api";
import { KindBadge } from "@/components/backtest/DatasetPanel";
import { Callout, Facts, Section, Tile } from "@/components/layout/Page";
import { fmtDateTime, fmtNum, fmtPct, UNAVAILABLE } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Display helpers only: every number below was computed by the Python research layer. */
export const fmtR = (v: number | null | undefined, d = 3) => (v == null ? UNAVAILABLE : `${v > 0 ? "+" : ""}${fmtNum(v, d)} R`);
export const fmtCi = (ci: Interval | undefined, f: (v: number) => string) =>
  !ci || ci[0] == null || ci[1] == null ? "intervalle indisponible" : `intervalle [${f(ci[0])} ; ${f(ci[1])}]`;
const pct = (v: number | null | undefined, d = 1) => (v == null ? UNAVAILABLE : fmtPct(v * 100, d));

const VERDICT_STYLE: Record<VerdictCode, string> = {
  EDGE: "border-primary/50 bg-primary/10",
  NO_EDGE: "border-amber-500/40 bg-amber-500/10",
  NEGATIVE: "border-red-500/50 bg-red-500/10",
  INSUFFICIENT: "border-border bg-muted/40",
  INVALID: "border-red-500/50 bg-red-500/10",
};
const OPINION_STYLE: Record<OpinionCode, string> = {
  "NE PAS TRADER": "border-amber-500/50 text-amber-300",
  IGNORER: "border-border text-muted-foreground",
  "FAVORABLE — EXPÉRIMENTAL": "border-sky-500/50 text-sky-300",
};
const ROLE_LABEL: Record<string, string> = {
  entraînement: "déjà résolu — fait partie de l'apprentissage",
  résolu: "déjà résolu avant la fin des données",
  "non exploitable": "non exploitable par le moteur",
  nouveau: "nouveau — résultat encore inconnu",
};
const RATING_TONE = (r: Rating | undefined) => (r === "positif" ? "up" : r === "négatif" ? "down" : "neutral") as "up" | "down" | "neutral";
const AXIS = { stroke: "hsl(var(--muted-foreground))", fontSize: 11 };

export function StudyView({ study }: { study: EdgeStudy }) {
  const r = study.result;
  const v = r.verdict;
  const fm = study.final_model;
  const op = fm?.opinion;
  const inf = r.inference;
  const maxW = Math.max(...(fm?.weights.map((w) => Math.abs(w.weight)) ?? [1]), 1e-9);
  return (
    <div className="space-y-5" data-testid="study-view">
      <div className={cn("rounded-xl border p-5", VERDICT_STYLE[v.code])} data-testid="study-verdict" data-code={v.code}>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Verdict · niveau de confiance {v.confidence}
        </p>
        <p className="mt-1 text-xl font-semibold">{v.title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{v.text}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <KindBadge kind={study.dataset.kind} />
          <span>{study.dataset.name} · {study.strategy.name}</span>
          <span>· étude <code data-testid="study-id">{study.study_id}</code></span>
        </div>
      </div>

      <div data-testid="study-experimental">
        <Callout tone="warn" title="Résultats expérimentaux — méthode en cours de validation">
          Ces chiffres décrivent des signaux candidats simulés un par un, pas une performance de portefeuille exécutable (limites
          journalières, position unique, tailles et drawdown ne sont pas appliqués). Aucun verdict de cette page n'est une preuve de
          rentabilité ; les scores du modèle ne sont pas des probabilités calibrées. Sur des données de contrôle sans avantage, la
          méthode a donné à tort un « indice d'avantage » dans environ 5 % des cas, et jusqu'à 8 % quand les marchés suivent des
          tendances d'environ une journée.
        </Callout>
      </div>
      {study.dataset.kind === "synthetic" && (
        <Callout tone="danger" title="Données synthétiques">
          Fausses cotations générées pour tester le logiciel. Elles peuvent contenir des régularités artificielles et ne disent
          rien d'un marché réel : un résultat obtenu ici ne prouve aucun avantage.
        </Callout>
      )}
      {study.multiple_testing.studies_in_family > 1 && (
        <Callout tone="warn" title={`Analyse n° ${study.multiple_testing.studies_in_family} de cet historique`}>
          Chaque nouvel essai sur le même historique augmente la chance de trouver un faux avantage ; tous les essais sont comptés
          dans un registre (règle : {study.multiple_testing.rule}, niveau {v.confidence}). La seule vraie protection reste une
          période future jamais utilisée.
        </Callout>
      )}
      {study.numerical_issues.length > 0 && (
        <Callout tone="warn" title="Valeurs non calculables">
          {study.numerical_issues.length} valeur(s) descriptive(s) non finie(s) ont été enregistrées comme indisponibles.
        </Callout>
      )}

      {r.n_oos > 0 && r.baseline && r.filtered && (
        <div className="grid grid-cols-2 gap-4 2xl:grid-cols-4">
          <Tile testId="study-oos" icon={Layers} label="Signaux hors échantillon" value={r.n_oos.toLocaleString("fr-FR")}
            sub={`${study.signals.labelled.toLocaleString("fr-FR")} étiquetés · ${r.folds.length} fenêtres${inf?.n_units != null ? ` · ${inf.n_units.toLocaleString("fr-FR")} unités indépendantes` : ""}`} />
          <Tile testId="study-baseline" icon={Scale} label="Tous les signaux candidats" value={fmtR(r.baseline.mean_r)}
            tone={RATING_TONE(r.baseline.rating)} sub={fmtCi(r.baseline.ci, (x) => fmtNum(x, 3))} />
          <Tile testId="study-filtered" icon={Crosshair} label="Avec filtre du modèle" value={fmtR(r.filtered.mean_r)}
            tone={RATING_TONE(r.filtered.rating)} sub={`${pct(r.coverage, 0)} des signaux · ${fmtCi(r.filtered.ci, (x) => fmtNum(x, 3))}`} />
          <Tile testId="study-auc" icon={Gauge} label="Classement du modèle (AUC)" value={fmtNum(r.auc?.value ?? null, 3)}
            tone={r.auc?.rating === "positif" ? "up" : "neutral"} sub={`0,5 = hasard · ${fmtCi(r.auc?.ci, (x) => fmtNum(x, 3))}`} />
        </div>
      )}

      {r.cumulative && r.cumulative.length > 1 && (
        <Section title="Résultat cumulé hors échantillon" icon={Sigma}
          description="Somme des R par signal candidat (signaux simultanés inclus) sur des périodes jamais vues par le modèle — pas une courbe de capital.">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={r.cumulative} margin={{ left: 4, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                <XAxis dataKey="t" tickFormatter={(t: string) => t.slice(5, 10).replace("-", "/")} minTickGap={48} {...AXIS} />
                <YAxis width={56} tickFormatter={(x: number) => fmtNum(x, 0)} {...AXIS} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(t) => fmtDateTime(String(t))} formatter={(x: number, n: string) => [fmtR(x, 1), n]} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="baseline_r" name="Tous les signaux" stroke="#64748b" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="filtered_r" name="Signaux retenus par le modèle" stroke="#22c55e" dot={false} strokeWidth={2} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      <div className="grid gap-5 2xl:grid-cols-2">
        {r.calibration && r.calibration.length > 0 && (
          <Section title="Calibration (non validée)" icon={Microscope} description="Score moyen du modèle par tranche contre fréquence de gain observée. Les scores ne sont pas calibrés : ne les lisez pas comme des probabilités.">
            <table className="w-full text-sm" data-testid="study-calibration">
              <thead>
                <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
                  <th className="py-2 font-medium">Score moyen</th>
                  <th className="py-2 font-medium">Fréquence observée</th>
                  <th className="py-2 text-right font-medium">Signaux</th>
                </tr>
              </thead>
              <tbody>
                {r.calibration.map((c, i) => (
                  <tr key={i} className="border-b border-border/30">
                    <td className="py-2 tabular-nums">{pct(c.mean_predicted)}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-32 overflow-hidden rounded bg-muted">
                          <div className="h-full bg-primary/70" style={{ width: `${Math.min(100, c.observed_rate * 100)}%` }} />
                        </div>
                        <span className="tabular-nums">{pct(c.observed_rate)}</span>
                      </div>
                    </td>
                    <td className="py-2 text-right tabular-nums">{c.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {r.brier && (
              <p className="mt-3 text-xs text-muted-foreground">
                Score de Brier {fmtNum(r.brier.model, 4)} contre {fmtNum(r.brier.reference, 4)} pour « taux moyen » ·
                gain {r.brier.skill == null ? UNAVAILABLE : pct(r.brier.skill)} (négatif = moins bon que deviner le taux moyen).
              </p>
            )}
          </Section>
        )}

        {fm && fm.weights.length > 0 && (
          <Section title="Ce que le modèle regarde" icon={Brain}
            description={`Poids descriptifs de la régression logistique (variables standardisées), ajustée sur tout l'historique étiqueté (${(fm.trained_on ?? 0).toLocaleString("fr-FR")} signaux) : une explication, pas une prévision.`}>
            <ul className="space-y-2" data-testid="study-weights">
              {fm.weights.map((w) => (
                <li key={w.feature} className="grid grid-cols-[minmax(0,1fr)_120px_56px] items-center gap-3 text-sm">
                  <span className="truncate" title={w.feature}>{w.label}</span>
                  <div className="relative h-2 rounded bg-muted">
                    <div className={cn("absolute top-0 h-2 rounded", w.weight >= 0 ? "left-1/2 bg-primary/70" : "right-1/2 bg-red-500/70")}
                      style={{ width: `${(Math.abs(w.weight) / maxW) * 50}%` }} />
                  </div>
                  <span className="text-right tabular-nums text-xs text-muted-foreground">{fmtNum(w.weight, 2)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">Vert : associé à plus de gains dans l'historique ; rouge : à moins.</p>
          </Section>
        )}
      </div>

      {op && (
        <Section title="Dernier signal du jeu de données" icon={FlaskConical} testId="study-latest">
          <div className="flex flex-wrap items-center gap-6">
            <Facts items={[
              ["Signal", op.signal_time ? `${op.direction ?? ""} · ${fmtDateTime(op.signal_time)}` : UNAVAILABLE],
              ["Statut du signal", op.role ? ROLE_LABEL[op.role] ?? op.role : UNAVAILABLE],
              ["Score du modèle (non calibré)", op.score == null ? "non donné" : fmtNum(op.score, 3)],
              ["Seuil du filtre", op.threshold == null ? "aucun seuil validé" : fmtNum(op.threshold, 3)],
              ["Modèle entraîné sur", op.trained_on == null ? UNAVAILABLE : `${op.trained_on.toLocaleString("fr-FR")} résultats connus avant ce signal`],
            ]} />
            <span data-testid="study-opinion" data-opinion={op.opinion}
              className={cn("rounded-lg border px-4 py-2 text-sm font-semibold", OPINION_STYLE[op.opinion] ?? OPINION_STYLE["NE PAS TRADER"])}>
              {op.opinion in OPINION_STYLE ? op.opinion : "NE PAS TRADER"}
            </span>
          </div>
          {op.reasons.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted-foreground" data-testid="study-opinion-reasons">
              {op.reasons.map((x) => <li key={x}>{x}</li>)}
            </ul>
          )}
          <p className="mt-2 text-xs text-muted-foreground">Avis de recherche expérimental, jamais un ordre : aucune position n'est ouverte par le logiciel.</p>
        </Section>
      )}

      <Section title="Fenêtres walk-forward" icon={ListOrdered} description="Chaque fenêtre est testée par un modèle entraîné uniquement sur le passé.">
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm" data-testid="study-folds">
            <thead>
              <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
                <th className="px-5 py-2 font-medium">#</th>
                <th className="px-2 py-2 font-medium">Période testée (UTC)</th>
                <th className="px-2 py-2 text-right font-medium">Entraîn.</th>
                <th className="px-2 py-2 text-right font-medium">dont valid.</th>
                <th className="px-2 py-2 text-right font-medium">Test</th>
                <th className="px-2 py-2 text-right font-medium">Retenus</th>
                <th className="px-2 py-2 text-right font-medium">Tous</th>
                <th className="px-2 py-2 text-right font-medium">Filtrés</th>
                <th className="px-5 py-2 text-right font-medium">AUC</th>
              </tr>
            </thead>
            <tbody>
              {r.folds.map((f) => (
                <tr key={f.fold} className="border-b border-border/30">
                  <td className="px-5 py-2">{f.fold}</td>
                  <td className="whitespace-nowrap px-2 py-2 tabular-nums text-muted-foreground">{f.test_start.slice(0, 10)} → {f.test_end.slice(0, 10)}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{f.n_train}</td>
                  <td className="px-2 py-2 text-right tabular-nums text-muted-foreground">{f.n_validation ?? UNAVAILABLE}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{f.n_test}</td>
                  {f.skipped || f.invalid ? (
                    <td colSpan={4} className="px-5 py-2 text-xs text-muted-foreground">{f.invalid ? `invalide : ${f.invalid}` : `ignorée : ${f.skipped}`}</td>
                  ) : (
                    <>
                      <td className="px-2 py-2 text-right tabular-nums">{f.taken}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{fmtR(f.baseline_mean_r ?? null, 2)}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{fmtR(f.filtered_mean_r ?? null, 2)}</td>
                      <td className="px-5 py-2 text-right tabular-nums">{fmtNum(f.auc ?? null, 2)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Méthode et traçabilité" icon={Microscope}>
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
          <li>Chaque signal candidat est simulé seul, avec les conventions d'exécution du moteur (entrée à l'ouverture suivante, stop
            avant objectif, coûts) et une sortie au marché si rien n'est touché après {study.settings.horizon_bars} bougies (jusqu'à{" "}
            {study.settings.horizon_bars + 1} bougies tenues, bougie d'entrée comprise). Résultat en R, coûts supposés inclus.</li>
          <li>Walk-forward ancré : les premiers {fmtPct(study.settings.initial_train_fraction * 100, 0)} de la période servent
            uniquement à l'entraînement ; un résultat n'est utilisé que s'il est connu (clôture de sa bougie de sortie) avant le
            début de la fenêtre testée (purge).</li>
          <li>Le seuil du filtre est choisi sur une tranche de validation interne, jamais sur les données de test.</li>
          <li>Incertitude : bootstrap ({study.settings.n_boot.toLocaleString("fr-FR")} tirages, méthode{" "}
            <code>{inf?.method ?? UNAVAILABLE}</code>){inf?.block_length != null ? `, blocs de ${inf.block_length}` : ""}. Le
            bootstrap porte sur les prédictions hors échantillon déjà calculées : il ne ré-entraîne pas le modèle.</li>
          {inf?.n_units != null && (
            <li>Les signaux dont les résultats se chevauchent dans le temps sont regroupés en une seule unité :{" "}
              {inf.n_units.toLocaleString("fr-FR")} unités indépendantes pour {r.n_oos.toLocaleString("fr-FR")} signaux hors
              échantillon. Ce sont les unités, pas les signaux, qui comptent pour l'incertitude et pour les effectifs minimaux.</li>
          )}
          <li>Indice d'avantage seulement si {typeof inf?.decision === "string" ? inf.decision : "la borne basse de l'espérance hors échantillon est positive"}
            {" "}(niveau {v.confidence}), avec assez d'observations ; statut <strong>expérimental</strong> tant que la méthode n'a
            pas été validée indépendamment.</li>
        </ul>
        <p className="mt-3 text-xs text-muted-foreground">
          {study.signals.candidates.toLocaleString("fr-FR")} signaux candidats · {study.signals.labelled.toLocaleString("fr-FR")} étiquetés ·
          variables {study.feature_set} · code <code>{study.code_hash}</code> · calculée le {fmtDateTime(study.created_at)}
        </p>
      </Section>
    </div>
  );
}
