"""Assembly of one EXTERNAL simulation record (an MT5 Strategy Tester run imported as data).

An imported simulation is NOT a backtest run of the Python engine: it lives in its own catalogue
(``external/``), carries its own format (``ato-external-sim/1``) and is never mixed with native runs.
Every number is either REPORTED (copied from the MT5 file, with its raw text) or RECOMPUTED (from the
deals, with the reconciliation against the reported figure). Missing fields are marked unavailable.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from datetime import datetime

from ..ea_audit.analysis import ANALYSIS_VERSION as BEHAVIOUR_VERSION
from ..ea_audit.analysis import analyse as behaviour
from ..ea_audit.report import Deal, ParsedReport, ReportFormatError
from ..storage.integrity import canonical_json
from . import reconstruct as R
from .mt5_report import PARSER_VERSION, Report

SIM_FORMAT = "ato-external-sim/1"
LAB_VERSION = "external-lab/1"
MAX_MANIFEST_BYTES = 256 * 1024


def _deal_json(d: Deal) -> dict:
    return {"seq": d.seq, "time": d.time.isoformat(), "deal": d.deal_id, "symbol": d.symbol, "type": d.kind,
            "direction": d.direction, "volume": d.volume, "price": d.price, "commission": d.commission,
            "swap": d.swap, "profit": d.profit, "balance": d.balance, "comment": d.comment}


def _order_json(o) -> dict:
    return {"order": o.order_id, "open_time": o.open_time.isoformat() if o.open_time else None,
            "time": o.time.isoformat() if o.time else None, "symbol": o.symbol, "type": o.kind,
            "volume_requested": o.volume_requested, "volume_filled": o.volume_filled, "price": o.price,
            "sl": o.sl, "tp": o.tp, "state": o.state, "comment": o.comment}


def deals_digest(deals: list[Deal]) -> str:
    return hashlib.sha256(canonical_json([_deal_json(d) for d in deals])).hexdigest()


def _merge(reports: list[Report]) -> Report:
    with_deals = [r for r in reports if r.deals]
    if not with_deals:
        raise ReportFormatError("Aucun tableau de deals (exécutions) trouvé : impossible de reconstruire la "
                                "simulation. Exportez le rapport complet du testeur (HTML ou Excel).")
    primary = max(with_deals, key=lambda r: (bool(r.summary), len(r.deals)))
    if len({deals_digest(r.deals) for r in with_deals}) > 1:
        raise ReportFormatError("Les fichiers envoyés contiennent des listes de deals différentes : importez-les "
                                "séparément (ce ne sont pas la même simulation).")
    for r in reports:
        if not primary.orders and r.orders:
            primary.orders, primary.order_header = r.orders, r.order_header
        if not primary.metadata and r.metadata:
            primary.metadata, primary.inputs, primary.summary = r.metadata, r.inputs, r.summary
            primary.title_lines = r.title_lines
        primary.rejected += [x for x in r.rejected if r is not primary]
    return primary


def _manifest(members: list[tuple[str, bytes]]) -> dict | None:
    for name, data in members:
        if name.lower().endswith(".json") and len(data) <= MAX_MANIFEST_BYTES:
            try:
                doc = json.loads(data.decode("utf-8-sig"))
            except (UnicodeDecodeError, ValueError):
                return {"file": name, "readable": False}
            if isinstance(doc, dict):
                return {"file": name, "readable": True,
                        "content": {k: v for k, v in list(doc.items())[:60] if isinstance(k, str)}}
    return None


def _server(rep: Report) -> tuple[str | None, str | None]:
    for line in rep.title_lines:
        m = re.match(r"(.+?)\s*\(Build\s*(\d+)\)", line)
        if m:
            return m.group(1).strip(), m.group(2)
    return None, None


def _timeframe(period_raw: str) -> str | None:
    m = re.match(r"\s*([A-Z]{1,2}\d{1,2})\b", period_raw or "")
    return m.group(1) if m else None


def _input(inputs: list[dict], *names: str) -> str | None:
    for i in inputs:
        if i["name"].lower() in names:
            return i["value"]
    return None


def build(reports: list[Report], members: list[tuple[str, bytes]], source_name: str, source_sha256: str,
          fallback_contract_size: float) -> dict:
    rep = _merge(reports)
    deals = sorted(rep.deals, key=lambda d: (d.time, d.seq))
    trading = [d for d in deals if d.kind in ("buy", "sell")]
    if not trading:
        raise ReportFormatError("Le rapport ne contient aucune opération d'achat ou de vente.")
    meta = rep.metadata
    server, build_no = _server(rep)
    cs_info = R.infer_contract_size(deals)
    cs = cs_info["value"] if cs_info["value"] else fallback_contract_size
    cs_source = "déduite des profits MT5" if cs_info["value"] else "hypothèse du profil enregistré (non vérifiée)"
    rec = R.reconstruct(deals, cs)
    metrics = R.deal_metrics(deals)
    recon = R.reconcile(rep.summary, metrics) if rep.summary else []
    tl = R.timeline(deals, cs)
    coll = R.collapse(deals, rec["trades"], tl, metrics)
    period = R.period_check(meta, deals)
    bal_check = R.balance_column_check(deals)
    ord_check = R.orders_check(rep.orders, deals)
    beh = behaviour(ParsedReport(deals=deals, source_format=rep.source_format, encoding=rep.encoding,
                                 header=rep.deal_header), cs, f"taille de contrat {cs:g} ({cs_source})")
    risk_inputs = R.risk_inputs(rep.inputs)

    checks = []
    if recon:
        bad = [r for r in recon if r["status"] != "concordant"]
        checks.append({"check": "résumé MT5 ↔ deals", "ok": not bad,
                       "detail": f"{len(recon) - len(bad)}/{len(recon)} indicateurs concordants"})
    else:
        checks.append({"check": "résumé MT5 ↔ deals", "ok": None, "detail": "résumé MT5 absent de la source"})
    checks.append({"check": "colonne Balance ↔ cumul des deals", "ok": bal_check["mismatches"] == 0 if bal_check["rows_checked"] else None,
                   "detail": f"{bal_check['rows_checked']} lignes, {bal_check['mismatches']} écart(s)"})
    p = rec["pairing"]
    checks.append({"check": "appariement ouverture/clôture ↔ profit MT5", "ok": p["closes_matched"] == p["closes_checked"],
                   "detail": f"{p['closes_matched']}/{p['closes_checked']} clôtures expliquées (règle {p['rule']})"})
    if ord_check["available"]:
        checks.append({"check": "ordres exécutés ↔ deals", "ok": ord_check["consistent"],
                       "detail": f"{ord_check['filled']} ordres exécutés pour {ord_check['trading_deals']} deals"})
    checks.append({"check": "clôtures sans ouverture connue", "ok": p["unmatched_close_volume"] == 0,
                   "detail": f"{p['unmatched_close_volume']:g} lot(s) clôturé(s) sans ouverture dans la source"})
    checks.append({"check": "lignes illisibles", "ok": not rep.rejected, "detail": f"{len(rep.rejected)} ligne(s) refusée(s)"})
    checks.append({"check": "doublons de deals", "ok": not rep.duplicates, "detail": f"{len(rep.duplicates)} doublon(s) écarté(s)"})
    failed = [c for c in checks if c["ok"] is False]
    unknown = [c for c in checks if c["ok"] is None]
    status = "écarts" if failed else ("partiel" if unknown else "validé")

    robot = meta.get("Expert") or None
    self_id = _input(rep.inputs, "inpnotename", "eaname", "inpeaname")
    identity = {
        "robot": robot, "self_identification": self_id, "symbol": meta.get("Symbol") or (trading[0].symbol or None),
        "timeframe": _timeframe(meta.get("Period", "")), "server": server, "build": build_no,
        "requested_period": meta.get("Period") or None, "initial_deposit": metrics["initial_deposit"],
        "currency": meta.get("Currency") or None, "leverage": meta.get("Leverage") or None,
        "inputs_sha256": hashlib.sha256(canonical_json(rep.inputs)).hexdigest(),
        "deals_sha256": deals_digest(deals), "source_sha256": source_sha256,
    }
    config = {k: identity[k] for k in ("robot", "self_identification", "symbol", "timeframe", "server",
                                       "requested_period", "initial_deposit", "currency", "leverage", "inputs_sha256")}
    sim_id = hashlib.sha256(canonical_json(identity)).hexdigest()[:16]
    largest = sorted(rec["trades"], key=lambda t: t["net"])[:10]
    return {
        "sim_id": sim_id, "identity": identity,
        "config_key": hashlib.sha256(canonical_json(config)).hexdigest()[:16],
        "test_key": hashlib.sha256(canonical_json({**config, "deals": identity["deals_sha256"]})).hexdigest()[:16],
        "kind": "simulation externe MT5 (importée, non exécutée par le moteur Python)",
        "versions": {"parser": PARSER_VERSION, "lab": LAB_VERSION, "behaviour": BEHAVIOUR_VERSION},
        "source": {"name": source_name, "sha256": source_sha256, "format": rep.source_format,
                   "encoding": rep.encoding, "report_file": rep.source_name,
                   "archive_members": [{"name": n, "bytes": len(b)} for n, b in members] if len(members) > 1 else []},
        "declared_manifest": _manifest(members),
        "robot": {"name": robot, "self_identification": self_id,
                  "declared_version": (re.search(r"[vV](\d+(?:\.\d+)+)", self_id or robot or "") or [None, None])[1],
                  "website": _input(rep.inputs, "inpnotewebsite")},
        "environment": {"server": server, "build": build_no, "company": meta.get("Company") or None,
                        "symbol": identity["symbol"], "timeframe": identity["timeframe"],
                        "requested_period": meta.get("Period") or None, "initial_deposit": metrics["initial_deposit"],
                        "currency": meta.get("Currency") or None, "leverage": meta.get("Leverage") or None,
                        "history_quality": meta.get("History Quality") or None, "bars": meta.get("Bars") or None,
                        "ticks": meta.get("Ticks") or None, "modelling": meta.get("Modelling") or None,
                        "title_lines": rep.title_lines},
        "inputs": rep.inputs, "risk_inputs": risk_inputs, "metadata": meta, "reported": rep.summary,
        "recomputed": metrics, "reconciliation": recon,
        "validation": {"status": status, "checks": checks, "rejected_rows": rep.rejected[:50],
                       "duplicates": rep.duplicates[:50]},
        "period": period,
        "contract_size": {"value": cs, "source": cs_source, **{k: v for k, v in cs_info.items() if k != "value"}},
        "counts": {"orders": len(rep.orders), "deals": len(deals), "trading_deals": len(trading),
                   "positions_opened": sum(1 for d in trading if d.direction in ("in", "inout")),
                   "closing_deals": sum(1 for d in trading if d.direction in ("out", "inout")),
                   "trades": len(rec["trades"]), "balance_operations": len(deals) - len(trading)},
        "pairing": rec["pairing"], "deals": [_deal_json(d) for d in deals],
        "orders": [_order_json(o) for o in rep.orders], "trades": rec["trades"], "timeline": tl,
        "lot_progression": R.lot_progression(deals), "monthly": R.monthly(rec["trades"]), "collapse": coll,
        "largest_losses": largest, "behaviour": beh,
        "findings": findings(coll, period, R.lot_progression(deals), rep.inputs, beh, metrics),
        "availability": {
            "position_ids": rep.has_position_ids, "orders_table": bool(rep.orders),
            "summary": bool(rep.summary), "inputs": bool(rep.inputs),
            "stop_loss_take_profit": bool(ord_check.get("with_sl") or ord_check.get("with_tp")) if ord_check["available"] else None,
            "equity_series": False, "price_series": False, "modelling_mode": bool(meta.get("Modelling")),
            "note": "L'équité n'est connue qu'aux instants d'opération (estimée au prix du deal) ; le rapport ne "
                    "contient ni série de prix ni courbe d'équité tick par tick.",
        },
        "limits": [
            "Simulation historique du Strategy Tester MT5, pas un résultat de trading réel.",
            "Le code .ex5 n'est ni exécuté ni lu : tout ce qui concerne sa logique interne est une hypothèse "
            "déduite du comportement observé.",
            "Équité entre deux opérations inconnue : les pertes latentes réelles ont pu être plus profondes.",
            "Contrat, coûts et conditions du serveur de démo non vérifiés de façon indépendante.",
            "Les deals d'un même test ne sont pas des observations indépendantes : ne pas les utiliser comme jeu "
            "d'apprentissage sans validation séparée.",
        ],
    }


def _money(x: float | None) -> str:
    return "—" if x is None else f"{x:,.2f}".replace(",", " ")


def findings(coll: dict | None, period: dict, lots: list[dict], inputs: list[dict], beh: dict, metrics: dict) -> dict:
    """What the report SHOWS (observed) versus what it SUGGESTS about the closed robot (hypotheses)."""
    observed, hypotheses = [], []
    wr, al, ap = metrics.get("profit_trades_pct"), metrics.get("average_loss_trade"), metrics.get("average_profit_trade")
    if wr is not None and al is not None and ap:
        observed.append({"fact": f"{wr:.1f} % de trades gagnants, mais une perte moyenne {abs(al) / ap:.1f} fois plus grande "
                                 f"que le gain moyen ({_money(al)} contre {_money(ap)}).", "source": "deals"})
    if coll:
        observed.append({"fact": f"Solde au plus haut : {_money(coll['peak_balance'])} le {coll['peak_time'][:16].replace('T', ' ')} ; "
                                 f"{coll['losing_trades']} pertes clôturées ensuite pour {_money(coll['losing_total'])} "
                                 f"({coll['drawdown_pct']:.2f} % du solde), {coll['lots_involved']:g} lots au total.",
                         "source": "deals"})
        if coll["first_entry"] and coll["last_entry"]:
            mins = (datetime.fromisoformat(coll["last_entry"]) - datetime.fromisoformat(coll["first_entry"])).total_seconds() / 60
            lo, hi = coll["entry_price_range"]
            observed.append({"fact": f"Les {coll['entries_involved']} positions concernées ont été ouvertes en {mins:.0f} minutes, "
                                     f"entre {lo:g} et {hi:g} ; toutes clôturées à {', '.join(f'{x:g}' for x in coll['exit_prices'])}.",
                             "source": "deals"})
        reasons = ", ".join(f"{v} × {k}" for k, v in coll["close_reasons"].items())
        observed.append({"fact": f"Motifs de clôture de ces pertes (commentaires MT5) : {reasons}.", "source": "deals"})
        g = coll.get("max_unrealised_gap_before")
        if g:
            observed.append({"fact": f"Écart maximal estimé entre solde réalisé ({_money(g['balance'])}) et équité "
                                     f"({_money(g['equity_est'])}) : {_money(g['gap'])}, le {g['t'][:16].replace('T', ' ')}. "
                                     "Le solde ne montrait pas la perte en cours.", "source": "deals (équité estimée)"})
    if period.get("ends_early"):
        observed.append({"fact": " ".join(period["evidence"]), "source": "rapport"})
        hypotheses.append({"statement": "Le testeur a arrêté la simulation parce que le compte ne pouvait plus continuer "
                                        "après le stop-out.",
                           "evidence": "Arrêt avant la date demandée, au même instant que les clôtures « so » et "
                                       "« end of test ».", "status": "hypothèse"})
    ratios = [x["lot_per_10k"] for x in lots if x.get("lot_per_10k")]
    if len(ratios) >= 10:
        m = statistics.fmean(ratios)
        cv = statistics.pstdev(ratios) / m if m else None
        if cv is not None and cv < 0.15:
            hypotheses.append({"statement": "La taille des lots est calculée automatiquement en proportion du solde : plus "
                                            "le compte gagne, plus chaque position est grosse.",
                               "evidence": f"Lot par tranche de 10 000 de solde : {min(ratios):.3f} à {max(ratios):.3f} "
                                           f"(moyenne {m:.3f}, variation {100 * cv:.0f} %) sur {len(ratios)} ouvertures.",
                               "status": "hypothèse"})
    by = {i["name"].lower(): i["value"] for i in inputs}
    if "inpddmode" in by or "inpddvalue" in by:
        off = by.get("inpddmode") in ("0", "false") and by.get("inpddvalue") in ("0", "0.0", "0.00", None)
        hypotheses.append({"statement": "Le contrôle de drawdown du robot était désactivé." if off else
                                        "Un contrôle de drawdown du robot était configuré.",
                           "evidence": f"Paramètres InpDDMode={by.get('inpddmode')}, InpDDValue={by.get('inpddvalue')} "
                                       "— interprétation d'après leurs noms, le code .ex5 n'étant pas lisible.",
                           "status": "hypothèse"})
    codes = {f["code"] for f in beh.get("flags", [])}
    if {"STACKING", "AVERAGING_DOWN"} & codes:
        hypotheses.append({"statement": "Le robot fonctionne en grille : il ajoute des positions quand le prix va contre lui, "
                                        "et le risque réel est celui de la série entière.",
                           "evidence": "; ".join(f["detail"] for f in beh["flags"] if f["code"] in ("STACKING", "AVERAGING_DOWN")),
                           "status": "hypothèse"})
    return {"observed": observed, "hypotheses": hypotheses,
            "note": "Constats = ce que contient le rapport. Hypothèses = interprétation du fonctionnement interne d'un code "
                    "fermé, à confirmer (paramètres, documentation de l'éditeur, nouveaux tests MT5)."}


def semantic_problems(body: dict) -> list[str]:
    """Recompute what must follow from the stored deals: an edited figure is detected."""
    out = []
    try:
        deals = [Deal(time=datetime.fromisoformat(d["time"]), seq=d["seq"], deal_id=d["deal"], symbol=d["symbol"],
                      kind=d["type"], direction=d["direction"], volume=d["volume"], price=d["price"],
                      commission=d["commission"], swap=d["swap"], profit=d["profit"], balance=d["balance"],
                      comment=d["comment"]) for d in body["deals"]]
    except (KeyError, TypeError, ValueError):
        return ["deals illisibles"]
    if deals_digest(deals) != body.get("identity", {}).get("deals_sha256"):
        out.append("empreinte des deals différente de l'identité")
    m = R.deal_metrics(deals)
    for k in ("net_profit", "gross_profit", "gross_loss", "total_trades", "balance_dd_maximal"):
        a, b = m.get(k), (body.get("recomputed") or {}).get(k)
        if a is None or b is None or abs(a - b) > 1e-6:
            out.append(f"indicateur {k} incohérent avec les deals")
    return out
