import { useQuery } from "@tanstack/react-query";
import { Ban, CheckCircle2, Circle, Lock, Route, ShieldCheck, ShieldHalf } from "lucide-react";
import { Callout, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { PolicyBadge, RiskProfileFacts } from "@/components/RiskProfile";
import { quantApi } from "@/lib/quantApi";
import { cn } from "@/lib/utils";

/** From quant/docs/ROADMAP.md — each step is a precondition of the next one. */
const ROADMAP: Array<{ v: string; title: string; text: string; done?: boolean }> = [
  { v: "0.3.1", title: "Moteur de backtest durci", text: "Résultats traçables (empreinte SHA-256), reproductibles, coûts et Risk Guardian appliqués.", done: true },
  { v: "0.4", title: "Validation hors échantillon", text: "Étiquetage de chaque signal, walk-forward purgé, modèle de filtrage, intervalles de confiance, robustesse Monte Carlo.", done: true },
  { v: "0.5", title: "Stratégie du trader", text: "Entretien, formalisation MACD M15/M1, tests sur exemples annotés, puis étude de validation sur son historique réel." },
  { v: "0.6", title: "Avantage confirmé sur période future", text: "Une période jamais utilisée (après la dernière étude) doit confirmer le verdict, coûts réels du courtier inclus." },
  { v: "0.7", title: "Compte démo, sous supervision", text: "Processus séparé, identifiants hors dépôt, approbation humaine de chaque ordre, journal d'audit, arrêt d'urgence." },
  { v: "1.0", title: "Réel — éventuel", text: "Seulement si les résultats démo sont reproductibles, après revue du risque et du cadre juridique." },
];

function LockRow({ label, value, safe }: { label: string; value: string; safe: boolean }) {
  return (
    <li className="flex items-center justify-between gap-4 border-b border-border/40 py-2.5 last:border-0">
      <span className="flex items-center gap-2 text-sm">
        {safe ? <Lock className="h-4 w-4 text-primary" /> : <Ban className="h-4 w-4 text-red-400" />}
        {label}
      </span>
      <code className={cn("rounded px-2 py-0.5 text-xs", safe ? "bg-primary/10 text-primary" : "bg-red-500/15 text-red-300")}>{value}</code>
    </li>
  );
}

/** Execution — deliberately disabled. The locks shown are read live from the engine, not asserted by the UI. */
export default function Automation() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const policy = useQuery({ queryKey: ["risk-policy"], queryFn: () => quantApi.riskPolicy(), enabled: online });
  const h = health.data;

  return (
    <Page>
      <PageHeader
        icon={Lock}
        title="Exécution & automatisation"
        status="locked"
        description="Aucun robot, aucun ordre, aucune connexion courtier — ni réel, ni démo. Cette page montre pourquoi, et ce qu'il faudrait prouver avant d'y penser."
      />

      <Callout tone="locked" title="Désactivée par conception">
        Le logiciel ne contient aucun adaptateur d'exécution. Il n'y a donc rien à activer ici : un interrupteur « trading auto »
        serait un mensonge. Toute exécution future passera par le Risk Guardian et une validation humaine.
      </Callout>

      {health.isError && <OfflineNotice />}

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Verrous déclarés par le moteur" icon={ShieldCheck} testId="execution-locks"
          description="Lus en direct sur /api/v1/health — ce n'est pas l'interface qui l'affirme.">
          {h ? (
            <ul>
              <LockRow label="Mode d'exécution" value={h.execution_mode} safe={h.execution_mode === "simulation"} />
              <LockRow label="Trading réel" value={h.live_trading_enabled ? "activé" : "désactivé"} safe={!h.live_trading_enabled} />
              <LockRow label="Trading sur compte démo" value={h.demo_trading_enabled ? "activé" : "désactivé"} safe={!h.demo_trading_enabled} />
              <LockRow label="Routes d'envoi d'ordre" value={String(h.order_routes)} safe={h.order_routes === 0} />
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">{health.isLoading ? "Lecture…" : "Moteur injoignable : verrous non vérifiables."}</p>
          )}
        </Section>

        <Section title="Ce qui est refusé, quoi qu'il arrive" icon={Ban}>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {[
              "Demander ou stocker un identifiant / mot de passe de courtier",
              "Augmenter la taille après une perte (martingale) — refusé par le code",
              "Dépasser le risque par trade, la perte journalière ou le drawdown fixés",
              "Présenter un résultat simulé comme un gain réalisable",
              "Exposer l'API hors de la machine (écoute 127.0.0.1 uniquement)",
            ].map((t) => (
              <li key={t} className="flex gap-2"><Ban className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />{t}</li>
            ))}
          </ul>
        </Section>
      </div>

      {policy.data && (
        <Section title="Risk Guardian — profil enregistré" icon={ShieldHalf} actions={<PolicyBadge policy={policy.data} />}
          description="Appliqué à chaque signal simulé : un signal qui dépasse une limite est refusé et le refus est journalisé.">
          <RiskProfileFacts risk={policy.data.saved_profile} />
        </Section>
      )}

      <Section title="Feuille de route avant toute exécution" icon={Route}
        description="Chaque étape doit être validée avant la suivante (quant/docs/ROADMAP.md).">
        <ol className="relative space-y-5 border-l border-border/60 pl-6" data-testid="execution-roadmap">
          {ROADMAP.map((r) => (
            <li key={r.v} className="relative">
              <span className="absolute -left-[33px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-background">
                {r.done ? <CheckCircle2 className="h-4 w-4 text-primary" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
              </span>
              <p className="text-sm font-medium">
                <code className="mr-2 text-xs text-muted-foreground">v{r.v}</code>
                {r.title}
                {r.done && <span className="ml-2 text-xs text-primary">livrée</span>}
              </p>
              <p className="text-sm text-muted-foreground">{r.text}</p>
            </li>
          ))}
        </ol>
      </Section>
    </Page>
  );
}
