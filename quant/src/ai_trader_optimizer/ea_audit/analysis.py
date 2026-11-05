"""Behavioural audit of an Expert Advisor from its MT5 deal list: grid / averaging-down / martingale
signatures and the price move that would wipe the account at its peak exposure.

Why: grid and martingale EAs show many small wins and a smooth balance curve until one trend erases the
account (the balance curve hides the open losses). The deal list is enough to see the MECHANISM — stacked
positions, entries added against open losses, lot sizes that grow — even when the .ex5 source is closed.

Every rule below is a fixed, declared heuristic (``THRESHOLDS``), chosen from the definition of the
mechanism, not fitted to any report. A clean result is NOT a proof of safety: a report covers one period and
one parameter set; floating drawdown is only partially visible from deals.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, replace

from .report import Deal, ParsedReport

ANALYSIS_VERSION = "ea-audit/1"
THRESHOLDS = {
    "min_trading_deals": 20,  # below: insufficient
    "stacking_positions": 3,  # ≥ 3 positions open in the same direction at once
    "averaging_adds": 3,  # ≥ 3 entries added while the open stack was losing…
    "averaging_share": 0.10,  # …and ≥ 10 % of all entries
    "escalation_ratio": 1.2,  # an add ≥ 1.2 × the previous entry of the same stack
    "escalation_min": 3,  # ≥ 3 such adds and a median add ratio ≥ escalation_ratio
    "after_loss_ratio": 1.2,  # first lot after a losing basket ≥ 1.2 × the previous first lot (median)…
    "after_loss_min": 3,  # …over ≥ 3 losing baskets, and > 1.1 × the same ratio after winning baskets
    "asymmetry_win_rate": 0.70,  # ≥ 70 % winning baskets…
    "asymmetry_loss_multiple": 10.0,  # …and worst basket loss ≥ 10 × median basket win
}
EPS = 1e-9
# MT5 writes the reason of broker-forced closes in the deal comment: "so 12.43%" (stop-out at that margin level)
# and "end of test" (Strategy Tester closing what is still open). Documented MT5 conventions, seen in a real report.
STOP_OUT = re.compile(r"^\s*so\b", re.I)
END_OF_TEST = re.compile(r"end\s+of\s+test", re.I)


@dataclass
class _Lot:
    side: int  # +1 long, -1 short
    volume: float
    price: float


@dataclass
class _Stack:
    symbol: str
    side: int
    opened: str
    first_price: float
    first_volume: float
    entries: int = 0
    max_positions: int = 0
    max_volume: float = 0.0
    worst_add_distance: float = 0.0  # how far price had gone AGAINST the first entry when the EA still added
    net: float = 0.0
    closed: str | None = None
    adds_against: int = 0
    lot_ratios: list[float] = field(default_factory=list)


def _fmt(t) -> str:
    return t.isoformat()


def _median(x: list[float]) -> float | None:
    return float(statistics.median(x)) if x else None


def analyse(report: ParsedReport, contract_size: float, contract_note: str) -> dict:
    if not (contract_size > 0 and math.isfinite(contract_size)):
        raise ValueError("taille de contrat invalide")
    deals = report.deals
    trading = [d for d in deals if d.kind in ("buy", "sell")]
    balance_ops = [d for d in deals if d.kind == "balance"]
    symbols = sorted({d.symbol for d in trading if d.symbol})

    open_lots: dict[str, list[_Lot]] = defaultdict(list)
    stacks: dict[tuple[str, int], _Stack] = {}
    done: list[_Stack] = []
    balance = 0.0  # running balance: deposits / withdrawals + net result of every deal, in file order
    entries = adds = adds_against = 0
    unmatched_volume = 0.0
    inout_deals = 0
    max_same_dir, max_gross, peak = 0, 0.0, None
    escalations: list[float] = []
    out_results: list[float] = []

    def stack_add(sym: str, side: int, d: Deal) -> None:
        nonlocal entries, adds, adds_against, max_same_dir
        entries += 1
        lots = [lot for lot in open_lots[sym] if lot.side == side]
        st = stacks.get((sym, side))
        if st is None or not lots:
            st = _Stack(symbol=sym, side=side, opened=_fmt(d.time), first_price=d.price, first_volume=d.volume)
            stacks[(sym, side)] = st
        else:
            adds += 1
            vol = sum(lot.volume for lot in lots)
            avg = sum(lot.volume * lot.price for lot in lots) / vol
            if (d.price - avg) * side < -EPS:  # adding while the open stack is losing (averaging down)
                adds_against += 1
                st.adds_against += 1
            prev = lots[-1].volume
            ratio = d.volume / prev if prev > 0 else math.nan
            if math.isfinite(ratio):
                st.lot_ratios.append(ratio)
                escalations.append(ratio)
            st.worst_add_distance = max(st.worst_add_distance, (st.first_price - d.price) * side)
        st.entries += 1
        open_lots[sym].append(_Lot(side, d.volume, d.price))
        n_same = sum(1 for lot in open_lots[sym] if lot.side == side)
        st.max_positions = max(st.max_positions, n_same)
        st.max_volume = max(st.max_volume, sum(lot.volume for lot in open_lots[sym] if lot.side == side))
        max_same_dir = max(max_same_dir, n_same)

    def close(sym: str, side: int, volume: float) -> float:
        """FIFO close of ``volume`` lots of ``side``; returns the unmatched part (report started mid-history)."""
        left = volume
        for lot in list(open_lots[sym]):
            if lot.side != side or left <= EPS:
                continue
            take = min(lot.volume, left)
            lot.volume -= take
            left -= take
            if lot.volume <= EPS:
                open_lots[sym].remove(lot)
        return max(0.0, left)

    def finish_stack_if_flat(sym: str, side: int, when) -> None:
        st = stacks.get((sym, side))
        if st is not None and not any(lot.side == side for lot in open_lots[sym]):
            st.closed = _fmt(when)
            done.append(st)
            del stacks[(sym, side)]

    for d in deals:
        if d.kind == "balance":
            balance += d.net
            continue
        if d.kind != "buy" and d.kind != "sell":
            continue
        side = 1 if d.kind == "buy" else -1
        sym = d.symbol
        if d.direction == "in":
            stack_add(sym, side, d)
        elif d.direction in ("out", "inout"):
            if d.direction == "inout":
                inout_deals += 1
            target = -side  # a SELL "out" closes longs, a BUY "out" closes shorts
            open_target = sum(lot.volume for lot in open_lots[sym] if lot.side == target)
            closing = min(open_target, d.volume) if d.direction == "inout" else d.volume
            left = close(sym, target, closing)
            if d.direction == "out":
                unmatched_volume += left
            st = stacks.get((sym, target))
            if st is not None:
                st.net += d.net
            out_results.append(d.net)
            finish_stack_if_flat(sym, target, d.time)
            if d.direction == "inout" and d.volume - closing > EPS:
                stack_add(sym, side, replace(d, volume=d.volume - closing))
        balance += d.net
        gross = sum(lot.volume for lots in open_lots.values() for lot in lots)
        max_gross = max(max_gross, gross)
        net_lots = sum(lot.side * lot.volume for lot in open_lots[sym])
        if peak is None or abs(net_lots) > abs(peak["net_lots"]) + EPS:
            floating = sum((d.price - lot.price) * lot.side * lot.volume * contract_size for lot in open_lots[sym])
            peak = {"time": _fmt(d.time), "symbol": sym, "net_lots": net_lots, "price": d.price,
                    "balance": balance, "floating_at_price": floating,
                    "positions": len(open_lots[sym])}

    open_at_end = [st for st in stacks.values()]
    baskets = [st.net for st in done]
    wins = [x for x in baskets if x > 0]
    losses = [x for x in baskets if x < 0]

    # lot size of each new basket relative to the previous basket's first lot, split by the previous outcome
    after_loss, after_win = [], []
    by_symbol: dict[str, list[_Stack]] = defaultdict(list)
    for st in done:
        by_symbol[st.symbol].append(st)
    for seq in by_symbol.values():
        seq.sort(key=lambda s: s.opened)
        for prev, cur in zip(seq, seq[1:], strict=False):
            if prev.first_volume > 0:
                (after_loss if prev.net < 0 else after_win).append(cur.first_volume / prev.first_volume)

    T = THRESHOLDS
    so = [d for d in trading if d.direction in ("out", "inout") and STOP_OUT.search(d.comment or "")]
    eot = [d for d in trading if d.direction in ("out", "inout") and END_OF_TEST.search(d.comment or "")]
    flags: list[dict] = []
    n_trading = len(trading)
    esc_big = [r for r in escalations if r >= T["escalation_ratio"]]
    if max_same_dir >= T["stacking_positions"]:
        flags.append({"code": "STACKING", "label": "Positions empilées dans le même sens",
                      "detail": f"jusqu'à {max_same_dir} positions ouvertes en même temps dans le même sens"})
    if adds_against >= T["averaging_adds"] and entries and adds_against / entries >= T["averaging_share"]:
        flags.append({"code": "AVERAGING_DOWN", "label": "Renforcement contre la perte (grille)",
                      "detail": f"{adds_against} entrées sur {entries} ajoutées alors que les positions ouvertes "
                                "dans le même sens étaient perdantes"})
    if len(esc_big) >= T["escalation_min"] and (_median(escalations) or 0) >= T["escalation_ratio"]:
        flags.append({"code": "LOT_ESCALATION", "label": "Lots croissants dans une même série (martingale)",
                      "detail": f"{len(esc_big)} ajouts ≥ {T['escalation_ratio']} × le lot précédent ; "
                                f"multiplicateur médian {_median(escalations):.2f}"})
    mal, maw = _median(after_loss), _median(after_win)
    if (len(after_loss) >= T["after_loss_min"] and mal is not None and mal >= T["after_loss_ratio"]
            and (maw is None or mal > 1.1 * maw)):
        flags.append({"code": "MARTINGALE_AFTER_LOSS", "label": "Lot augmenté après une perte (martingale)",
                      "detail": f"premier lot après une série perdante : × {mal:.2f} (médiane, {len(after_loss)} cas)"
                                + (f", contre × {maw:.2f} après une série gagnante" if maw is not None else "")})
    if baskets and wins and losses:
        wr = len(wins) / len(baskets)
        mw = statistics.median(wins)
        if wr >= T["asymmetry_win_rate"] and abs(min(losses)) >= T["asymmetry_loss_multiple"] * mw:
            flags.append({"code": "ASYMMETRIC", "label": "Beaucoup de petits gains, quelques pertes énormes",
                          "detail": f"{wr:.0%} de séries gagnantes ; pire perte = {abs(min(losses)) / mw:.0f} × le "
                                    "gain médian"})
    if open_at_end:
        flags.append({"code": "OPEN_AT_END", "label": "Positions encore ouvertes à la fin du rapport",
                      "detail": f"{sum(s.max_positions for s in open_at_end)} position(s) non clôturée(s) : leur perte "
                                "latente n'est pas dans le solde final"})

    vols_so = sum(d.volume for d in so)
    if so:
        flags.insert(0, {"code": "STOP_OUT", "label": "Compte liquidé par le courtier (stop-out)",
                         "detail": f"{len(so)} position(s) ({vols_so:.2f} lot) fermée(s) de force le "
                                   f"{_fmt(so[0].time)[:16].replace('T', ' ')} — commentaire MT5 « {so[0].comment} » ; "
                                   f"perte de ces clôtures : {sum(d.net for d in so):,.2f}".replace(",", " ")})
    if eot:
        flags.append({"code": "END_OF_TEST_CLOSE", "label": "Positions fermées par la fin du test",
                      "detail": f"{len(eot)} position(s) clôturée(s) par le testeur et non par l'EA ; résultat "
                                f"{sum(d.net for d in eot):,.2f}".replace(",", " ")})
    codes = {f["code"] for f in flags}
    if so:
        verdict = {"code": "STOP_OUT", "title": "Compte liquidé pendant le test",
                   "text": "Le courtier a fermé les positions de force faute de marge : le capital a été presque entièrement "
                           "perdu sur cette période. Les gains réguliers qui précèdent ne compensent pas ce risque."}
    elif n_trading < T["min_trading_deals"]:
        verdict = {"code": "INSUFFICIENT", "title": "Rapport trop court pour conclure",
                   "text": f"{n_trading} opérations de trading (minimum {T['min_trading_deals']})."}
    elif codes & {"LOT_ESCALATION", "MARTINGALE_AFTER_LOSS"}:
        verdict = {"code": "MARTINGALE", "title": "Martingale détectée — risque de ruine",
                   "text": "L'EA augmente la taille de ses lots pour se refaire. Une tendance assez longue contre lui "
                           "peut vider le compte, quel que soit l'historique de gains. Le Risk Guardian de ce logiciel "
                           "refuse ce mode de gestion."}
    elif {"AVERAGING_DOWN", "STACKING"} <= codes:
        verdict = {"code": "GRID", "title": "Grille détectée — pertes non bornées par trade",
                   "text": "L'EA ajoute des positions quand le prix va contre lui. Le risque réel est celui de la "
                           "série entière au pire moment, pas celui d'un trade."}
    elif codes - {"OPEN_AT_END"}:
        verdict = {"code": "RISK_SIGNS", "title": "Signaux de risque à examiner",
                   "text": "Pas de grille ni de martingale caractérisée, mais des comportements à vérifier."}
    else:
        verdict = {"code": "NO_SIGNATURE", "title": "Aucune signature de grille ou de martingale détectée",
                   "text": "Sur cette période et ces réglages seulement. Ce n'est pas une preuve de sécurité ni de "
                           "rentabilité."}

    stress = None
    if peak is not None and abs(peak["net_lots"]) > EPS:
        per_unit = abs(peak["net_lots"]) * contract_size  # account currency lost per 1.0 price unit against
        equity = peak["balance"] + peak["floating_at_price"]
        stress = {
            **peak,
            "equity_estimate": equity,
            "loss_per_price_unit": per_unit,
            "adverse_move_to_lose_half": (equity - 0.5 * peak["balance"]) / per_unit,
            "adverse_move_to_zero": equity / per_unit,
            "direction": "baisse" if peak["net_lots"] > 0 else "hausse",
            "note": ("Mouvement de prix (en unités de cotation, ex. dollars par once pour XAUUSD) qui, depuis le prix "
                     "de la dernière opération au moment de l'exposition maximale, ramènerait l'équité estimée à la "
                     "moitié du solde puis à zéro. Spread, swap et stop-out du courtier ignorés : en réalité le "
                     "compte serait liquidé AVANT."),
        }

    vols = [d.volume for d in trading if d.direction in ("in", "inout")]
    return {
        "analysis_version": ANALYSIS_VERSION,
        "source": {"format": report.source_format, "encoding": report.encoding, "header": report.header,
                   "deals_read": len(deals), "rows_rejected": len(report.rejected_rows),
                   "rejected_examples": report.rejected_rows[:10], "rows_ignored": report.ignored_rows},
        "period": {"start": _fmt(deals[0].time), "end": _fmt(deals[-1].time)} if deals else None,
        "symbols": symbols,
        "contract": {"contract_size": contract_size, "note": contract_note},
        "verdict": verdict,
        "flags": flags,
        "counts": {"stop_out_closes": len(so), "end_of_test_closes": len(eot), "trading_deals": n_trading, "balance_operations": len(balance_ops), "entries": entries,
                   "adds_to_open_stack": adds, "adds_against_open_loss": adds_against, "baskets_closed": len(done),
                   "baskets_open_at_end": len(open_at_end), "inout_deals": inout_deals,
                   "unmatched_close_volume": round(unmatched_volume, 8)},
        "exposure": {"max_positions_same_direction": max_same_dir, "max_gross_lots": max_gross,
                     "min_entry_lot": min(vols) if vols else None, "max_entry_lot": max(vols) if vols else None,
                     "median_add_ratio": _median(escalations), "max_add_ratio": max(escalations) if escalations else None,
                     "median_first_lot_ratio_after_loss": mal, "median_first_lot_ratio_after_win": maw,
                     "worst_adverse_distance_while_adding": max((s.worst_add_distance for s in done + open_at_end),
                                                                default=0.0)},
        "baskets": {"count": len(baskets), "win_rate": len(wins) / len(baskets) if baskets else None,
                    "median_win": _median(wins), "median_loss": _median(losses),
                    "worst_loss": min(losses) if losses else None, "best_win": max(wins) if wins else None,
                    "net_total": sum(baskets) if baskets else 0.0,
                    "definition": "Série = suite de positions d'un même sens ouvertes sans retour à zéro ; son "
                                  "résultat inclut commission et swap."},
        "out_deals": {"count": len(out_results), "net_total": sum(out_results) if out_results else 0.0},
        "stress": stress,
        "thresholds": THRESHOLDS,
        "limits": [
            "Analyse du comportement visible dans les opérations, pas du code de l'EA (.ex5 fermé).",
            "Une période et un jeu de réglages : un autre marché peut déclencher un comportement absent ici.",
            "Le drawdown latent entre deux opérations n'est pas visible dans la liste des opérations ; seul le "
            "rapport MT5 « Equity drawdown » ou un rejeu sur les prix le mesure.",
            "Les règles de détection sont des heuristiques fixes et déclarées, non calibrées sur des EAs réels.",
            "Lecture de rapport construite d'après la mise en page MT5 documentée ; à confirmer sur un rapport du "
            "terminal du trader.",
        ],
    }
