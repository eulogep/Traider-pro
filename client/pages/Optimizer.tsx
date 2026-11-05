import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpenCheck,
  CheckCircle2,
  Circle,
  CircleHelp,
  Clock,
  FlaskConical,
  ListChecks,
  MessageSquareQuote,
  SlidersHorizontal,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import type { StrategyItem } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { Callout, Facts, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

const CATEGORY: Record<string, string> = {
  baseline: "Référence (baseline)",
  pilot_trader: "Stratégie du trader pilote",
  third_party: "Tierce",
};
const STATUS: Record<string, { label: string; cls: string }> = {
  active: { label: "active", cls: "border-primary/30 bg-primary/10 text-primary" },
  draft: { label: "brouillon", cls: "border-amber-500/30 bg-amber-500/10 text-amber-300" },
  archived: { label: "archivée", cls: "border-border bg-muted text-muted-foreground" },
};
const RULES: Array<[keyof StrategyItem["spec"]["rules"], string]> = [
  ["buy", "Achat"],
  ["sell", "Vente"],
  ["wait", "Attendre"],
  ["invalidation", "Invalidation"],
  ["exit", "Sortie"],
];
const WEEKDAYS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"];
/** Known spec codes in plain French; an unknown code is shown as is (never guessed). */
const CODES: Record<string, string> = {
  none: "aucune (pas d'ajout ni de retrait partiel)",
  project: "propriété du projet",
  owner_consent: "avec l'accord du trader",
};
const code = (v: string) => (v ? CODES[v] ?? v : "—");

function StrategyCard({ item, active, onClick }: { item: StrategyItem; active: boolean; onClick: () => void }) {
  const s = item.spec;
  const st = STATUS[s.status] ?? STATUS.archived;
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`strategy-card-${s.id}`}
      aria-pressed={active}
      className={cn(
        "w-full rounded-xl border p-4 text-left transition-colors",
        active ? "border-primary/50 bg-primary/5 ring-1 ring-primary/30" : "border-border/60 bg-card/70 hover:border-border",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{CATEGORY[s.category] ?? s.category}</span>
        <span className={cn("rounded border px-1.5 py-px text-[10px] font-medium uppercase", st.cls)}>{st.label}</span>
      </div>
      <p className="mt-1.5 font-semibold leading-snug">{s.name}</p>
      <p className="mt-1 flex items-center gap-1.5 text-xs">
        {item.runnable ? (
          <span className="flex items-center gap-1 text-primary"><CheckCircle2 className="h-3.5 w-3.5" />testable dans Backtests</span>
        ) : (
          <span className="flex items-center gap-1 text-amber-400"><Clock className="h-3.5 w-3.5" />pas encore testable</span>
        )}
        <span className="text-muted-foreground">· v{s.version}</span>
      </p>
    </button>
  );
}

function StrategyDetail({ item }: { item: StrategyItem }) {
  const s = item.spec;
  const params = Object.entries(s.params);
  const hours = s.trading_hours;
  return (
    <div className="space-y-6" data-testid="strategy-detail">
      {!item.runnable && item.problems.length > 0 && (
        <Callout tone="warn" title="Pourquoi elle n'est pas encore testable">
          <ul className="list-disc space-y-0.5 pl-4">
            {item.problems.map((p) => <li key={p}>{p}</li>)}
          </ul>
        </Callout>
      )}
      {s.illustrative && (
        <Callout tone="info" title="Stratégie illustrative">
          Elle sert à valider le moteur de bout en bout. Elle n'est pas la stratégie du trader et ses résultats ne disent rien de
          celle-ci.
        </Callout>
      )}

      <Section title="Fiche" icon={BookOpenCheck} description={s.description}>
        <Facts
          cols={3}
          items={[
            ["Identifiant", <code key="id" className="text-xs">{s.id}@{s.version}</code>],
            ["Propriétaire", s.owner],
            ["Marché", Object.values(s.market).join(" · ") || "—"],
            ["Unité d'exécution", s.timeframes.execution],
            ["Unités de contexte", s.timeframes.context.length ? s.timeframes.context.join(", ") : "aucune"],
            ["Horaires", `${hours.sessions.join(", ") || "toute la journée"} (${hours.timezone}) · ${hours.weekdays.map((d) => WEEKDAYS[d] ?? d).join(" ")}`],
            ["Gestion de position", code(s.position_scaling)],
            ["Droits d'usage", code(s.usage_rights)],
            ["Implémentation", s.implementation ? <code key="impl" className="text-xs">{s.implementation}</code> : "aucune pour l'instant"],
          ]}
        />
      </Section>

      <Section title="Règles écrites" icon={ListChecks} description="Ce que la stratégie fait, en clair. Le code doit s'y conformer.">
        <div className="grid gap-4 md:grid-cols-2">
          {RULES.map(([k, label]) => (
            <div key={k} className="rounded-lg border border-border/50 bg-background/40 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
              <ul className="mt-1.5 space-y-1 text-sm">
                {(s.rules[k] ?? []).length ? (
                  s.rules[k].map((r) => (
                    <li key={r} className={cn("leading-snug", /À DÉFINIR/i.test(r) && "text-amber-300")}>{r}</li>
                  ))
                ) : (
                  <li className="text-muted-foreground">—</li>
                )}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Paramètres autorisés" icon={SlidersHorizontal}
        description="Seules ces valeurs, dans ces bornes, peuvent être modifiées dans Backtests.">
        {params.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucun paramètre défini pour l'instant.</p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
                  <th className="px-5 py-2 font-medium">Paramètre</th>
                  <th className="px-2 py-2 font-medium">Défaut</th>
                  <th className="px-2 py-2 font-medium">Bornes / choix</th>
                  <th className="px-5 py-2 font-medium">Modifiable</th>
                </tr>
              </thead>
              <tbody>
                {params.map(([name, p]) => (
                  <tr key={name} className="border-b border-border/30 align-top">
                    <td className="px-5 py-2.5">
                      <p>{p.description}</p>
                      <code className="text-xs text-muted-foreground">{name}</code>
                    </td>
                    <td className="px-2 py-2.5 font-mono text-xs">{String(p.default)}</td>
                    <td className="px-2 py-2.5 font-mono text-xs text-muted-foreground">
                      {p.choices ? p.choices.join(" | ") : p.min != null || p.max != null ? `${p.min ?? "−∞"} … ${p.max ?? "+∞"}` : "—"}
                    </td>
                    <td className="px-5 py-2.5 text-xs">{p.editable ? "oui" : "non (fixé)"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {s.open_questions.length > 0 && (
        <Section title="Questions à poser au trader" icon={MessageSquareQuote} testId="open-questions"
          description="Tant qu'elles n'ont pas de réponse, rien n'est inventé : la stratégie reste en brouillon.">
          <ol className="space-y-2">
            {s.open_questions.map((q, i) => (
              <li key={q} className="flex gap-3 text-sm">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-amber-500/40 text-xs text-amber-300">{i + 1}</span>
                <span className="pt-0.5">{q}</span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs text-muted-foreground">Guide d'entretien complet : <code>quant/docs/ENTRETIEN_TRADER.md</code>.</p>
        </Section>
      )}

      {item.runnable && (
        <div className="flex justify-end">
          <Button asChild>
            <Link to="/backtest"><FlaskConical className="mr-2 h-4 w-4" />Tester cette stratégie</Link>
          </Button>
        </div>
      )}
    </div>
  );
}

function Prerequisite({ done, label, detail }: { done: boolean; label: string; detail: string }) {
  return (
    <li className="flex gap-3">
      {done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />}
      <div>
        <p className={cn("text-sm font-medium", !done && "text-muted-foreground")}>{label}</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
    </li>
  );
}

/** Strategies & optimisation — specs come from the engine registry; optimisation is not built yet and says so. */
export default function Optimizer() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => quantApi.listStrategies(), enabled: online });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => quantApi.listDatasets(), enabled: online });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => quantApi.listBacktests(), enabled: online });
  const studies = useQuery({ queryKey: ["studies"], queryFn: () => quantApi.listEdgeStudies(), enabled: online });
  const list = strategies.data?.strategies ?? [];
  const [key, setKey] = useState<string | null>(null);
  useEffect(() => {
    if (!key && list.length) setKey(list[0].key);
  }, [list, key]);
  const selected = list.find((s) => s.key === key);
  const errors = Object.entries(strategies.data?.errors ?? {});

  const pilotReady = list.some((s) => s.spec.category === "pilot_trader" && s.runnable);
  const hasHistorical = (datasets.data ?? []).some((d) => d.kind === "historical");
  const historicalRun = (runs.data ?? []).some((r) => r.data_kind === "historical");
  const historicalStudy = (studies.data ?? []).some((s) => s.data_kind === "historical");

  return (
    <Page wide>
      <PageHeader
        icon={BookOpenCheck}
        title="Stratégies & optimisation"
        status="engine"
        description="Les stratégies enregistrées dans le moteur, leurs règles écrites et leurs paramètres. L'optimisation automatique viendra seulement quand les prérequis ci-dessous seront remplis."
      />
      {health.isError && <OfflineNotice />}

      {online && (
        <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{list.length} stratégie(s)</p>
            {strategies.isLoading && <div className="h-28 animate-pulse rounded-xl bg-muted/40" />}
            {list.map((s) => (
              <StrategyCard key={s.key} item={s} active={s.key === key} onClick={() => setKey(s.key)} />
            ))}
            {errors.length > 0 && (
              <Callout tone="danger" title="Spécifications refusées">
                <ul className="space-y-1">
                  {errors.map(([k, e]) => <li key={k}><code>{k}</code> : {e}</li>)}
                </ul>
              </Callout>
            )}
          </div>
          <div className="min-w-0">{selected && <StrategyDetail key={selected.key} item={selected} />}</div>
        </div>
      )}

      <Section
        title="Optimisation des paramètres"
        icon={Sparkles}
        testId="optimization-status"
        description="Pas encore disponible — volontairement."
        actions={<span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">à venir</span>}
      >
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-3 text-sm text-muted-foreground">
            <p className="flex items-center gap-2 font-medium text-foreground"><TriangleAlert className="h-4 w-4 text-amber-400" />Pourquoi pas tout de suite ?</p>
            <p>
              Chercher « les meilleurs réglages » sur un seul historique trouve presque toujours des paramètres qui collent au passé
              par hasard (sur-optimisation). Les résultats paraissent excellents, puis s'effondrent en réel.
            </p>
            <p>
              La page <Link to="/research" className="underline">Validation</Link> mesure déjà, hors échantillon, l'espérance
              d'une stratégie et l'apport d'un modèle de filtrage. L'optimisation sera construite dessus : réglages choisis sur une
              période, jugés sur une période jamais vue, avec un niveau de confiance relevé à chaque essai.
            </p>
          </div>
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-sm font-medium"><CircleHelp className="h-4 w-4 text-muted-foreground" />Prérequis (état réel)</p>
            <ul className="space-y-3" data-testid="optimization-prerequisites">
              <Prerequisite done={online && hasHistorical} label="Un historique réel importé"
                detail="Export MT5 du symbole visé (M1), avec sa source déclarée." />
              <Prerequisite done={online && pilotReady} label="La stratégie du trader formalisée et active"
                detail="Réponses aux questions ouvertes, puis implémentation testée." />
              <Prerequisite done={online && historicalRun} label="Un backtest de référence sur cet historique"
                detail="Pour savoir d'où l'on part avant de chercher à améliorer." />
              <Prerequisite done={online && historicalStudy} label="Une étude hors échantillon sur cet historique"
                detail="Page Validation : verdict walk-forward avec intervalles de confiance." />
            </ul>
          </div>
        </div>
      </Section>
    </Page>
  );
}
