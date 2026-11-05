"""Alternative risk rules applied to the OBSERVED trades of an external simulation — with an explicit qualification.

A closed robot's deal list says what it DID, not what it WOULD HAVE DONE under other rules. Removing an entry can
change its basket exits, its lot sizes (automatic sizing follows the balance) and whether a stop-out happens.
Every result therefore carries one of three qualifications:

* ``exact``          — recalculation of observed events only (e.g. stopping for good at a flat moment: nothing
                       after it is needed);
* ``approximation``  — conditional: the kept trades are assumed to close exactly as observed;
* ``non_simulable``  — the data needed (prices between deals, the robot's logic) is not in the report.

Never a backtest of the modified robot: that requires re-running the .ex5 in MT5's Strategy Tester.
"""

from __future__ import annotations

from datetime import datetime

RULES = {
    "stop_after_realised_dd": {"label": "Arrêt définitif après un drawdown réalisé ≥ X %", "unit": "%", "default": 20},
    "equity_dd_block": {"label": "Aucune nouvelle entrée si le drawdown d'équité estimé ≥ X %", "unit": "%", "default": 20},
    "max_positions": {"label": "Au plus N positions ouvertes dans le même sens", "unit": "positions", "default": 5},
    "exposure_cap": {"label": "Exposition ouverte plafonnée à X lots", "unit": "lots", "default": 3},
    "lot_scale": {"label": "Tous les lots multipliés par k", "unit": "×", "default": 0.5},
    "daily_loss_stop": {"label": "Plus d'entrée le jour où la perte réalisée atteint X % du solde du matin", "unit": "%", "default": 3},
    "volatility_reduction": {"label": "Réduction de l'exposition en forte volatilité", "unit": "", "default": None},
}
COMMON_CAVEATS = [
    "Les positions conservées sont supposées se clôturer exactement comme dans le rapport (mêmes prix, mêmes instants) ; "
    "un robot à panier recalcule pourtant ses sorties sur l'ensemble de ses positions.",
    "La taille automatique des lots suit le solde : avec un autre historique de solde, le robot aurait choisi d'autres lots.",
    "Le stop-out observé dépend de la marge : avec moins d'exposition il aurait pu ne pas se produire, et le robot aurait "
    "alors gardé ses positions plus longtemps — ce qui n'est pas observable.",
]


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _curve(trades: list[dict], deposit: float, scale: float = 1.0) -> dict:
    bal, peak, dd, dd_pct, low = deposit, deposit, 0.0, 0.0, deposit
    for t in sorted(trades, key=lambda x: (x["exit_seq"], x["entry_seq"])):
        bal += t["net"] * scale
        peak = max(peak, bal)
        low = min(low, bal)
        if peak - bal > dd:
            dd, dd_pct = peak - bal, 100.0 * (peak - bal) / peak if peak > 0 else 0.0
    return {"net": bal - deposit, "final_balance": bal, "max_realised_dd": dd, "max_realised_dd_pct": dd_pct,
            "lowest_balance": low}


def _open_at(kept: list[dict], t: str) -> list[dict]:
    return [k for k in kept if k["entry_time"] <= t < k["exit_time"]]


def _filter_entries(trades: list[dict], deposit: float, cs: float, keep) -> list[dict]:
    """Walk entries in time order; ``keep(trade, state)`` decides. State: open kept trades, realised balance."""
    by_entry = sorted(trades, key=lambda x: (x["entry_seq"], x["exit_seq"]))
    kept: list[dict] = []
    for tr in by_entry:
        t = tr["entry_time"]
        closed = [k for k in kept if k["exit_time"] <= t]
        balance = deposit + sum(k["net"] for k in closed)
        opened = _open_at(kept, t)
        floating = sum((tr["entry_price"] - k["entry_price"]) * (1 if k["side"] == "BUY" else -1) * k["volume"] * cs
                       for k in opened)
        if keep(tr, {"open": opened, "balance": balance, "equity_est": balance + floating, "closed": closed}):
            kept.append(tr)
    return kept


def run(body: dict, rule: str, value: float | None) -> dict:
    if rule not in RULES:
        raise ValueError(f"règle inconnue : {rule}")
    trades = body["trades"]
    deposit = float(body["recomputed"].get("initial_deposit") or 0.0)
    cs = float(body["contract_size"]["value"])
    spec = RULES[rule]
    v = spec["default"] if value is None else float(value)
    base = _curve(trades, deposit)
    out = {"rule": rule, "label": spec["label"], "value": v, "unit": spec["unit"], "baseline": base,
           "caveats": [], "what_to_do": None}

    if rule == "volatility_reduction":
        return {**out, "qualification": "non_simulable", "result": None,
                "explanation": "Le rapport ne contient aucune série de prix entre les opérations : la volatilité au "
                               "moment de chaque entrée est inconnue.",
                "what_to_do": "Exporter de MT5 les bougies M1 de XAUUSD sur la même période (Symboles → Barres → "
                              "Exporter) et les importer ; ou relancer l'EA dans le Strategy Tester avec un réglage "
                              "de lots réduit pour comparer."}
    if v is None or v <= 0:
        raise ValueError("valeur de règle invalide (doit être > 0)")

    if rule == "lot_scale":
        res = _curve(trades, deposit, v)
        so = any(t["close_reason"] == "stop-out" for t in trades)
        return {**out, "qualification": "approximation", "result": {**res, "kept_trades": len(trades),
                                                                     "removed_trades": 0, "stop_out_kept": so},
                "explanation": f"Chaque résultat observé est multiplié par {v:g} : arithmétique exacte sur les mêmes "
                               "exécutions, mais le robot aurait-il pris les mêmes décisions ?",
                "caveats": COMMON_CAVEATS}

    if rule == "stop_after_realised_dd":
        ordered = sorted(trades, key=lambda x: (x["exit_seq"], x["entry_seq"]))
        bal, peak, stop_at = deposit, deposit, None
        for tr in ordered:
            bal += tr["net"]
            peak = max(peak, bal)
            if peak > 0 and 100.0 * (peak - bal) / peak >= v:
                if not _open_at([k for k in trades if k["entry_time"] <= tr["exit_time"]], tr["exit_time"]):
                    stop_at = tr["exit_time"]
                    break
        kept = [t for t in trades if stop_at is None or t["entry_time"] <= stop_at]
        res = _curve(kept, deposit)
        triggered = stop_at is not None and len(kept) < len(trades)
        return {**out, "qualification": "exact", "result": {**res, "kept_trades": len(kept),
                                                            "removed_trades": len(trades) - len(kept),
                                                            "triggered_at": stop_at,
                                                            "stop_out_kept": any(t["close_reason"] == "stop-out" for t in kept)},
                "explanation": ("Arrêt définitif au premier instant SANS position ouverte où le drawdown réalisé "
                                f"atteint {v:g} % : seuls des événements observés sont utilisés."
                                + ("" if triggered else " Le seuil n'est atteint sur du solde RÉALISÉ qu'APRÈS "
                                   "l'effondrement (ou jamais) : les pertes étaient latentes, invisibles pour une règle "
                                   "fondée sur le solde.")),
                "caveats": [] if triggered else ["Une règle fondée sur le solde réalisé ne voit pas les pertes "
                                                 "latentes d'une grille : c'est précisément le mécanisme de l'effondrement."]}

    if rule == "max_positions":
        n = int(v)
        kept = _filter_entries(trades, deposit, cs, lambda tr, st: sum(1 for k in st["open"] if k["side"] == tr["side"]) < n)
    elif rule == "exposure_cap":
        kept = _filter_entries(trades, deposit, cs, lambda tr, st: sum(k["volume"] for k in st["open"]) + tr["volume"] <= v + 1e-9)
    elif rule == "equity_dd_block":
        peak = {"eq": deposit}

        def keep(tr, st):
            peak["eq"] = max(peak["eq"], st["equity_est"], st["balance"])
            return 100.0 * (peak["eq"] - st["equity_est"]) / peak["eq"] < v if peak["eq"] > 0 else True
        kept = _filter_entries(trades, deposit, cs, keep)
    else:  # daily_loss_stop
        def keep(tr, st):
            day = tr["entry_time"][:10]
            before = [k for k in st["closed"] if k["exit_time"][:10] < day]
            today = [k for k in st["closed"] if k["exit_time"][:10] == day]
            morning = deposit + sum(k["net"] for k in before)
            loss = -sum(k["net"] for k in today)
            return not (morning > 0 and loss >= morning * v / 100.0)
        kept = _filter_entries(trades, deposit, cs, keep)

    res = _curve(kept, deposit)
    return {**out, "qualification": "approximation",
            "result": {**res, "kept_trades": len(kept), "removed_trades": len(trades) - len(kept),
                       "stop_out_kept": any(t["close_reason"] == "stop-out" for t in kept)},
            "explanation": "Les entrées qui auraient violé la règle sont retirées avec leur clôture ; les autres sont "
                           "conservées telles qu'observées. Approximation conditionnelle, pas un backtest du robot modifié.",
            "caveats": COMMON_CAVEATS,
            "what_to_do": "Pour un résultat fiable : relancer l'EA dans le Strategy Tester de MT5 avec un réglage "
                          "équivalent (s'il existe dans ses paramètres) et importer le nouveau rapport pour comparaison."}


def catalogue() -> list[dict]:
    return [{"rule": k, **v} for k, v in RULES.items()]
