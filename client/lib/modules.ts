import {
  BookOpenCheck,
  Bot,
  CandlestickChart,
  FlaskConical,
  Home,
  LayoutDashboard,
  Lock,
  Microscope,
  Settings,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

/**
 * What each page really is — shown in the navigation so nobody mistakes a reference page for a live feature.
 *  - engine:    figures come from the Python engine (React → /api/v1 → FastAPI)
 *  - reference: documentation / hypotheses / specifications, no performance figure
 *  - locked:    deliberately disabled by design (no execution, no broker)
 */
export type ModuleStatus = "engine" | "reference" | "locked";

export interface NavItem {
  href: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  status: ModuleStatus;
}

export const STATUS_LABELS: Record<ModuleStatus, string> = {
  engine: "Moteur",
  reference: "Référence",
  locked: "Verrouillé",
};

export const NAV_GROUPS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: "Laboratoire",
    items: [
      { href: "/", label: "Accueil", hint: "Ce que fait le logiciel", icon: Home, status: "reference" },
      { href: "/dashboard", label: "Tableau de bord", hint: "Runs enregistrés", icon: LayoutDashboard, status: "engine" },
      { href: "/backtest", label: "Backtests", hint: "Simuler une stratégie", icon: FlaskConical, status: "engine" },
      { href: "/research", label: "Validation", hint: "Avantage hors échantillon", icon: Microscope, status: "engine" },
      { href: "/bot-analysis", label: "Bot Analysis", hint: "Robots MT5 externes : risques, effondrement", icon: Bot, status: "engine" },
      { href: "/ea-audit", label: "Audit d'EA", hint: "Grille, martingale, risque de ruine", icon: ShieldAlert, status: "engine" },
      { href: "/optimizer", label: "Stratégies", hint: "Règles et paramètres", icon: BookOpenCheck, status: "engine" },
    ],
  },
  {
    title: "Marché & garde-fous",
    items: [
      { href: "/trading", label: "Instruments", hint: "Contrats, coûts, MT5", icon: CandlestickChart, status: "reference" },
      { href: "/automation", label: "Exécution", hint: "Désactivée", icon: Lock, status: "locked" },
    ],
  },
  {
    title: "Système",
    items: [{ href: "/settings", label: "Paramètres", hint: "Moteur et risque", icon: Settings, status: "engine" }],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);
