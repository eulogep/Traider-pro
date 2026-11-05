import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CandlestickChart, Coins, FileDown, KeyRound, Ruler, Upload } from "lucide-react";
import { INSTRUMENTS } from "@shared/instruments";
import { Button } from "@/components/ui/button";
import { Callout, Facts, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { quantApi } from "@/lib/quantApi";

const MT5_STEPS: Array<{ title: string; text: string }> = [
  { title: "Ouvrir la fenêtre Symboles", text: "Dans MetaTrader 5 : menu Affichage → Symboles (Ctrl+U)." },
  { title: "Demander les barres", text: "Onglet « Barres » : choisir le symbole (ex. XAUUSD), la période M1 et les dates, puis « Demander »." },
  { title: "Exporter", text: "Cliquer « Exporter les barres » : MT5 écrit un fichier CSV (date, heure, OHLC, volumes, spread)." },
  {
    title: "Importer dans Backtests",
    text: "« Importer un CSV » : indiquer la source (courtier / serveur), la nature « Historique réel » et le fuseau horaire du serveur. Ne le devinez pas : demandez-le au courtier.",
  },
];

/** Instruments & market data — reference page: contract hypotheses, engine defaults, how data gets in. No broker link. */
export default function Trading() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const defaults = useQuery({ queryKey: ["defaults"], queryFn: () => quantApi.getDefaults(), enabled: online });
  const d = defaults.data;
  const num = (v: number | null | undefined) => (v == null ? "non renseigné" : v.toLocaleString("fr-FR"));

  return (
    <Page>
      <PageHeader
        icon={CandlestickChart}
        title="Instruments & données de marché"
        status="reference"
        description="Les caractéristiques de contrat et de coûts que le moteur suppose, et comment y faire entrer un historique réel."
        actions={
          <Button asChild variant="outline">
            <Link to="/backtest"><Upload className="mr-2 h-4 w-4" />Importer un historique</Link>
          </Button>
        }
      />

      <Callout tone="safe" title="Pas de connexion MetaTrader 5 dans l'application">
        Aucun identifiant ni mot de passe n'est demandé ou stocké, et aucun cours n'est simulé ici. Les données entrent uniquement
        par fichier exporté, validé par le moteur avant usage.
      </Callout>

      {health.isError && <OfflineNotice />}

      {d && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Contrat par défaut du moteur" icon={Ruler} testId="engine-contract"
            description={d.contract.source}>
            <Facts
              items={[
                ["Symbole", d.contract.symbol],
                ["Taille de contrat (unités / lot)", num(d.contract.contract_size)],
                ["Lot minimum", num(d.contract.min_lot)],
                ["Pas de lot", num(d.contract.lot_step)],
                ["Lot maximum", num(d.contract.max_lot)],
                ["Devise de cotation", d.contract.quote_currency ?? "non renseignée"],
              ]}
            />
          </Section>
          <Section title="Coûts supposés par les backtests" icon={Coins} testId="engine-costs"
            description="Valeurs fixes hypothétiques, appliquées à chaque transaction simulée.">
            <Facts
              items={[
                ["Spread (en prix)", num(d.costs.spread)],
                ["Glissement (en prix)", num(d.costs.slippage)],
                [`Commission / lot / côté (${d.account_currency})`, num(d.costs.commission_per_lot_per_side)],
                ["Capital initial par défaut", `${num(d.initial_equity)} ${d.account_currency}`],
                ["Bougie touchant SL et TP", d.same_bar_policy === "stop_first" ? "stop d'abord (prudent)" : d.same_bar_policy],
                ["Clôture en fin de session", d.close_at_session_end ? "oui" : "non"],
              ]}
            />
            <p className="mt-4 text-xs text-muted-foreground">
              Un vrai spread varie (news, ouverture, nuit). Comparez ces valeurs avec celles de votre courtier avant de tirer une
              conclusion.
            </p>
          </Section>
        </div>
      )}

      <Section title="Importer un historique depuis MetaTrader 5" icon={FileDown} testId="mt5-export-guide"
        description="La seule manière de faire entrer des cotations réelles dans le laboratoire.">
        <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {MT5_STEPS.map((s, i) => (
            <li key={s.title} className="rounded-lg border border-border/50 bg-background/40 p-4">
              <span className="flex h-7 w-7 items-center justify-center rounded-full border border-primary/40 text-sm font-semibold text-primary">{i + 1}</span>
              <p className="mt-3 text-sm font-medium">{s.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-muted-foreground">
          Le fichier est refusé en entier s'il contient une erreur (prix incohérents, doublons, fractions de seconde). Les trous
          sont signalés, jamais comblés.
        </p>
      </Section>

      <Section title="Spécifications de référence" icon={KeyRound}
        description="Valeurs CFD / FX typiques — HYPOTHÈSES à vérifier chez le courtier. Elles ne servent pas au moteur.">
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm" data-testid="instrument-specs">
            <thead>
              <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
                <th className="px-5 py-2 font-medium">Symbole</th>
                <th className="px-2 py-2 text-right font-medium">Contrat / lot</th>
                <th className="px-2 py-2 font-medium">Base</th>
                <th className="px-2 py-2 font-medium">Cotation</th>
                <th className="px-5 py-2 text-right font-medium">Décimales</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(INSTRUMENTS).map((s) => (
                <tr key={s.symbol} className="border-b border-border/30">
                  <td className="px-5 py-2.5 font-medium">{s.symbol}</td>
                  <td className="px-2 py-2.5 text-right tabular-nums">{s.contractSize.toLocaleString("fr-FR")}</td>
                  <td className="px-2 py-2.5">{s.baseCurrency}</td>
                  <td className="px-2 py-2.5">{s.quoteCurrency}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums">{s.digits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </Page>
  );
}
