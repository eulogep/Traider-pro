import { Settings, ShieldCheck } from "lucide-react";
import type { BacktestConfig, RiskPolicyInfo, StrategyItem } from "@shared/quant-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtValue } from "@/lib/format";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

type ParamValue = number | string | boolean;

interface Props {
  strategies: StrategyItem[];
  strategyKey: string | null;
  onStrategy: (key: string) => void;
  config: BacktestConfig;
  onConfig: (c: BacktestConfig) => void;
  tradeFrom: string;
  tradeTo: string;
  onPeriod: (from: string, to: string) => void;
  policy?: RiskPolicyInfo;
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{children}</p>;
}

function numberOr(value: string, fallback: number): number {
  const n = Number(value);
  return value.trim() === "" || !Number.isFinite(n) ? fallback : n;
}

export function ConfigPanel(p: Props) {
  const runnable = p.strategies.filter((s) => s.runnable);
  const notRunnable = p.strategies.filter((s) => !s.runnable);
  const current = p.strategies.find((s) => s.key === p.strategyKey);
  const params = current?.spec.params ?? {};
  const values: Record<string, ParamValue> = Object.fromEntries(
    Object.entries(params).map(([k, spec]) => [k, p.config.strategy_params[k] ?? spec.default]),
  );
  const setParam = (k: string, v: ParamValue) =>
    p.onConfig({ ...p.config, strategy_params: { ...p.config.strategy_params, [k]: v } });
  const setCost = (k: keyof BacktestConfig["costs"], v: number) =>
    p.onConfig({ ...p.config, costs: { ...p.config.costs, [k]: v } });
  const { contract, risk } = p.config;

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center text-base">
          <Settings className="mr-2 h-4 w-4" />
          Stratégie et hypothèses
        </CardTitle>
        <CardDescription>Bornes et valeurs par défaut fournies par le moteur Python.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <SectionTitle>Stratégie</SectionTitle>
          <Select value={p.strategyKey ?? undefined} onValueChange={p.onStrategy}>
            <SelectTrigger data-testid="strategy-select">
              <SelectValue placeholder="Choisir…" />
            </SelectTrigger>
            <SelectContent>
              {runnable.map((s) => (
                <SelectItem key={s.key} value={s.key}>
                  {s.spec.name} — v{s.spec.version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {current?.spec.illustrative && (
            <p className="text-xs text-amber-700 dark:text-amber-300">
              Stratégie illustrative : elle sert à tester le logiciel, aucun avantage statistique n'est supposé.
            </p>
          )}
          {notRunnable.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Non exécutables : {notRunnable.map((s) => `${s.spec.name} (${s.problems[0]})`).join(" · ")}
            </p>
          )}
        </div>

        {Object.keys(params).length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <SectionTitle>Paramètres autorisés</SectionTitle>
              {Object.keys(p.config.strategy_params).length > 0 && (
                <button type="button" className="text-xs text-primary hover:underline"
                  onClick={() => p.onConfig({ ...p.config, strategy_params: {} })}>
                  Valeurs par défaut
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
              {Object.entries(params).map(([name, spec]) => (
                <div key={name} className="space-y-1">
                  <Label htmlFor={`param-${name}`} className="block text-xs leading-tight" title={spec.description}>
                    <span className="line-clamp-1">{spec.description || name}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {name}{spec.min !== null && spec.max !== null ? ` · ${spec.min}–${spec.max}` : ""}
                    </span>
                  </Label>
                  {spec.type === "choice" ? (
                    <Select
                      value={String(values[name])}
                      onValueChange={(v) => setParam(name, v)}
                      disabled={!spec.editable}
                    >
                      <SelectTrigger id={`param-${name}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(spec.choices ?? []).map((c) => (
                          <SelectItem key={String(c)} value={String(c)}>
                            {String(c)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : spec.type === "bool" ? (
                    <Switch
                      id={`param-${name}`}
                      checked={Boolean(values[name])}
                      onCheckedChange={(v) => setParam(name, v)}
                      disabled={!spec.editable}
                    />
                  ) : (
                    <Input
                      id={`param-${name}`}
                      type="number"
                      min={spec.min ?? undefined}
                      max={spec.max ?? undefined}
                      step={spec.type === "int" ? 1 : 0.1}
                      value={String(values[name])}
                      disabled={!spec.editable}
                      onChange={(e) => setParam(name, numberOr(e.target.value, Number(spec.default)))}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <SectionTitle>Capital, coûts et période <span className="normal-case tracking-normal text-muted-foreground">(hypothèses à vérifier)</span></SectionTitle>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
            <div className="space-y-1">
              <Label htmlFor="equity" className="text-xs">
                Capital initial ({p.config.account_currency})
              </Label>
              <Input
                id="equity"
                type="number"
                min={100}
                step={500}
                value={p.config.initial_equity}
                onChange={(e) =>
                  p.onConfig({ ...p.config, initial_equity: numberOr(e.target.value, p.config.initial_equity) })
                }
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="spread" className="text-xs">Spread fixe (prix)</Label>
              <Input
                id="spread"
                type="number"
                min={0}
                step={0.05}
                value={p.config.costs.spread}
                onChange={(e) => setCost("spread", numberOr(e.target.value, p.config.costs.spread))}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="slippage" className="text-xs">Glissement / exécution (prix)</Label>
              <Input
                id="slippage"
                type="number"
                min={0}
                step={0.01}
                value={p.config.costs.slippage}
                onChange={(e) => setCost("slippage", numberOr(e.target.value, p.config.costs.slippage))}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="commission" className="text-xs">Commission / lot / côté</Label>
              <Input
                id="commission"
                type="number"
                min={0}
                step={0.5}
                value={p.config.costs.commission_per_lot_per_side}
                onChange={(e) =>
                  setCost(
                    "commission_per_lot_per_side",
                    numberOr(e.target.value, p.config.costs.commission_per_lot_per_side),
                  )
                }
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="from" className="text-xs">Entrées à partir du (UTC, optionnel)</Label>
              <Input id="from" type="date" value={p.tradeFrom} onChange={(e) => p.onPeriod(e.target.value, p.tradeTo)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="to" className="text-xs">Jusqu'au (UTC, inclus, optionnel)</Label>
              <Input id="to" type="date" value={p.tradeTo} onChange={(e) => p.onPeriod(p.tradeFrom, e.target.value)} />
            </div>
          </div>
        </div>

        <div className="space-y-2 rounded-lg border border-border/60 bg-muted/30 p-3 text-xs" data-testid="risk-summary">
          <p className="flex items-start gap-1.5 font-medium">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              Risk Guardian (fail-closed) —{" "}
              {p.policy?.enforced
                ? "mode supervisé : profil imposé par le serveur (une requête ne peut être que plus stricte)"
                : "mode recherche : ces limites sont des hypothèses modifiables, pas une politique imposée"}
            </span>
          </p>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
            <dt className="text-muted-foreground">Risque / trade</dt><dd className="text-right tabular-nums">{fmtValue(risk.risk_per_trade_pct)} %</dd>
            <dt className="text-muted-foreground">Perte jour max</dt><dd className="text-right tabular-nums">{fmtValue(risk.max_daily_loss_pct)} %</dd>
            <dt className="text-muted-foreground">Drawdown max</dt><dd className="text-right tabular-nums">{fmtValue(risk.max_drawdown_pct)} %</dd>
            <dt className="text-muted-foreground">Trades / jour</dt><dd className="text-right tabular-nums">{risk.max_trades_per_day}</dd>
            <dt className="text-muted-foreground">Contrat {contract.symbol}</dt>
            <dd className="text-right tabular-nums">{contract.contract_size == null ? "inconnu" : fmtValue(contract.contract_size)} u./lot · min {fmtValue(contract.min_lot)}</dd>
          </dl>
          <p className="text-amber-300/90">{contract.source}</p>
          <p className="text-muted-foreground">Martingale interdite. Profil et contrat modifiables dans la console Python (Risk Management / Settings).</p>
        </div>
      </CardContent>
    </Card>
  );
}
