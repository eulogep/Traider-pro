import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Cpu, HardDrive, Pencil, RotateCcw, Settings as SettingsIcon, ShieldCheck, ShieldHalf, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Callout, Facts, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { PolicyBadge, RiskProfileFacts } from "@/components/RiskProfile";
import { fmtValue } from "@/lib/format";
import { quantApi } from "@/lib/quantApi";
import { useSettings } from "@/lib/settingsContext";

function Cmd({ children }: { children: string }) {
  return <code className="block overflow-x-auto whitespace-pre rounded-md border border-border/60 bg-background/70 px-3 py-2 text-xs">{children}</code>;
}

/** Settings — the engine's real configuration, read-only here; where and how to change it is stated explicitly. */
export default function Settings() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const defaults = useQuery({ queryKey: ["defaults"], queryFn: () => quantApi.getDefaults(), enabled: online });
  const policy = useQuery({ queryKey: ["risk-policy"], queryFn: () => quantApi.riskPolicy(), enabled: online });
  const { resetSettings } = useSettings();
  const [cleared, setCleared] = useState(false);
  const h = health.data;
  const d = defaults.data;

  return (
    <Page>
      <PageHeader
        icon={SettingsIcon}
        title="Paramètres"
        status="engine"
        description="La configuration réelle du moteur Python. Elle est affichée ici en lecture seule : aucune valeur de cette page ne vient du navigateur."
      />
      {health.isError && <OfflineNotice />}

      {h && (
        <Section title="Moteur" icon={Cpu} testId="settings-engine">
          <Facts
            cols={3}
            items={[
              ["Version du logiciel", h.software_version],
              ["Version du moteur", <code key="e" className="text-xs">{h.engine_version}</code>],
              ["Empreinte du code", <code key="c" className="text-xs">{h.code_hash}</code>],
              ["Mode", h.execution_mode],
              ["Adresse de l'API", "127.0.0.1:8765 (locale)"],
              ["Routes d'ordre", String(h.order_routes)],
            ]}
          />
        </Section>
      )}

      {d && (
        <Section title="Valeurs par défaut des backtests" icon={Wallet} testId="settings-defaults"
          description="Préremplies dans Backtests ; chaque run enregistre la configuration exacte qu'il a utilisée.">
          <Facts
            cols={3}
            items={[
              ["Capital initial", `${fmtValue(d.initial_equity)} ${d.account_currency}`],
              ["Spread (en prix)", fmtValue(d.costs.spread)],
              ["Glissement (en prix)", fmtValue(d.costs.slippage)],
              ["Commission / lot / côté", `${fmtValue(d.costs.commission_per_lot_per_side)} ${d.account_currency}`],
              ["Contrat", `${d.contract.symbol} · ${fmtValue(d.contract.contract_size)} unités / lot`],
              ["Lots (min · pas · max)", `${fmtValue(d.contract.min_lot)} · ${fmtValue(d.contract.lot_step)} · ${fmtValue(d.contract.max_lot)}`],
            ]}
          />
          <p className="mt-3 text-xs text-muted-foreground">Source du contrat : {d.contract.source}</p>
        </Section>
      )}

      {policy.data && (
        <Section title="Profil de risque enregistré" icon={ShieldHalf} actions={<PolicyBadge policy={policy.data} />} testId="settings-risk"
          description={policy.data.enforced
            ? "Mode supervisé : le serveur refuse tout run qui relâche ces limites."
            : "Mode recherche : un run peut utiliser d'autres limites ; il est alors signalé comme différent du profil enregistré."}>
          <RiskProfileFacts risk={policy.data.saved_profile} />
        </Section>
      )}

      <Section title="Modifier ces valeurs" icon={Pencil} description="Volontairement hors du navigateur : seul le laboratoire local écrit la configuration.">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-2 text-sm">
            <p className="font-medium">Capital, coûts, contrat et profil de risque</p>
            <p className="text-muted-foreground">Dans la console de recherche Streamlit (locale), page de lancement des runs :</p>
            <Cmd>{"cd quant && .venv/bin/streamlit run app.py"}</Cmd>
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-medium">Imposer le profil de risque à chaque run</p>
            <p className="text-muted-foreground">Démarrer l'API en mode supervisé :</p>
            <Cmd>{"ATO_RISK_POLICY=supervised pnpm quant:api"}</Cmd>
          </div>
        </div>
      </Section>

      <div className="grid gap-6 md:grid-cols-2">
        <Section title="Sécurité de l'API locale" icon={ShieldCheck}>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>Écoute uniquement sur la machine (127.0.0.1) ; un autre hôte est refusé.</li>
            <li>Les écritures exigent l'en-tête <code>X-ATO-Request</code> et une origine locale : une page web étrangère ne peut rien déclencher.</li>
            <li>Taille des envois, nombre de lignes, calculs simultanés et espace disque sont plafonnés.</li>
            <li>Aucun secret : pas de clé, pas d'identifiant de courtier.</li>
          </ul>
        </Section>
        <Section title="Données de ce navigateur" icon={HardDrive}>
          <p className="text-sm text-muted-foreground">
            Le navigateur ne garde que des préférences d'affichage (jamais de mot de passe : ils sont filtrés avant tout
            enregistrement). Les données, runs et réglages du moteur restent dans <code>quant/data/</code>.
          </p>
          <Button variant="outline" size="sm" className="mt-4" onClick={() => { resetSettings(); setCleared(true); }}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Réinitialiser les préférences locales
          </Button>
          {cleared && <p className="mt-2 text-xs text-primary">Préférences locales réinitialisées.</p>}
        </Section>
      </div>

      <Callout tone="info">
        Les anciennes options de cet écran (connexion MT5, notifications, trading en un clic, double authentification, sauvegarde
        cloud…) ont été retirées : elles n'étaient reliées à aucune fonction réelle du logiciel.
      </Callout>
    </Page>
  );
}
