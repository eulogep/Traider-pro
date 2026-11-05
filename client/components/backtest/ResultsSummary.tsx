import { AlertTriangle, ArrowDownRight, ArrowUpRight, Coins, Gauge, Percent, Scale, Target, TrendingDown } from "lucide-react";
import type { ReactNode } from "react";
import type { Metrics } from "@shared/quant-api";
import { cn } from "@/lib/utils";
import { fmtMoney, fmtNum, fmtPct, fmtSignedMoney } from "@/lib/format";

/** Tone is chosen from the SIGN of an engine value — a display decision, never a computation. */
type Tone = "up" | "down" | "neutral" | "warn";
const sign = (v: number | null | undefined): Tone => (v == null ? "neutral" : v > 0 ? "up" : v < 0 ? "down" : "neutral");
const TONE: Record<Tone, string> = {
  up: "text-trading-green-500",
  down: "text-trading-red-500",
  neutral: "text-foreground",
  warn: "text-amber-500",
};

function Kpi(props: {
  testId: string;
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  icon: ReactNode;
  large?: boolean;
  title?: string;
}) {
  return (
    <div
      data-testid={props.testId}
      title={props.title}
      className={cn(
        "rounded-xl border border-border/60 bg-card/80 p-4 shadow-sm",
        props.large && "bg-gradient-to-br from-card to-muted/30",
      )}
    >
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {props.icon}
        {props.label}
      </p>
      <p className={cn("mt-1 font-semibold tabular-nums", props.large ? "text-2xl" : "text-lg", TONE[props.tone ?? "neutral"])}>
        {props.value}
      </p>
      {props.sub && <p className="mt-0.5 text-xs text-muted-foreground">{props.sub}</p>}
    </div>
  );
}

export function ResultsSummary({ m, currency }: { m: Metrics; currency: string }) {
  const pfTone: Tone = m.profit_factor == null ? "neutral" : m.profit_factor >= 1 ? "up" : "down";
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 2xl:grid-cols-4">
        <Kpi large testId="kpi-pnl" label="P&L net simulé" icon={m.net_pnl >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
          value={fmtSignedMoney(m.net_pnl, currency)} sub={`${fmtPct(m.return_pct)} du capital`} tone={sign(m.net_pnl)} />
        <Kpi large testId="kpi-winrate" label="Win rate" icon={<Target className="h-3.5 w-3.5" />}
          value={fmtPct(m.win_rate_pct, 1)} sub={`${m.trades} transactions`} />
        <Kpi large testId="kpi-pf" label="Profit factor" icon={<Scale className="h-3.5 w-3.5" />}
          value={fmtNum(m.profit_factor)} sub={m.unavailable.profit_factor ?? "gains bruts / pertes brutes"} tone={pfTone} />
        <Kpi large testId="kpi-dd" label="Drawdown max (MTM)" icon={<TrendingDown className="h-3.5 w-3.5" />}
          value={fmtPct(m.max_dd_mtm_pct)} sub={`clôturé ${fmtPct(m.max_dd_closed_pct)}`} tone={m.max_dd_mtm_pct < 0 ? "down" : "neutral"}
          title={m.drawdown_note} />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-6">
        <Kpi testId="kpi-initial" label="Capital initial" icon={<Coins className="h-3.5 w-3.5" />} value={fmtMoney(m.initial_equity, currency)} />
        <Kpi testId="kpi-final" label="Capital final" icon={<Coins className="h-3.5 w-3.5" />} value={fmtMoney(m.final_equity, currency)}
          tone={sign(m.net_pnl)} />
        <Kpi testId="kpi-trades" label="Transactions" icon={<Gauge className="h-3.5 w-3.5" />} value={String(m.trades)}
          sub={`${m.signals} signaux · ${m.signals_entered} entrés`} />
        <Kpi testId="kpi-expectancy" label="Espérance / trade" icon={<Percent className="h-3.5 w-3.5" />}
          value={fmtMoney(m.expectancy, currency)} sub={m.expectancy_r == null ? undefined : `${fmtNum(m.expectancy_r, 3)} R`}
          tone={sign(m.expectancy)} />
        <Kpi testId="kpi-costs" label="Coûts estimés" icon={<Coins className="h-3.5 w-3.5" />} value={fmtMoney(m.total_costs, currency)}
          sub={`avant coûts : ${fmtSignedMoney(m.pnl_before_costs, currency)}`} />
        <Kpi testId="kpi-beyond" label="Pertes > risque prévu" icon={<AlertTriangle className="h-3.5 w-3.5" />}
          value={String(m.losses_beyond_planned_risk ?? 0)} sub="gaps / glissement" tone={(m.losses_beyond_planned_risk ?? 0) > 0 ? "warn" : "neutral"} />
      </div>
      {!m.sample_sufficient && (
        <p data-testid="sample-note"
          className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {m.sample_note}
        </p>
      )}
    </div>
  );
}
