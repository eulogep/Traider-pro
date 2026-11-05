import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Metrics, Trade } from "@shared/quant-api";
import { quantApi } from "@/lib/quantApi";
import { fmtDateTime, fmtMoney, fmtNum, fmtPct } from "@/lib/format";

const GREEN = "#22c55e";
const RED = "#ef4444";
const AXIS = { stroke: "hsl(var(--muted-foreground))", fontSize: 11 };
const TIP = {
  contentStyle: { background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "hsl(var(--muted-foreground))" },
};

function Panel({ title, sub, children, h = "h-64" }: { title: string; sub?: string; children: React.ReactNode; h?: string }) {
  return (
    <section className="rounded-xl border border-border/60 bg-card/80 p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
      <div className={h}>{children}</div>
    </section>
  );
}

export function PerformanceCharts({ runId, m, currency, trades }: { runId: string; m: Metrics; currency: string; trades: Trade[] }) {
  const equity = useQuery({ queryKey: ["equity", runId], queryFn: () => quantApi.getEquity(runId) });
  const pts = equity.data?.points ?? [];
  const day = (v: string) => v.slice(5, 10).replace("-", "/");
  return (
    <div className="space-y-4">
      <Panel title="Courbe de capital"
        sub={equity.data ? `${pts.length} points affichés sur ${equity.data.total_points} (points extrêmes conservés)` : undefined} h="h-72">
        {equity.isLoading && <div className="h-full animate-pulse rounded-lg bg-muted/40" />}
        {equity.isError && <p className="text-sm text-red-500">{(equity.error as Error).message}</p>}
        {equity.data && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pts} margin={{ left: 8, right: 8, top: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
              <XAxis dataKey="timestamp" tickFormatter={day} minTickGap={48} {...AXIS} />
              <YAxis domain={["auto", "auto"]} width={72} tickFormatter={(v: number) => fmtNum(v, 0)} {...AXIS} />
              <Tooltip {...TIP} labelFormatter={(v) => fmtDateTime(String(v))}
                formatter={(v: number, n: string) => [fmtMoney(v, currency), n]} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine y={m.initial_equity} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="mtm_equity" name="Mark-to-market" stroke="#64748b" dot={false} strokeWidth={1}
                isAnimationActive={false} />
              <Line type="stepAfter" dataKey="closed_equity" name="Capital clôturé" stroke={GREEN} dot={false} strokeWidth={2}
                isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Drawdown (mark-to-market)" sub={`max ${fmtPct(m.max_dd_mtm_pct)} · calculé par le moteur`} h="h-52">
          {equity.data && (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={pts} margin={{ left: 8, right: 8, top: 4 }}>
                <defs>
                  <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={RED} stopOpacity={0.05} />
                    <stop offset="100%" stopColor={RED} stopOpacity={0.45} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                <XAxis dataKey="timestamp" tickFormatter={day} minTickGap={48} {...AXIS} />
                <YAxis width={56} tickFormatter={(v: number) => `${fmtNum(v, 1)} %`} {...AXIS} />
                <Tooltip {...TIP} labelFormatter={(v) => fmtDateTime(String(v))}
                  formatter={(v: number) => [fmtPct(v), "Drawdown"]} />
                <Area type="monotone" dataKey="drawdown_mtm_pct" stroke={RED} fill="url(#ddFill)" strokeWidth={1.5}
                  isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title="Résultat de chaque trade (multiples de R)" sub="1 R = risque prévu à l'entrée" h="h-52">
          {trades.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune transaction.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trades} margin={{ left: 8, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                <XAxis dataKey="trade_id" {...AXIS} />
                <YAxis width={40} {...AXIS} />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
                <Tooltip {...TIP} labelFormatter={(v) => `Trade n° ${v}`}
                  formatter={(v: number) => [`${fmtNum(v)} R`, "Résultat net"]} />
                <Bar dataKey="r_multiple" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                  {trades.map((t) => <Cell key={t.trade_id} fill={(t.r_multiple ?? 0) > 0 ? GREEN : RED} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>
    </div>
  );
}
