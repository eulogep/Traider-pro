import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, Database, FlaskConical, History, LayoutDashboard, Plus, TrendingDown, Wallet } from "lucide-react";
import type { RunSummary } from "@shared/quant-api";
import { Button } from "@/components/ui/button";
import { KindBadge } from "@/components/backtest/DatasetPanel";
import { Callout, OfflineNotice, Page, PageHeader, Section, Tile } from "@/components/layout/Page";
import { quantApi } from "@/lib/quantApi";
import { fmtDateTime, fmtMoney, fmtNum, fmtPct, fmtSignedMoney, UNAVAILABLE } from "@/lib/format";
import { cn } from "@/lib/utils";

const AXIS = { stroke: "hsl(var(--muted-foreground))", fontSize: 11 };
const signTone = (v: number | null | undefined) => (v == null ? "neutral" : v > 0 ? "up" : v < 0 ? "down" : "neutral") as "up" | "down" | "neutral";
const toneCls = (v: number | null | undefined) =>
  cn("tabular-nums", signTone(v) === "up" && "text-trading-green-500", signTone(v) === "down" && "text-trading-red-500");
const money = (r: RunSummary, v: number | null) => (r.account_currency ? fmtSignedMoney(v, r.account_currency) : UNAVAILABLE);

/** Equity curve of one run, as computed and stored by the engine (display only). */
function LatestEquity({ run }: { run: RunSummary }) {
  const eq = useQuery({ queryKey: ["equity-mini", run.run_id], queryFn: () => quantApi.getEquity(run.run_id, 400) });
  return (
    <div className="h-56">
      {eq.isLoading && <div className="h-full animate-pulse rounded-lg bg-muted/40" />}
      {eq.isError && <p className="text-sm text-red-400">{(eq.error as Error).message}</p>}
      {eq.data && (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={eq.data.points} margin={{ left: 4, right: 8, top: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
            <XAxis dataKey="timestamp" tickFormatter={(v: string) => v.slice(5, 10).replace("-", "/")} minTickGap={48} {...AXIS} />
            <YAxis domain={["auto", "auto"]} width={64} tickFormatter={(v: number) => fmtNum(v, 0)} {...AXIS} />
            <Tooltip
              contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              labelFormatter={(v) => fmtDateTime(String(v))}
              formatter={(v: number) => [fmtMoney(v, run.account_currency ?? ""), "Capital clôturé"]}
            />
            <Line type="stepAfter" dataKey="closed_equity" stroke="#22c55e" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function RunsTable({ runs }: { runs: RunSummary[] }) {
  const navigate = useNavigate();
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm" data-testid="runs-table">
        <thead>
          <tr className="border-b border-border/60 text-left text-xs text-muted-foreground">
            <th className="px-5 py-2 font-medium">Calculé le (UTC)</th>
            <th className="px-2 py-2 font-medium">Stratégie</th>
            <th className="px-2 py-2 font-medium">Données</th>
            <th className="px-2 py-2 text-right font-medium">Trades</th>
            <th className="px-2 py-2 text-right font-medium">P&L net</th>
            <th className="px-2 py-2 text-right font-medium">Win rate</th>
            <th className="px-2 py-2 text-right font-medium">PF</th>
            <th className="px-5 py-2 text-right font-medium">DD max</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.run_id}
              tabIndex={0}
              onClick={() => navigate(`/backtest?run=${encodeURIComponent(r.run_id)}`)}
              onKeyDown={(e) => e.key === "Enter" && navigate(`/backtest?run=${encodeURIComponent(r.run_id)}`)}
              className="cursor-pointer border-b border-border/30 transition-colors hover:bg-muted/40 focus:bg-muted/40 focus:outline-none"
            >
              <td className="whitespace-nowrap px-5 py-2.5 tabular-nums text-muted-foreground">{r.created_at.slice(0, 16).replace("T", " ")}</td>
              <td className="max-w-[220px] truncate px-2 py-2.5 font-mono text-xs">{r.strategy_key}</td>
              <td className="px-2 py-2.5">
                <span className={cn("rounded px-1.5 py-0.5 text-[11px]", r.data_kind === "synthetic" ? "bg-red-500/15 text-red-300" : "bg-blue-500/15 text-blue-300")}>
                  {r.data_kind === "synthetic" ? "synthétique" : r.data_kind === "historical" ? "historique" : r.data_kind}
                </span>
              </td>
              {r.integrity === "refusée" ? (
                <td colSpan={5} className="px-5 py-2.5 text-xs text-red-300" title={r.integrity_error ?? undefined} data-testid="run-refused">
                  refusé : intégrité non vérifiée — aucun chiffre affiché
                </td>
              ) : (
                <>
                  <td className="px-2 py-2.5 text-right tabular-nums">{r.trades ?? UNAVAILABLE}</td>
                  <td className={cn("whitespace-nowrap px-2 py-2.5 text-right", toneCls(r.net_pnl))}>{money(r, r.net_pnl)}</td>
                  <td className="px-2 py-2.5 text-right tabular-nums">{fmtPct(r.win_rate_pct, 1)}</td>
                  <td className="px-2 py-2.5 text-right tabular-nums">{fmtNum(r.profit_factor)}</td>
                  <td className={cn("px-5 py-2.5 text-right", toneCls(r.max_dd_mtm_pct))}>{fmtPct(r.max_dd_mtm_pct)}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Dashboard — every number is read from the Python engine's stored runs and datasets. */
export default function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => quantApi.listDatasets(), enabled: online });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => quantApi.listBacktests(), enabled: online });
  const ds = datasets.data ?? [];
  const rs = runs.data ?? [];
  const latest = rs.find((r) => r.integrity !== "refusée");
  const historical = ds.filter((d) => d.kind === "historical").length;
  const allSynthetic = rs.length > 0 && rs.every((r) => r.data_kind === "synthetic");

  return (
    <Page wide>
      <PageHeader
        icon={LayoutDashboard}
        title="Tableau de bord"
        status="engine"
        description="Vos jeux de données et backtests enregistrés par le moteur Python. Cliquez sur un run pour l'ouvrir en détail."
        actions={
          <Button asChild>
            <Link to="/backtest">
              <Plus className="mr-2 h-4 w-4" />
              Nouveau backtest
            </Link>
          </Button>
        }
      />

      {health.isError && <OfflineNotice />}
      {health.isLoading && <div className="h-32 animate-pulse rounded-xl bg-muted/40" />}

      {online && (
        <>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Tile testId="dash-datasets" icon={Database} label="Jeux de données" value={datasets.data ? ds.length : "…"}
              sub={datasets.data ? `${historical} historique(s) · ${ds.length - historical} synthétique(s)` : undefined} />
            <Tile testId="dash-runs" icon={History} label="Backtests" value={runs.data ? rs.length : "…"}
              sub={latest ? `dernier : ${fmtDateTime(latest.created_at)}` : "aucun pour l'instant"} />
            <Tile testId="dash-last-pnl" icon={Wallet} label="Dernier run · P&L net simulé"
              value={latest ? money(latest, latest.net_pnl) : "—"} tone={latest ? signTone(latest.net_pnl) : "neutral"}
              sub={latest ? `${latest.trades} trades · ${latest.data_kind === "synthetic" ? "données synthétiques" : "historique"}` : undefined} />
            <Tile testId="dash-last-dd" icon={TrendingDown} label="Dernier run · drawdown max"
              value={latest ? fmtPct(latest.max_dd_mtm_pct) : "—"} tone={latest && (latest.max_dd_mtm_pct ?? 0) < 0 ? "down" : "neutral"}
              sub={latest ? "mark-to-market, calculé par le moteur" : undefined} />
          </div>

          {allSynthetic && (
            <Callout tone="warn" title="Tous vos runs utilisent des données synthétiques" testId="dash-synthetic-only">
              Ils vérifient que le logiciel fonctionne, pas qu'une stratégie gagne. Importez un historique réel (export MT5) pour une
              première mesure — voir <Link to="/trading" className="underline">Instruments</Link>.
            </Callout>
          )}

          {rs.length === 0 && runs.data ? (
            <section data-testid="dash-empty" className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border p-10 text-center">
              <FlaskConical className="h-8 w-8 text-muted-foreground" />
              <h2 className="text-lg font-semibold">Aucun backtest enregistré</h2>
              <p className="max-w-md text-sm text-muted-foreground">
                Le tableau de bord se remplit avec les simulations calculées par le moteur. Rien n'est affiché tant qu'il n'y en a pas.
              </p>
              <Button asChild variant="outline">
                <Link to="/backtest">Aller aux backtests <ArrowRight className="ml-2 h-4 w-4" /></Link>
              </Button>
            </section>
          ) : (
            latest && (
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <Section
                  title="Dernier run · capital clôturé"
                  icon={History}
                  description={<>{latest.strategy_key} · run <code>{latest.run_id}</code></>}
                  actions={
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/backtest?run=${encodeURIComponent(latest.run_id)}`}>Ouvrir le détail</Link>
                    </Button>
                  }
                >
                  <LatestEquity run={latest} />
                </Section>
                <Section title="Jeux de données" icon={Database} description="Validés par le moteur, jamais comblés.">
                  <ul className="space-y-3" data-testid="dash-datasets-list">
                    {ds.slice(0, 6).map((d) => (
                      <li key={d.dataset_id} className="space-y-1 border-b border-border/40 pb-3 last:border-0 last:pb-0">
                        <p className="flex items-center justify-between gap-2 text-sm font-medium">
                          <span className="truncate">{d.name}</span>
                          <span className="shrink-0 text-xs text-muted-foreground">{d.symbol} · {d.timeframe}</span>
                        </p>
                        <KindBadge kind={d.kind} />
                        <p className="text-xs text-muted-foreground">
                          {d.rows.toLocaleString("fr-FR")} bougies · {d.start.slice(0, 10)} → {d.end.slice(0, 10)}
                        </p>
                      </li>
                    ))}
                    {ds.length > 6 && <li className="text-xs text-muted-foreground">… et {ds.length - 6} autre(s)</li>}
                  </ul>
                </Section>
              </div>
            )
          )}

          {rs.length > 0 && (
            <Section title="Historique des backtests" icon={History}
              description="Montants dans la devise de chaque run. Un run sans devise connue n'affiche pas de montant.">
              <RunsTable runs={rs} />
            </Section>
          )}
        </>
      )}
    </Page>
  );
}
