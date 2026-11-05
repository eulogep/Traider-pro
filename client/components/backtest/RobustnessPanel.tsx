import { useQuery } from "@tanstack/react-query";
import { Dices, ShieldAlert, Sigma } from "lucide-react";
import { Link } from "react-router-dom";
import { Callout, Facts, Section } from "@/components/layout/Page";
import { fmtCi, fmtR } from "@/components/research/StudyView";
import { quantApi } from "@/lib/quantApi";
import { fmtMoney, fmtNum, fmtPct, UNAVAILABLE } from "@/lib/format";

const pct = (v: number | null | undefined, d = 1) => (v == null ? UNAVAILABLE : fmtPct(v * 100, d));

/** How much of this run could be luck — bootstrap and Monte Carlo computed by the Python research layer. */
export function RobustnessPanel({ runId, currency }: { runId: string; currency: string }) {
  const q = useQuery({ queryKey: ["robustness", runId], queryFn: () => quantApi.getRobustness(runId) });
  if (q.isLoading) return <div className="h-40 animate-pulse rounded-lg bg-muted/40" />;
  if (q.isError) return <p className="text-sm text-red-400">{(q.error as Error).message}</p>;
  const r = q.data!;
  if (!r.expectancy_r) return <Callout tone="warn">{r.note ?? "Pas assez de trades pour mesurer l'incertitude."}</Callout>;
  const dd = r.max_drawdown_pct!;
  const conf = fmtPct(r.confidence * 100, 0);
  return (
    <div className="space-y-4" data-testid="robustness">
      <Callout tone={r.rating === "positif" ? "safe" : r.rating === "négatif" ? "danger" : "warn"}
        title={r.rating === "positif" ? "Espérance positive au-delà du hasard (sur ce run)"
          : r.rating === "négatif" ? "Espérance négative au-delà du hasard"
          : r.rating === "insuffisant" ? `Moins de ${r.min_trades} trades : mesure très imprécise` : "Résultat compatible avec le hasard"}>
        Intervalles à {conf} par bootstrap par blocs ({r.n_boot.toLocaleString("fr-FR")} tirages) sur les {r.n_trades} trades de ce run.
        Pour un verdict hors échantillon, lancez une étude dans <Link to="/research" className="underline">Validation</Link>.
      </Callout>
      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Incertitude de l'espérance" icon={Sigma}>
          <Facts items={[
            ["Espérance par trade", fmtR(r.expectancy_r.value)],
            [`Intervalle ${conf}`, fmtCi(r.expectancy_r.ci, (x) => fmtNum(x, 3))],
            ["Part des tirages bootstrap > 0 (pas une probabilité)", pct(r.expectancy_r.p_positive)],
            ["Espérance en argent", fmtMoney(r.expectancy_money!.value, currency)],
            ["Win rate", pct(r.win_rate!.value)],
            [`Win rate · intervalle ${conf}`, fmtCi(r.win_rate!.ci, (x) => pct(x))],
          ]} />
        </Section>
        <Section title="Drawdown si l'ordre des trades était interchangeable" icon={Dices}
          description={`${r.n_boot.toLocaleString("fr-FR")} réordonnancements aléatoires des trades de ce run. Hypothèse forte : l'ordre ne compte pas — les séries de pertes réelles sont détruites.`}>
          <Facts items={[
            ["Drawdown de ce run", fmtPct(dd.actual)],
            ["Drawdown médian", fmtPct(dd.median)],
            ["1 fois sur 20, pire que", fmtPct(dd.p95)],
            ["Pire cas observé", fmtPct(dd.worst)],
            ["Limite du Risk Guardian", fmtPct(dd.limit)],
            ["Part des réordonnancements atteignant la limite", pct(dd.p_breach_limit)],
          ]} />
          <p className="mt-3 flex items-start gap-2 text-xs text-muted-foreground">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Mesure conditionnelle, pas une probabilité de drawdown futur : les montants restent fixes, le Risk Guardian n'est pas
            rejoué, et mélanger les trades efface les séries de pertes consécutives (un drawdown réel peut être bien pire).
          </p>
        </Section>
      </div>
    </div>
  );
}
