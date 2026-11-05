/**
 * Display-only formatting of values returned by the quant API.
 * `null` / non-finite = "indisponible": a missing metric is never shown as 0.
 */
export const UNAVAILABLE = "indisponible";

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function fmtMoney(v: number | null | undefined, currency = "USD", digits = 2): string {
  if (!isNum(v)) return UNAVAILABLE;
  const s = Math.abs(v).toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `${v < 0 ? "−" : ""}${s} ${currency}`;
}

export function fmtSignedMoney(v: number | null | undefined, currency = "USD"): string {
  if (!isNum(v)) return UNAVAILABLE;
  return v > 0 ? `+${fmtMoney(v, currency)}` : fmtMoney(v, currency);
}

export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (!isNum(v)) return UNAVAILABLE;
  return `${v.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits })} %`;
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (!isNum(v)) return UNAVAILABLE;
  return v.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return UNAVAILABLE;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return UNAVAILABLE;
  return `${d.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

/** Compact "MM-DD HH:MM" (UTC) for dense tables whose header states the time zone. */
export function fmtShortDateTime(iso: string | null | undefined): string {
  if (!iso) return UNAVAILABLE;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return UNAVAILABLE;
  return d.toISOString().slice(5, 16).replace("T", " ");
}

/** Plain engine value in French notation (0.25 → "0,25"), without rounding it away. */
export function fmtValue(v: number | null | undefined): string {
  if (!isNum(v)) return UNAVAILABLE;
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 6 });
}

export const DATA_KIND_LABELS: Record<string, string> = {
  synthetic: "Synthétique — fausses cotations",
  historical: "Historique (déclaré par l'utilisateur, non vérifié)",
  demo_account: "Compte démo",
};
