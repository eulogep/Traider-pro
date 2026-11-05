"""Reconstruction of positions and trades from MT5 deals, reconciliation with the MT5 summary, and the
observed facts of a "risk collapse". Everything is derived from the imported deals; nothing is assumed about
the robot's code.

Vocabulary (kept distinct everywhere):
* ORDER  — a request sent by the robot (Orders table: state filled / canceled …);
* DEAL   — an execution (Deals table): direction ``in`` opens, ``out`` closes, ``in/out`` reverses. A BUY deal may
           CLOSE a SELL position — the side of a deal never tells whether it opens;
* POSITION — what an ``in`` deal opens; the tester report has NO position id, so closes are paired to openings
           FIFO or LIFO per side. The pairing is VERIFIED: each close's MT5 profit must equal
           (exit − entry) × volume × contract size for the paired openings; the better rule is kept and its
           verification rate published;
* TRADE  — one closed position (or part of it), with its entry and exit deals.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass

from ..ea_audit.report import Deal

STOP_OUT = re.compile(r"^\s*so\b", re.I)
END_OF_TEST = re.compile(r"end\s+of\s+test", re.I)
TP_SL = re.compile(r"^\s*(tp|sl)\b", re.I)
EPS = 1e-9


@dataclass
class _Open:
    seq: int
    deal_id: str
    time: object
    side: int
    volume: float
    price: float
    commission: float
    comment: str


def close_reason(comment: str) -> str:
    c = comment or ""
    if STOP_OUT.search(c):
        return "stop-out"
    if END_OF_TEST.search(c):
        return "fin du test"
    m = TP_SL.match(c)
    if m:
        return "take-profit" if m.group(1).lower() == "tp" else "stop-loss"
    return "robot"


def _pair(deals: list[Deal], rule: str, cs: float | None) -> tuple[list[dict], dict]:
    """Trades from deals under ``rule`` (fifo|lifo). If ``cs`` is given, counts closes whose MT5 profit matches."""
    book: dict[tuple[str, int], list[_Open]] = defaultdict(list)
    trades: list[dict] = []
    checked = matched = unmatched_vol = 0
    for d in deals:
        if d.kind not in ("buy", "sell"):
            continue
        side = 1 if d.kind == "buy" else -1
        if d.direction == "in":
            book[(d.symbol, side)].append(_Open(d.seq, d.deal_id, d.time, side, d.volume, d.price, d.commission,
                                                d.comment))
            continue
        if d.direction not in ("out", "inout"):
            continue
        target = (d.symbol, -side)
        stack = book[target]
        left = d.volume if d.direction == "out" else min(d.volume, sum(o.volume for o in stack))
        expected, parts = 0.0, []
        if rule == "match" and cs is not None and d.direction == "out":
            # an open position of exactly this volume whose price move reproduces MT5's profit, oldest first
            hit = next((o for o in stack if abs(o.volume - d.volume) <= EPS
                        and abs((d.price - o.price) * o.side * o.volume * cs - d.profit)
                        <= max(0.011, 1e-6 * abs(d.profit))), None)
            if hit is not None:
                stack.remove(hit)
                stack.insert(0, hit)
        while left > EPS and stack:
            o = stack[-1] if rule == "lifo" else stack[0]
            take = min(o.volume, left)
            parts.append((o, take))
            expected += (d.price - o.price) * o.side * take
            o.volume -= take
            left -= take
            if o.volume <= EPS:
                stack.remove(o)
        if d.direction == "out":
            unmatched_vol += max(0.0, left)
        closed = sum(t for _, t in parts)
        if cs is not None and closed > EPS and abs(left) <= EPS:
            checked += 1
            if abs(expected * cs - d.profit) <= max(0.011, 1e-6 * abs(d.profit)):
                matched += 1
        for o, take in parts:
            share = take / closed if closed > EPS else 0.0
            trades.append({
                "side": "BUY" if o.side > 0 else "SELL", "symbol": d.symbol, "volume": round(take, 8),
                "entry_deal": o.deal_id, "entry_seq": o.seq, "entry_time": o.time.isoformat(), "entry_price": o.price,
                "entry_comment": o.comment,
                "exit_deal": d.deal_id, "exit_seq": d.seq, "exit_time": d.time.isoformat(), "exit_price": d.price,
                "exit_comment": d.comment, "close_reason": close_reason(d.comment),
                "profit": d.profit * share, "swap": d.swap * share,
                "commission": d.commission * share + o.commission * (take / (take + o.volume) if o.volume > EPS else 1),
            })
        if d.direction == "inout" and d.volume - closed > EPS:
            book[(d.symbol, side)].append(_Open(d.seq, d.deal_id, d.time, side, d.volume - closed, d.price, 0.0,
                                                d.comment))
    for t in trades:
        t["net"] = t["profit"] + t["swap"] + t["commission"]
    still_open = [{"symbol": k[0], "side": "BUY" if k[1] > 0 else "SELL", "volume": o.volume, "entry_deal": o.deal_id,
                   "entry_time": o.time.isoformat(), "entry_price": o.price} for k, v in book.items() for o in v]
    return trades, {"rule": rule, "closes_checked": checked, "closes_matched": matched,
                    "unmatched_close_volume": round(unmatched_vol, 8), "open_at_end": still_open}


def infer_contract_size(deals: list[Deal]) -> dict:
    """Units per lot implied by MT5's own profits: profit / ((exit − entry) × side × volume), FIFO-paired closes."""
    trades, _ = _pair(deals, "fifo", None)
    by_exit = defaultdict(list)
    for t in trades:
        by_exit[t["exit_seq"]].append(t)
    est = []
    for parts in by_exit.values():
        move = sum((p["exit_price"] - p["entry_price"]) * (1 if p["side"] == "BUY" else -1) * p["volume"] for p in parts)
        prof = sum(p["profit"] for p in parts)
        if abs(move) > 1e-6 and abs(prof) > 0.05:
            est.append(prof / move)
    if not est:
        return {"value": None, "samples": 0, "note": "Aucune clôture exploitable pour déduire la taille du contrat."}
    med = statistics.median(est)
    near = sum(1 for e in est if abs(e - med) <= 0.01 * abs(med))
    return {"value": round(med, 6), "samples": len(est), "consistent_samples": near,
            "note": "Déduite des profits calculés par MT5 lui-même (et non supposée)."}


def reconstruct(deals: list[Deal], contract_size: float) -> dict:
    """Pairing rules tried: exact profit match (else FIFO), FIFO, LIFO. The one explaining the most MT5 profits is
    kept — an identification step, published with every count; it changes no reported figure."""
    runs = {rule: _pair(deals, rule, contract_size) for rule in ("match", "fifo", "lifo")}
    best = max(runs, key=lambda r: (runs[r][1]["closes_matched"], r == "match"))
    trades, verif = runs[best]
    verif = {**verif, "alternatives": {r: v[1]["closes_matched"] for r, v in runs.items()},
             "position_ids_in_report": False,
             "note": "Le rapport du testeur ne contient pas d'identifiant de position : l'appariement ouverture/clôture "
                     "est reconstruit puis vérifié contre le profit calculé par MT5 pour chaque clôture."}
    trades.sort(key=lambda t: (t["exit_seq"], t["entry_seq"]))
    for i, t in enumerate(trades):
        t["trade_no"] = i + 1
    return {"trades": trades, "pairing": verif}


# ---------------------------------------------------------------------------------------------- metrics
def _closing(deals: list[Deal]) -> list[Deal]:
    return [d for d in deals if d.kind in ("buy", "sell") and d.direction in ("out", "inout")]


def deal_metrics(deals: list[Deal]) -> dict:
    """Recomputed with MT5's own unit: a « trade » in the summary is a CLOSING deal (out / in-out)."""
    trading = [d for d in deals if d.kind in ("buy", "sell")]
    closing = _closing(deals)
    res = [d.profit + d.swap + d.commission for d in closing]
    wins = [x for x in res if x > 0]
    losses = [x for x in res if x < 0]
    deposits = sum(d.profit for d in deals if d.kind == "balance")
    first_dep = next((d.profit for d in deals if d.kind == "balance"), None)
    net = sum(d.profit + d.swap + d.commission for d in trading)
    # MT5 calls a trade "long" when it CLOSES a long position: the closing deal is a SELL
    longs = [d for d in closing if d.kind == "sell"]
    shorts = [d for d in closing if d.kind == "buy"]

    def won(xs):
        return 100.0 * sum(1 for d in xs if d.profit + d.swap + d.commission > 0) / len(xs) if xs else None

    bal, peak, dd, dd_pct, bal_series = 0.0, None, 0.0, 0.0, []
    for d in deals:
        bal += d.profit + d.swap + d.commission
        bal_series.append(bal)
        if d.kind == "balance":
            peak = bal if peak is None else max(peak, bal)
            continue
        peak = bal if peak is None else max(peak, bal)
        if peak - bal > dd:
            dd, dd_pct = peak - bal, 100.0 * (peak - bal) / peak if peak > 0 else 0.0
    streak_w = streak_l = best_w = best_l = 0
    run_l_amt = worst_l_amt = 0.0
    for x in res:
        if x > 0:
            streak_w, streak_l, run_l_amt = streak_w + 1, 0, 0.0
        elif x < 0:
            streak_l, streak_w = streak_l + 1, 0
            run_l_amt += x
            worst_l_amt = min(worst_l_amt, run_l_amt)
        best_w, best_l = max(best_w, streak_w), max(best_l, streak_l)
    return {
        "net_profit": net, "gross_profit": sum(wins), "gross_loss": sum(losses),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else None,
        "total_trades": len(closing), "total_deals": len(trading),
        "profit_trades": len(wins), "profit_trades_pct": 100.0 * len(wins) / len(closing) if closing else None,
        "loss_trades": len(losses), "loss_trades_pct": 100.0 * len(losses) / len(closing) if closing else None,
        "largest_profit_trade": max(wins) if wins else None, "largest_loss_trade": min(losses) if losses else None,
        "average_profit_trade": sum(wins) / len(wins) if wins else None,
        "average_loss_trade": sum(losses) / len(losses) if losses else None,
        "long_trades": len(longs), "long_won_pct": won(longs), "short_trades": len(shorts), "short_won_pct": won(shorts),
        "balance_dd_maximal": dd, "balance_dd_maximal_pct": dd_pct,
        "max_consecutive_wins": best_w, "max_consecutive_losses": best_l, "worst_consecutive_loss_amount": worst_l_amt,
        "initial_deposit": first_dep, "deposits_total": deposits, "final_balance": bal_series[-1] if bal_series else None,
    }


def _decimals(raw: str) -> int:
    m = re.search(r"[.,](\d+)", raw or "")
    return len(m.group(1)) if m else 0


# MT5 summary key -> (recomputed key, field of the reported value: "value" | "pct" | "amount")
RECON = [
    ("net_profit", "net_profit", "value"), ("gross_profit", "gross_profit", "value"),
    ("gross_loss", "gross_loss", "value"), ("profit_factor", "profit_factor", "value"),
    ("total_trades", "total_trades", "value"), ("total_deals", "total_deals", "value"),
    ("profit_trades", "profit_trades", "value"), ("profit_trades", "profit_trades_pct", "pct"),
    ("loss_trades", "loss_trades", "value"), ("largest_profit_trade", "largest_profit_trade", "value"),
    ("largest_loss_trade", "largest_loss_trade", "value"), ("average_profit_trade", "average_profit_trade", "value"),
    ("average_loss_trade", "average_loss_trade", "value"), ("long_trades", "long_trades", "value"),
    ("long_trades", "long_won_pct", "pct"), ("short_trades", "short_trades", "value"),
    ("short_trades", "short_won_pct", "pct"), ("balance_dd_maximal", "balance_dd_maximal", "value"),
    ("balance_dd_maximal", "balance_dd_maximal_pct", "pct"), ("max_consecutive_wins", "max_consecutive_wins", "value"),
    ("max_consecutive_losses", "max_consecutive_losses", "value"),
    ("max_consecutive_losses", "worst_consecutive_loss_amount", "amount"),
    ("initial_deposit", "initial_deposit", "value"),
]


def reconcile(summary: dict, metrics: dict) -> list[dict]:
    """Reported (MT5) vs recomputed (from deals). Tolerance = rounding of the reported figure."""
    rows = []
    for key, mkey, part in RECON:
        rep = summary.get(key)
        if not rep or rep.get(part) is None:
            continue
        reported = rep[part]
        computed = metrics.get(mkey)
        raw = rep.get("raw", "")
        if part == "pct":
            m = re.search(r"([\d.,]+)%", raw)
            dec = _decimals(m.group(1)) if m else 2
        elif part == "amount":
            m = re.search(r"\(([^)]*)\)", raw)
            dec = _decimals(m.group(1)) if m else 2
        else:
            dec = _decimals(raw.split("(")[0])
        tol = 0.5 * 10 ** (-dec) + 1e-9
        ok = computed is not None and math.isfinite(computed) and abs(computed - reported) <= tol
        rows.append({"metric": key if part == "value" else f"{key}.{part}", "label": rep["label"], "reported": reported,
                     "computed": computed, "tolerance": tol,
                     "status": "concordant" if ok else ("non calculable" if computed is None else "écart")})
    return rows


def balance_column_check(deals: list[Deal]) -> dict:
    bal, bad, first = 0.0, 0, None
    checked = 0
    for d in deals:
        bal += d.profit + d.swap + d.commission
        if d.balance is None:
            continue
        checked += 1
        if abs(bal - d.balance) > 0.011:
            bad += 1
            first = first or {"deal": d.deal_id, "reported": d.balance, "recomputed": bal}
    return {"rows_checked": checked, "mismatches": bad, "first_mismatch": first}


def orders_check(orders: list, deals: list[Deal]) -> dict:
    """Orders are requests, deals are executions: every trading deal should come from one FILLED order."""
    if not orders:
        return {"available": False, "note": "Tableau des ordres absent de cette source : seules les exécutions sont connues."}
    states: dict[str, int] = defaultdict(int)
    for o in orders:
        states[o.state or "inconnu"] += 1
    filled = states.get("filled", 0)
    trading = sum(1 for d in deals if d.kind in ("buy", "sell"))
    return {"available": True, "orders": len(orders), "states": dict(states), "filled": filled,
            "trading_deals": trading, "consistent": filled == trading,
            "with_sl": sum(1 for o in orders if o.sl), "with_tp": sum(1 for o in orders if o.tp),
            "note": "Un ordre est une demande du robot ; seul un deal est une exécution."}


# ---------------------------------------------------------------------------------------------- timeline & facts
def timeline(deals: list[Deal], contract_size: float) -> list[dict]:
    """State after each trading deal: realised balance, open lots per side, floating P&L and equity ESTIMATED by
    marking every open position at that deal's price (the report contains no price series in between)."""
    open_pos: dict[int, list[list[float]]] = {1: [], -1: []}
    bal, out = 0.0, []
    for d in deals:
        bal += d.profit + d.swap + d.commission
        if d.kind not in ("buy", "sell"):
            out.append({"t": d.time.isoformat(), "balance": bal, "equity_est": None, "long_lots": None,
                        "short_lots": None, "event": "balance"})
            continue
        side = 1 if d.kind == "buy" else -1
        if d.direction == "in":
            open_pos[side].append([d.volume, d.price])
        else:
            left, st = d.volume, open_pos[-side]
            while left > EPS and st:
                take = min(st[0][0], left)
                st[0][0] -= take
                left -= take
                if st[0][0] <= EPS:
                    st.pop(0)
        floating = sum((d.price - p) * s * v * contract_size for s in (1, -1) for v, p in open_pos[s])
        out.append({"t": d.time.isoformat(), "balance": bal, "equity_est": bal + floating, "floating_est": floating,
                    "long_lots": round(sum(v for v, _ in open_pos[1]), 8),
                    "short_lots": round(sum(v for v, _ in open_pos[-1]), 8),
                    "positions": len(open_pos[1]) + len(open_pos[-1]), "price": d.price,
                    "event": f"{d.kind} {d.direction}", "deal": d.deal_id})
    return out


def monthly(trades: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for t in trades:
        m = t["exit_time"][:7]
        a = agg.setdefault(m, {"month": m, "trades": 0, "wins": 0, "net": 0.0, "worst": 0.0, "lots": 0.0})
        a["trades"] += 1
        a["wins"] += t["net"] > 0
        a["net"] += t["net"]
        a["worst"] = min(a["worst"], t["net"])
        a["lots"] += t["volume"]
    return [agg[k] for k in sorted(agg)]


def collapse(deals: list[Deal], trades: list[dict], tl: list[dict], metrics: dict) -> dict | None:
    """The largest realised drawdown episode: peak balance → trough, the trades closed in it, how the exposure
    was built, and the gap between realised balance and estimated equity just before."""
    pts = [p for p in tl if p["balance"] is not None]
    if not pts:
        return None
    peak_i, trough_i, worst_dd = 0, 0, 0.0
    run_peak_i = 0
    for i, p in enumerate(pts):
        if p["balance"] > pts[run_peak_i]["balance"]:
            run_peak_i = i
        dd = pts[run_peak_i]["balance"] - p["balance"]
        if dd > worst_dd:
            worst_dd, peak_i, trough_i = dd, run_peak_i, i
    if worst_dd <= 0:
        return None
    t_peak, t_trough = pts[peak_i]["t"], pts[trough_i]["t"]
    closed = [t for t in trades if t_peak < t["exit_time"] <= t_trough]
    losers = sorted([t for t in closed if t["net"] < 0], key=lambda t: t["exit_seq"])
    involved = sorted({t["entry_seq"] for t in losers})
    entries = [t for t in sorted(losers, key=lambda t: t["entry_seq"])]
    gaps = []
    for a, b in zip(entries, entries[1:], strict=False):
        gaps.append({"from": a["entry_deal"], "to": b["entry_deal"], "minutes": _minutes(a["entry_time"], b["entry_time"]),
                     "price_move": round(b["entry_price"] - a["entry_price"], 5)})
    before = [p for p in pts[:trough_i] if p.get("equity_est") is not None]
    worst_float = min(before, key=lambda p: p["equity_est"] - p["balance"]) if before else None
    reasons = defaultdict(int)
    for t in losers:
        reasons[t["close_reason"]] += 1
    return {
        "peak_time": t_peak, "peak_balance": pts[peak_i]["balance"], "trough_time": t_trough,
        "trough_balance": pts[trough_i]["balance"], "drawdown": worst_dd,
        "drawdown_pct": 100.0 * worst_dd / pts[peak_i]["balance"] if pts[peak_i]["balance"] > 0 else None,
        "losing_trades": len(losers), "losing_total": sum(t["net"] for t in losers),
        "lots_involved": round(sum(t["volume"] for t in losers), 8), "entries_involved": len(involved),
        "close_reasons": dict(reasons), "trades": losers, "entry_gaps": gaps,
        "first_entry": entries[0]["entry_time"] if entries else None,
        "last_entry": entries[-1]["entry_time"] if entries else None,
        "entry_price_range": [min(t["entry_price"] for t in entries), max(t["entry_price"] for t in entries)] if entries else None,
        "exit_prices": sorted({t["exit_price"] for t in losers}),
        "max_unrealised_gap_before": None if worst_float is None else {
            "t": worst_float["t"], "balance": worst_float["balance"], "equity_est": worst_float["equity_est"],
            "gap": worst_float["equity_est"] - worst_float["balance"]},
    }


def _minutes(a: str, b: str) -> float:
    from datetime import datetime
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60.0


_PERIOD = re.compile(r"(\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})")


def period_check(metadata: dict, deals: list[Deal]) -> dict:
    raw = metadata.get("Period", "")
    m = _PERIOD.search(raw)
    req = (m.group(1).replace(".", "-"), m.group(2).replace(".", "-")) if m else (None, None)
    trading = [d for d in deals if d.kind in ("buy", "sell")]
    first = trading[0].time.isoformat() if trading else None
    last = trading[-1].time.isoformat() if trading else None
    tail = [d for d in trading if trading and d.time == trading[-1].time]
    forced = sorted({close_reason(d.comment) for d in tail if d.direction in ("out", "inout")})
    early = bool(req[1] and last and last[:10] < req[1])
    evidence = []
    if early:
        evidence.append(f"Dernière opération le {last[:16].replace('T', ' ')}, fin demandée le {req[1]}.")
        if "stop-out" in forced:
            evidence.append("Les dernières clôtures portent le commentaire MT5 de stop-out (« so … % »).")
        if "fin du test" in forced:
            evidence.append("Les positions restantes sont fermées au même instant avec « end of test ».")
    return {"requested_raw": raw, "requested_start": req[0], "requested_end": req[1], "first_deal": first,
            "last_deal": last, "ends_early": early, "last_instant_close_reasons": forced, "evidence": evidence,
            "interpretation": ("Observé : le test s'arrête avant la date demandée, juste après un stop-out. "
                               "Hypothèse (non vérifiable dans le rapport) : le testeur a interrompu la simulation "
                               "parce que le compte ne pouvait plus continuer.") if early and "stop-out" in forced
            else ("Observé : arrêt avant la date demandée, cause non indiquée dans le rapport." if early else
                  "Période observée cohérente avec la période demandée.")}


RISK_INPUT_HINTS = re.compile(r"lot|risk|dd|drawdown|grid|step|martingale|multipl|mult|max|equity|stop", re.I)


def risk_inputs(inputs: list[dict]) -> list[dict]:
    return [i for i in inputs if RISK_INPUT_HINTS.search(i["name"]) and not i["name"].startswith(">")]


def lot_progression(deals: list[Deal]) -> list[dict]:
    """Entry lot size against the realised balance just before — automatic sizing shows as a straight line."""
    bal, out = 0.0, []
    for d in deals:
        if d.kind in ("buy", "sell") and d.direction == "in":
            out.append({"t": d.time.isoformat(), "lot": d.volume, "balance_before": bal,
                        "lot_per_10k": d.volume / bal * 10_000 if bal > 0 else None})
        bal += d.profit + d.swap + d.commission
    return out
