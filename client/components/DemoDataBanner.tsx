import { AlertTriangle, Cpu } from "lucide-react";
import { useLocation } from "react-router-dom";

/** Pages whose figures come from the Python quant engine (React → /api/v1 → FastAPI → engine). */
export const ENGINE_BACKED_PATHS = ["/backtest"];

/**
 * Every other page still shows generated demo figures until it is wired to the engine:
 * say so on each of them, and say the opposite (honestly) on engine-backed pages.
 */
export function DemoDataBanner() {
  const { pathname } = useLocation();
  if (ENGINE_BACKED_PATHS.includes(pathname)) {
    return (
      <div
        role="status"
        className="flex items-center justify-center gap-2 bg-blue-50 px-4 py-2 text-center text-sm text-blue-900 dark:bg-blue-950 dark:text-blue-100"
      >
        <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          Résultats calculés par le moteur Python (simulation) — aucun ordre transmis. La nature des données
          (synthétiques ou historiques) est indiquée sur chaque résultat.
        </span>
      </div>
    );
  }
  return (
    <div
      role="alert"
      className="flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-900 dark:bg-amber-950 dark:text-amber-100"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        Page de démonstration : chiffres générés aléatoirement — aucun résultat réel, aucune connexion courtier,
        aucun ordre transmis. Les backtests réels sont dans « Backtests ».
      </span>
    </div>
  );
}
