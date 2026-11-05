import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BadgeCheck,
  Database,
  FileSearch,
  Fingerprint,
  FlaskConical,
  Lock,
  Play,
  ShieldCheck,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/layout/AppShell";
import { Page } from "@/components/layout/Page";
import { NAV_ITEMS } from "@/lib/modules";
import { quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

const STEPS: Array<{ icon: LucideIcon; title: string; text: string; href: string; cta: string }> = [
  {
    icon: Database,
    title: "1. Charger des données",
    text: "Importez un historique (CSV ou export MetaTrader 5). Il est validé tel quel : aucune bougie n'est corrigée ni inventée.",
    href: "/backtest",
    cta: "Importer",
  },
  {
    icon: SlidersHorizontal,
    title: "2. Choisir une stratégie",
    text: "Chaque stratégie a des règles écrites et des paramètres bornés. Celle du trader reste en brouillon tant qu'elle n'est pas formalisée.",
    href: "/optimizer",
    cta: "Voir les stratégies",
  },
  {
    icon: Play,
    title: "3. Simuler",
    text: "Le moteur Python rejoue l'historique bougie par bougie, avec coûts, spread et Risk Guardian. Aucun ordre ne part.",
    href: "/backtest",
    cta: "Lancer un backtest",
  },
  {
    icon: Fingerprint,
    title: "4. Vérifier",
    text: "Chaque résultat porte une empreinte SHA-256 et peut être recalculé à l'identique. Les refus de signaux sont expliqués.",
    href: "/dashboard",
    cta: "Voir les runs",
  },
];

const PRINCIPLES: Array<{ icon: LucideIcon; title: string; text: string }> = [
  { icon: ShieldCheck, title: "Aucun argent réel", text: "Pas de compte, pas d'identifiant, pas de route d'ordre. Le moteur le déclare lui-même." },
  { icon: FileSearch, title: "Données jamais retouchées", text: "Trous, doublons, fuseau douteux : le fichier est refusé ou signalé, jamais « réparé » en silence." },
  { icon: BadgeCheck, title: "Pas de promesse", text: "Un backtest décrit le passé avec des hypothèses de coûts. Ce n'est ni un gain réalisable ni une prévision." },
  { icon: Lock, title: "Risque borné", text: "Risque par trade, perte journalière et drawdown sont plafonnés. La martingale est interdite par le code." },
];

function LabState() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => quantApi.listDatasets(), enabled: online });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => quantApi.listBacktests(), enabled: online });
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => quantApi.listStrategies(), enabled: online });
  const runnable = strategies.data?.strategies.filter((s) => s.runnable).length;
  const rows: Array<[string, string | number | undefined]> = [
    ["Jeux de données", datasets.data?.length],
    ["Backtests enregistrés", runs.data?.length],
    ["Stratégies testables", runnable],
  ];
  return (
    <div data-testid="home-lab-state" className="rounded-2xl border border-border/60 bg-card/80 p-5 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">État du laboratoire</p>
        <span className={cn("flex items-center gap-1.5 text-xs", online ? "text-primary" : "text-red-400")}>
          <span className={cn("h-2 w-2 rounded-full", online ? "bg-primary" : "bg-red-500")} />
          {health.isLoading ? "connexion…" : online ? "moteur en ligne" : "moteur hors ligne"}
        </span>
      </div>
      {online ? (
        <>
          <dl className="mt-4 grid grid-cols-3 gap-3">
            {rows.map(([k, v]) => (
              <div key={k} className="rounded-lg border border-border/50 bg-background/50 p-3">
                <dd className="text-2xl font-semibold tabular-nums">{v ?? "…"}</dd>
                <dt className="text-[11px] leading-tight text-muted-foreground">{k}</dt>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-muted-foreground">
            Moteur <code>{health.data.engine_version}</code> · mode {health.data.execution_mode} ·{" "}
            {health.data.order_routes} route d'ordre · trading réel {health.data.live_trading_enabled ? "activé" : "désactivé"}
          </p>
        </>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">
          {health.isLoading ? "…" : <>Démarrez le moteur avec <code className="rounded bg-muted px-1">pnpm quant:api</code> pour voir vos données.</>}
        </p>
      )}
    </div>
  );
}

export default function Index() {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-border/50">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,hsl(var(--primary)/0.18),transparent_55%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--border)/0.35)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border)/0.35)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
        <Page className="relative grid items-center gap-10 py-12 md:py-16 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-6">
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <FlaskConical className="h-3.5 w-3.5" />
              Laboratoire de recherche · XAUUSD & Forex · simulation
            </span>
            <h1 className="max-w-2xl text-4xl font-bold leading-[1.1] tracking-tight md:text-5xl">
              Tester une idée de trading <span className="text-primary">avant</span> d'y risquer un centime.
            </h1>
            <p className="max-w-xl text-base text-muted-foreground md:text-lg">
              AI Trader Optimizer rejoue vos règles sur l'historique, compte les coûts, applique des limites de risque et montre
              chaque refus. Les résultats sont traçables et recalculables, jamais embellis.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/backtest" data-testid="home-cta-backtest">
                  Lancer un backtest <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/optimizer">Voir les stratégies</Link>
              </Button>
            </div>
          </div>
          <LabState />
        </Page>
      </section>

      <Page className="space-y-12">
        <section className="space-y-5">
          <div>
            <h2 className="text-xl font-semibold">Comment ça marche</h2>
            <p className="text-sm text-muted-foreground">Quatre étapes, toutes réalisées par le moteur Python.</p>
          </div>
          <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {STEPS.map((s) => (
              <li key={s.title} className="flex flex-col rounded-xl border border-border/60 bg-card/70 p-5">
                <s.icon className="h-5 w-5 text-primary" />
                <h3 className="mt-3 font-semibold">{s.title}</h3>
                <p className="mt-1 flex-1 text-sm text-muted-foreground">{s.text}</p>
                <Link to={s.href} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                  {s.cta} <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <section className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold">Ce qui existe vraiment</h2>
              <p className="text-sm text-muted-foreground">Chaque écran affiche sa nature dans le menu.</p>
            </div>
            <ul className="divide-y divide-border/50 rounded-xl border border-border/60 bg-card/70" data-testid="home-modules">
              {NAV_ITEMS.filter((i) => i.href !== "/").map((i) => (
                <li key={i.href}>
                  <Link to={i.href} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/40">
                    <i.icon className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">
                      <span className="block text-sm font-medium">{i.label}</span>
                      <span className="block text-xs text-muted-foreground">{i.hint}</span>
                    </span>
                    <StatusChip status={i.status} />
                  </Link>
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">
              <StatusChip status="engine" className="mr-1" /> chiffres du moteur ·{" "}
              <StatusChip status="reference" className="mx-1" /> documentation, hypothèses ·{" "}
              <StatusChip status="locked" className="mx-1" /> désactivé volontairement
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold">Les règles du laboratoire</h2>
              <p className="text-sm text-muted-foreground">Elles sont appliquées par le code, pas seulement écrites ici.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {PRINCIPLES.map((p) => (
                <div key={p.title} className="rounded-xl border border-border/60 bg-card/70 p-4">
                  <p className="flex items-center gap-2 text-sm font-semibold">
                    <p.icon className="h-4 w-4 text-primary" />
                    {p.title}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{p.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <p className="border-t border-border/50 pt-6 text-xs text-muted-foreground">
          Le trading sur le Forex et les CFD comporte un risque élevé de perte. Les performances simulées ne préjugent pas des
          résultats futurs et ne constituent pas un conseil en investissement.
        </p>
      </Page>
    </div>
  );
}
