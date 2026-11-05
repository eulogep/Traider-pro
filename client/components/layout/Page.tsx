import type { ReactNode } from "react";
import { AlertTriangle, Info, Lock, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ModuleStatus } from "@/lib/modules";
import { cn } from "@/lib/utils";
import { StatusChip } from "./AppShell";

/** Page frame shared by every screen: same gutters, same maximum width. */
export function Page({ children, wide = false, className }: { children: ReactNode; wide?: boolean; className?: string }) {
  return (
    <div className={cn("mx-auto w-full space-y-6 px-4 py-6 md:px-8 md:py-8", wide ? "max-w-[1520px]" : "max-w-6xl", className)}>
      {children}
    </div>
  );
}

export function PageHeader(props: {
  icon: LucideIcon;
  title: string;
  description: ReactNode;
  status?: ModuleStatus;
  actions?: ReactNode;
}) {
  const Icon = props.icon;
  return (
    <header className="flex flex-col gap-4 border-b border-border/50 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{props.title}</h1>
            {props.status && <StatusChip status={props.status} />}
          </div>
          <p className="max-w-3xl text-sm text-muted-foreground">{props.description}</p>
        </div>
      </div>
      {props.actions && <div className="flex flex-wrap items-center gap-2">{props.actions}</div>}
    </header>
  );
}

export function Section(props: {
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
}) {
  const Icon = props.icon;
  return (
    <section data-testid={props.testId} className={cn("rounded-xl border border-border/60 bg-card/70 shadow-sm", props.className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/50 px-5 py-4">
        <div className="space-y-0.5">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
            {props.title}
          </h2>
          {props.description && <p className="text-xs text-muted-foreground">{props.description}</p>}
        </div>
        {props.actions}
      </div>
      <div className="p-5">{props.children}</div>
    </section>
  );
}

type Tone = "info" | "warn" | "danger" | "safe" | "locked";
const CALLOUT: Record<Tone, { cls: string; icon: LucideIcon }> = {
  info: { cls: "border-blue-500/30 bg-blue-500/10 text-blue-100", icon: Info },
  warn: { cls: "border-amber-500/30 bg-amber-500/10 text-amber-100", icon: AlertTriangle },
  danger: { cls: "border-red-500/40 bg-red-500/10 text-red-100", icon: AlertTriangle },
  safe: { cls: "border-primary/30 bg-primary/10 text-emerald-100", icon: ShieldCheck },
  locked: { cls: "border-amber-500/30 bg-amber-500/5 text-amber-100", icon: Lock },
};

export function Callout({ tone = "info", title, children, testId }: { tone?: Tone; title?: string; children: ReactNode; testId?: string }) {
  const { cls, icon: Icon } = CALLOUT[tone];
  return (
    <div role={tone === "danger" ? "alert" : "note"} data-testid={testId} className={cn("flex items-start gap-3 rounded-lg border px-4 py-3 text-sm", cls)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="space-y-1">
        {title && <p className="font-semibold">{title}</p>}
        <div className="text-[13px] leading-relaxed opacity-90">{children}</div>
      </div>
    </div>
  );
}

/** Label / value grid for read-only facts (specification, configuration…). */
export function Facts({ items, cols = 2 }: { items: Array<[string, ReactNode]>; cols?: 1 | 2 | 3 }) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-3 text-sm", cols === 2 && "sm:grid-cols-2", cols === 3 && "sm:grid-cols-2 lg:grid-cols-3")}>
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0 border-b border-border/40 pb-2">
          <dt className="text-xs text-muted-foreground">{k}</dt>
          <dd className="mt-0.5 break-words font-medium tabular-nums">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Tile(props: { label: string; value: ReactNode; sub?: ReactNode; icon?: LucideIcon; testId?: string; tone?: "up" | "down" | "neutral" }) {
  const Icon = props.icon;
  return (
    <div data-testid={props.testId} className="rounded-xl border border-border/60 bg-card/70 p-4 shadow-sm">
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {props.label}
      </p>
      <p
        className={cn(
          "mt-1 text-2xl font-semibold tabular-nums",
          props.tone === "up" && "text-trading-green-500",
          props.tone === "down" && "text-trading-red-500",
        )}
      >
        {props.value}
      </p>
      {props.sub && <p className="mt-0.5 truncate text-xs text-muted-foreground">{props.sub}</p>}
    </div>
  );
}

export function OfflineNotice() {
  return (
    <Callout tone="danger" title="API Python injoignable" testId="api-offline-notice">
      Aucune donnée du moteur ne peut être affichée et aucun chiffre de remplacement n'est montré. Démarrez-la dans un second
      terminal : <code className="rounded bg-black/30 px-1.5 py-0.5">pnpm quant:api</code> (écoute 127.0.0.1:8765).
    </Callout>
  );
}
