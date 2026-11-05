import { AlertTriangle, FileSearch, Layers, Scale, ShieldAlert, TrendingDown } from "lucide-react";
import type { EaAudit, EaVerdictCode } from "@shared/quant-api";
import { Callout, Facts, Section, Tile } from "@/components/layout/Page";
import { fmtNum, fmtPct } from "@/lib/format";

const UNAVAILABLE = "—";
const num = (v: number | null | undefined, d = 2) => (v == null ? UNAVAILABLE : fmtNum(v, d));
const money = (v: number | null | undefined) => (v == null ? UNAVAILABLE : fmtNum(v, 2));

const VERDICT_TONE: Record<EaVerdictCode, "danger" | "warn" | "info"> = {
  STOP_OUT: "danger",
  MARTINGALE: "danger",
  GRID: "danger",
  RISK_SIGNS: "warn",
  NO_SIGNATURE: "info",
  INSUFFICIENT: "info",
};

/** Display only: every figure comes from the Python engine (ea_audit/). Nothing here computes money. */
export function EaAuditView({ audit }: { audit: EaAudit }) {
  const tone = VERDICT_TONE[audit.verdict.code] ?? "warn";
  const s = audit.stress;
  const b = audit.baskets;
  const e = audit.exposure;
  return (
    <div className="space-y-6" data-testid="ea-audit">
      <div data-testid="ea-verdict" data-verdict={audit.verdict.code}>
        <Callout tone={tone} title={audit.verdict.title}>
          {audit.verdict.text}
        </Callout>
      </div>

      {s && (
        <Section title="Test de résistance au pire moment" icon={TrendingDown} testId="ea-stress"
          description="Calcul fait sur l'exposition maximale réellement atteinte dans le rapport.">
          <p className="text-sm">
            Le {new Date(s.time).toLocaleString("fr-FR")}, l'EA avait <strong>{num(s.net_lots)} lot(s) net(s)</strong> ouverts
            ({s.positions} position(s)) sur {s.symbol || "l'instrument"}. Chaque unité de prix contre lui coûtait alors{" "}
            <strong>{money(s.loss_per_price_unit)}</strong> en devise du compte.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Tile label={`Mouvement en ${s.direction} pour perdre la moitié du solde`} value={num(s.adverse_move_to_lose_half)}
              sub="en unités de prix (dollars par once pour XAUUSD)" tone="down" testId="ea-move-half" />
            <Tile label={`Mouvement en ${s.direction} pour un compte à zéro`} value={num(s.adverse_move_to_zero)}
              sub="le stop-out du courtier interviendrait avant" tone="down" testId="ea-move-zero" />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">{s.note} Comparez ces distances aux mouvements réels de l'or sur
            l'historique que vous avez importé : une distance plus courte que des mouvements déjà vus signifie qu'un tel
            épisode viderait le compte.</p>
        </Section>
      )}

      {audit.flags.length > 0 && (
        <Section title="Mécanismes détectés" icon={ShieldAlert} testId="ea-flags">
          <ul className="space-y-2">
            {audit.flags.map((f) => (
              <li key={f.code} data-flag={f.code} className="flex items-start gap-2 text-sm">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                <span><strong>{f.label}</strong> — {f.detail}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Tile label="Positions empilées (même sens, max.)" value={String(e.max_positions_same_direction)} icon={Layers} />
        <Tile label="Lots ouverts au maximum" value={num(e.max_gross_lots)} sub={`entrées de ${num(e.min_entry_lot)} à ${num(e.max_entry_lot)} lot`} />
        <Tile label="Multiplicateur médian des ajouts" value={e.median_add_ratio == null ? UNAVAILABLE : `× ${num(e.median_add_ratio)}`}
          sub={`${audit.counts.adds_against_open_loss} ajout(s) contre une perte ouverte`} icon={Scale} />
        <Tile label="Séries gagnantes" value={b.win_rate == null ? UNAVAILABLE : fmtPct(b.win_rate * 100, 0)}
          sub={`gain médian ${money(b.median_win)} · pire perte ${money(b.worst_loss)}`} />
      </div>

      <Section title="Lecture du rapport" icon={FileSearch}>
        <Facts items={[
          ["Fichier", `${audit.file.name} (${audit.source.format.toUpperCase()}, ${audit.source.encoding})`],
          ["Période", audit.period ? `${new Date(audit.period.start).toLocaleDateString("fr-FR")} → ${new Date(audit.period.end).toLocaleDateString("fr-FR")}` : UNAVAILABLE],
          ["Opérations lues", audit.source.deals_read.toLocaleString("fr-FR")],
          ["Lignes refusées (jamais devinées)", audit.source.rows_rejected.toLocaleString("fr-FR")],
          ["Séries clôturées / ouvertes à la fin", `${b.count} / ${audit.counts.baskets_open_at_end}`],
          ["Taille de contrat", `${fmtNum(audit.contract.contract_size, 0)} — ${audit.contract.note}`],
        ]} />
        {audit.source.rows_rejected > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-amber-300" data-testid="ea-rejected">
            {audit.source.rejected_examples.map((r) => <li key={r.row}>Ligne {r.row} : {r.reason}</li>)}
          </ul>
        )}
        {audit.counts.unmatched_close_volume > 0 && (
          <p className="mt-2 text-xs text-amber-300">
            {num(audit.counts.unmatched_close_volume)} lot(s) clôturé(s) sans ouverture dans le rapport : il commence
            probablement en cours d'historique.
          </p>
        )}
      </Section>

      <Callout tone="info" title="Limites de cette analyse">
        <ul className="list-disc space-y-1 pl-4">
          {audit.limits.map((l) => <li key={l}>{l}</li>)}
          <li>{audit.note}</li>
        </ul>
      </Callout>
    </div>
  );
}
