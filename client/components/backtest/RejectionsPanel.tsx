import { useQuery } from "@tanstack/react-query";
import type { Metrics } from "@shared/quant-api";
import { quantApi } from "@/lib/quantApi";

export function RejectionsPanel({ m }: { m: Metrics }) {
  const labels = useQuery({ queryKey: ["reasons"], queryFn: () => quantApi.rejectionLabels() });
  const rows = Object.entries(m.rejection_reasons).sort((a, b) => b[1] - a[1]);
  const top = rows[0]?.[1] ?? 1;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3 text-center">
        {[["Signaux", m.signals], ["Entrés", m.signals_entered], ["Refusés", m.signals_rejected]].map(([l, v]) => (
          <div key={String(l)} className="rounded-lg border border-border/60 bg-card/80 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{l}</p>
            <p className="text-xl font-semibold tabular-nums">{v}</p>
          </div>
        ))}
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Aucun signal refusé.</p>
      ) : (
        <ul className="space-y-2" data-testid="rejections">
          {rows.map(([code, n]) => (
            <li key={code} className="space-y-1">
              <div className="flex justify-between gap-4 text-sm">
                <span>{labels.data?.[code] ?? code}</span>
                <span className="tabular-nums text-muted-foreground">{n}</span>
              </div>
              {/* bar width = count relative to the largest count (display scaling only) */}
              <div className="h-1.5 rounded-full bg-muted/50">
                <div className="h-1.5 rounded-full bg-amber-500/80" style={{ width: `${Math.max(2, (100 * n) / top)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted-foreground">
        Un signal peut cumuler plusieurs raisons. Les refus du Risk Guardian sont « fail-closed » : en cas de doute,
        aucune position n'est ouverte.
      </p>
    </div>
  );
}
