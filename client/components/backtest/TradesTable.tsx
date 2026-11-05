import { useMemo, useState } from "react";
import type { Trade } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { fmtNum, fmtShortDateTime, fmtSignedMoney } from "@/lib/format";

const PAGE = 25;
const EXIT_LABELS: Record<string, string> = {
  TP: "Objectif", TP_GAP: "Objectif (gap)", SL: "Stop", SL_GAP: "Stop (gap)", TIME_EXIT: "Durée max",
  SESSION_END: "Fin de session", END_OF_DATA: "Fin des données",
};
type Side = "ALL" | "BUY" | "SELL";
type Outcome = "ALL" | "WIN" | "LOSS";

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      className={cn("rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground hover:text-foreground")}>
      {children}
    </button>
  );
}

export function TradesTable({ trades, currency }: { trades: Trade[]; currency: string }) {
  const [side, setSide] = useState<Side>("ALL");
  const [outcome, setOutcome] = useState<Outcome>("ALL");
  const [page, setPage] = useState(0);
  // filtering = selecting rows returned by the engine; nothing is recomputed
  const rows = useMemo(() => trades.filter((t) =>
    (side === "ALL" || t.direction === side) &&
    (outcome === "ALL" || (outcome === "WIN" ? t.net_pnl > 0 : t.net_pnl <= 0))), [trades, side, outcome]);
  const pageRows = rows.slice(page * PAGE, page * PAGE + PAGE);
  const set = <T,>(fn: (v: T) => void) => (v: T) => { fn(v); setPage(0); };

  if (trades.length === 0) {
    return <p className="text-sm text-muted-foreground" data-testid="no-trades">
      Aucune transaction simulée : consultez l'onglet « Signaux refusés ».</p>;
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {(["ALL", "BUY", "SELL"] as Side[]).map((v) => (
          <Chip key={v} active={side === v} onClick={() => set(setSide)(v)}>{v === "ALL" ? "Tous les sens" : v}</Chip>
        ))}
        <span className="mx-1 h-4 w-px bg-border" />
        {(["ALL", "WIN", "LOSS"] as Outcome[]).map((v) => (
          <Chip key={v} active={outcome === v} onClick={() => set(setOutcome)(v)}>
            {v === "ALL" ? "Tous les résultats" : v === "WIN" ? "Gagnants" : "Perdants / nuls"}
          </Chip>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">{rows.length} / {trades.length} transactions</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border/60">
        <Table data-testid="trades-table" className="text-xs">
          <TableHeader>
            <TableRow className="bg-muted/30 [&>th]:h-9 [&>th]:whitespace-nowrap [&>th]:px-2">
              <TableHead>#</TableHead>
              <TableHead>Sens</TableHead>
              <TableHead>Entrée → sortie (UTC)</TableHead>
              <TableHead className="text-right">Lots</TableHead>
              <TableHead className="text-right">Prix entrée → sortie</TableHead>
              <TableHead>Motif</TableHead>
              <TableHead className="text-right">Risque prévu</TableHead>
              <TableHead className="text-right">P&L net</TableHead>
              <TableHead className="text-right">R</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageRows.map((t) => {
              const win = t.net_pnl > 0;
              const tone = win ? "text-trading-green-500" : "text-trading-red-500";
              const sameDay = t.entry_time.slice(0, 10) === t.exit_time.slice(0, 10);
              return (
                <TableRow key={t.trade_id} className="[&>td]:whitespace-nowrap [&>td]:px-2 [&>td]:py-1.5">
                  <TableCell className="text-muted-foreground">{t.trade_id}</TableCell>
                  <TableCell>
                    <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold",
                      t.direction === "BUY" ? "bg-sky-500/15 text-sky-400" : "bg-fuchsia-500/15 text-fuchsia-400")}>
                      {t.direction}
                    </span>
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {fmtShortDateTime(t.entry_time)}
                    <span className="text-muted-foreground"> → {sameDay ? fmtShortDateTime(t.exit_time).slice(6) : fmtShortDateTime(t.exit_time)}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{fmtNum(t.lots)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {fmtNum(t.entry_price, 3)} <span className="text-muted-foreground">→</span> {fmtNum(t.exit_price, 3)}
                  </TableCell>
                  <TableCell>
                    {EXIT_LABELS[t.exit_reason] ?? t.exit_reason}
                    {t.gap_during_trade && <span className="ml-1 text-amber-400" title="Trou de données pendant le trade">⚠</span>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">{fmtNum(t.planned_risk)}</TableCell>
                  <TableCell className={cn("text-right font-semibold tabular-nums", tone)}>{fmtSignedMoney(t.net_pnl, currency)}</TableCell>
                  <TableCell className={cn("text-right tabular-nums", tone)}>{fmtNum(t.r_multiple)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {rows.length ? `${page * PAGE + 1}–${Math.min(rows.length, page * PAGE + PAGE)} sur ${rows.length}` : "Aucun résultat pour ce filtre"}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Précédent</Button>
          <Button variant="outline" size="sm" disabled={(page + 1) * PAGE >= rows.length} onClick={() => setPage(page + 1)}>Suivant</Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        MAE/MFE (dans les exports) : bornes inférieures prouvées sur bougies OHLC, pas une trajectoire exacte.
      </p>
    </div>
  );
}
