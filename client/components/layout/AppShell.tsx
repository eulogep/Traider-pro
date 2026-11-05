import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Cpu, Eye, Menu, ShieldCheck, TrendingUp, WifiOff, X } from "lucide-react";
import { SHOWCASE_MODE, quantApi } from "@/lib/quantApi";
import { NAV_GROUPS, STATUS_LABELS, type ModuleStatus, type NavItem } from "@/lib/modules";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<ModuleStatus, string> = {
  engine: "border-primary/30 bg-primary/10 text-primary",
  reference: "border-border bg-muted/50 text-muted-foreground",
  locked: "border-amber-500/30 bg-amber-500/10 text-amber-400",
};

/** Shown only in the static showcase build: says what the visitor is looking at, and when it was computed. */
export function ShowcaseBanner() {
  const m = useQuery({
    queryKey: ["showcase-manifest"],
    queryFn: async () => (await (await fetch("/showcase/manifest.json")).json()) as { generated_at: string; software_version: string; engine_version: string },
    enabled: SHOWCASE_MODE,
    staleTime: Infinity,
  });
  if (!SHOWCASE_MODE) return null;
  return (
    <div data-testid="showcase-banner" role="note"
      className="flex items-start gap-2 border-b border-sky-500/30 bg-sky-500/10 px-4 py-2 text-xs text-sky-200">
      <Eye className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <strong>Vitrine en lecture seule.</strong> Résultats calculés par le moteur Python
        {m.data ? ` v${m.data.software_version} le ${new Date(m.data.generated_at).toLocaleDateString("fr-FR")}` : ""}, puis figés :
        une démo synthétique, et l'analyse d'un vrai rapport MT5 (Gold Grid V3.70). Importer ou lancer un calcul est désactivé ;
        aucune connexion à un courtier, aucun ordre.
      </span>
    </div>
  );
}

export function StatusChip({ status, className }: { status: ModuleStatus; className?: string }) {
  return (
    <span className={cn("rounded px-1.5 py-px text-[10px] font-medium uppercase tracking-wide border", STATUS_STYLE[status], className)}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-3 px-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-emerald-700 shadow-sm shadow-primary/30">
        <TrendingUp className="h-5 w-5 text-primary-foreground" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight">AI Trader Optimizer</p>
        <p className="text-[11px] text-muted-foreground">Traider Pro · laboratoire</p>
      </div>
    </Link>
  );
}

function NavLink({ item, active, onClick }: { item: NavItem; active: boolean; onClick?: () => void }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      data-testid={`nav-${item.href === "/" ? "home" : item.href.slice(1)}`}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
        active ? "bg-primary/10 text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
    >
      <Icon className={cn("h-4 w-4 shrink-0", active ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{item.label}</span>
        <span className="block truncate text-[11px] text-muted-foreground/80">{item.hint}</span>
      </span>
      {item.status !== "reference" && <StatusChip status={item.status} />}
    </Link>
  );
}

/** Engine status from the real health endpoint: the only "live" indicator of the app. */
function EngineStatus() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false, refetchInterval: 30_000 });
  const ok = health.isSuccess;
  return (
    <div data-testid="shell-engine-status" className="rounded-lg border border-border/60 bg-background/40 p-3 text-xs">
      <p className="flex items-center gap-2 font-medium">
        <span className={cn("h-2 w-2 rounded-full", ok ? "bg-primary" : health.isLoading ? "bg-muted-foreground" : "bg-red-500")} />
        {SHOWCASE_MODE ? "Résultats figés du moteur Python" : health.isLoading ? "Connexion au moteur…" : ok ? "Moteur Python en ligne" : "Moteur Python hors ligne"}
      </p>
      {ok ? (
        <p className="mt-1 flex items-center gap-1.5 text-muted-foreground">
          <Cpu className="h-3 w-3" />
          {health.data.software_version} · {health.data.order_routes} route d'ordre
        </p>
      ) : (
        !health.isLoading && (
          <p className="mt-1 flex items-center gap-1.5 text-muted-foreground">
            <WifiOff className="h-3 w-3" />
            <code>pnpm quant:api</code>
          </p>
        )
      )}
    </div>
  );
}

function SafetyNote() {
  return (
    <p className="flex items-start gap-2 px-2 text-[11px] leading-snug text-muted-foreground">
      <ShieldCheck className="mt-px h-3.5 w-3.5 shrink-0 text-primary" />
      Simulation uniquement : aucun compte réel, aucun identifiant, aucun ordre transmis.
    </p>
  );
}

function NavContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav aria-label="Navigation principale" className="space-y-5">
      {NAV_GROUPS.map((g) => (
        <div key={g.title} className="space-y-1">
          <p className="px-2.5 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">{g.title}</p>
          {g.items.map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} onClick={onNavigate} />
          ))}
        </div>
      ))}
    </nav>
  );
}

/**
 * Application frame: fixed sidebar on large screens, collapsible top bar on small ones.
 * It shows what every page IS (engine / reference / locked) and the real engine status.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  // block bodies: recent browsers make scrollTo() return a Promise, which React would take for a cleanup function
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-background">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border/60 bg-card/40 backdrop-blur lg:flex">
        <div className="flex h-16 items-center border-b border-border/60 px-3">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-5">
          <NavContent pathname={pathname} />
        </div>
        <div className="space-y-3 border-t border-border/60 p-3">
          <EngineStatus />
          <SafetyNote />
        </div>
      </aside>

      {/* mobile top bar */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/60 bg-card/80 px-3 backdrop-blur lg:hidden">
        <Brand />
        <button
          type="button"
          aria-label={open ? "Fermer le menu" : "Ouvrir le menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>
      {open && (
        <div className="fixed inset-x-0 bottom-0 top-14 z-30 space-y-5 overflow-y-auto border-t border-border/60 bg-background p-4 lg:hidden">
          <NavContent pathname={pathname} onNavigate={() => setOpen(false)} />
          <EngineStatus />
          <SafetyNote />
        </div>
      )}

      <div className="lg:pl-64">
        <ShowcaseBanner />
        {children}
      </div>
    </div>
  );
}
