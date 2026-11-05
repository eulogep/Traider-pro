import type { RiskConfig, RiskPolicyInfo } from "@shared/quant-api";
import { Facts } from "@/components/layout/Page";
import { fmtValue } from "@/lib/format";
import { cn } from "@/lib/utils";

const yesNo = (v: boolean) => (v ? "oui" : "non");
const opt = (v: number | null, unit = "") => (v == null ? "sans limite" : `${fmtValue(v)}${unit}`);

/** Read-only view of the Risk Guardian profile saved in the engine (values displayed as returned). */
export function RiskProfileFacts({ risk }: { risk: RiskConfig }) {
  return (
    <Facts
      cols={3}
      items={[
        ["Risque par trade", `${fmtValue(risk.risk_per_trade_pct)} % du capital`],
        ["Perte journalière max", `${fmtValue(risk.max_daily_loss_pct)} %`],
        ["Drawdown max", `${fmtValue(risk.max_drawdown_pct)} %`],
        ["Positions ouvertes max", String(risk.max_open_positions)],
        ["Trades par jour max", String(risk.max_trades_per_day)],
        ["Pertes par jour max", opt(risk.max_losses_per_day)],
        ["Pertes consécutives max", `${opt(risk.max_consecutive_losses)} (${risk.consecutive_loss_scope === "day" ? "par jour" : "sur le run"})`],
        ["Arrêt après un jour gagnant", yesNo(risk.stop_after_daily_win)],
        ["Risque prévu compté dans la limite jour", yesNo(risk.daily_limit_includes_planned_risk)],
        ["Risque prévu compté dans le drawdown", yesNo(risk.drawdown_limit_includes_planned_risk)],
        ["Fuseau du « jour »", risk.day_timezone],
        ["Martingale", risk.allow_martingale ? "autorisée" : "interdite par le code"],
      ]}
    />
  );
}

export function PolicyBadge({ policy }: { policy: RiskPolicyInfo }) {
  const supervised = policy.mode === "supervised";
  return (
    <span
      data-testid="policy-mode"
      className={cn(
        "rounded border px-2 py-0.5 text-xs",
        supervised ? "border-primary/30 bg-primary/10 text-primary" : "border-blue-500/30 bg-blue-500/10 text-blue-300",
      )}
    >
      {supervised ? "mode supervisé · profil imposé" : "mode recherche · profil modifiable par run"}
    </span>
  );
}
