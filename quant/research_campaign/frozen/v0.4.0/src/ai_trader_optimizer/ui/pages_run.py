"""Backtesting, Trade Journal, Risk Management and Settings pages."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .. import ENGINE_VERSION, __version__
from ..analytics import results_by_period
from ..backtest import FILL_ASSUMPTIONS_FR, BacktestConfig, ExecutionCosts
from ..paths import data_dir, strategies_dir
from ..risk import LEGACY_V01_RISK, REJECTION_LABELS_FR, XAUUSD_HYPOTHETICAL, ContractSpec, RiskConfig
from ..safety import DEMO_TRADING_ENABLED, LIVE_TRADING_ENABLED
from ..services import default_config, reproduce, run_and_store, save_defaults, save_risk
from .common import (
    ALL_REASON_LABELS,
    apply_session_overrides,
    candles_chart,
    catalog,
    data_kind_warning,
    drawdown_chart,
    empty_state,
    equity_chart,
    fmt_money,
    fmt_num,
    fmt_pct,
    kind_badge,
    load_dataset,
    period_chart,
    pnl_histogram,
    reasons_chart,
    reasons_fr,
    runs_with_labels,
    safety_banner,
    strategies,
)


def _select_run(key: str):
    cat = catalog()
    runs = runs_with_labels(cat)
    if runs.empty:
        return None
    ids = runs["run_id"].tolist()
    cur = st.session_state.get("selected_run")
    sel = st.selectbox("Backtest", ids, index=ids.index(cur) if cur in ids else 0, key=key,
                       format_func=dict(zip(ids, runs["libellé"], strict=False)).get)
    st.session_state["selected_run"] = sel
    return cat.load_run(sel)


# ------------------------------------------------------------------ Backtesting
def backtesting_page() -> None:
    st.title("Backtesting")
    safety_banner()
    cat, strats = catalog(), strategies()
    datasets = cat.list_datasets()
    runnable = strats.runnable()
    if datasets.empty:
        empty_state("Aucun jeu de données.", "Allez dans **Market Data** pour importer un CSV ou générer la démo.")
        return
    if not runnable:
        empty_state("Aucune stratégie exécutable.", "Voir **Strategy Lab**.")
        return

    base = default_config(cat)
    with st.form("backtest"):
        c1, c2 = st.columns(2)
        ids = datasets["dataset_id"].tolist()
        cur = st.session_state.get("selected_dataset")
        names = dict(zip(ids, datasets["name"] + " · " + datasets["kind"] + " · " + datasets["timeframe"], strict=False))
        ds_id = c1.selectbox("Données", ids, index=ids.index(cur) if cur in ids else 0, format_func=names.get)
        keys = [s.key for s in runnable]
        cur_s = st.session_state.get("selected_strategy")
        skey = c2.selectbox("Stratégie", keys, index=keys.index(cur_s) if cur_s in keys else 0,
                            format_func=lambda k: f"{strats.specs[k].name} — v{strats.specs[k].version}")
        meta = cat.dataset_meta(ds_id)
        start_d, end_d = pd.Timestamp(meta.start).date(), pd.Timestamp(meta.end).date()
        c3, c4 = st.columns(2)
        d_from = c3.date_input("Entrées à partir du (UTC)", start_d, min_value=start_d, max_value=end_d)
        d_to = c4.date_input("Jusqu'au (UTC, inclus)", end_d, min_value=start_d, max_value=end_d)
        st.markdown("**Coûts hypothétiques** (pré-remplis depuis Settings — à vérifier chez le courtier)")
        k1, k2, k3, k4 = st.columns(4)
        equity = k1.number_input("Capital initial", 100.0, 10_000_000.0, float(base.initial_equity), step=500.0)
        spread = k2.number_input("Spread fixe (prix)", 0.0, 50.0, float(base.costs.spread), step=0.05, format="%.3f")
        slip = k3.number_input("Glissement / exécution (prix)", 0.0, 50.0, float(base.costs.slippage), step=0.01,
                               format="%.3f")
        comm = k4.number_input("Commission / lot / côté", 0.0, 100.0, float(base.costs.commission_per_lot_per_side),
                               step=0.5)
        o1, o2, o3 = st.columns(3)
        close_eos = o1.checkbox("Fermer en fin de session", False)
        max_bars = o2.number_input("Durée max d'un trade (bougies, 0 = aucune)", 0, 100_000, 0)
        label = o3.text_input("Libellé du run", "")
        go = st.form_submit_button("Lancer le backtest", type="primary")

    spec = strats.specs[skey]
    cfg_preview = apply_session_overrides(base, skey)
    st.caption(f"Paramètres : {spec.resolve_params(cfg_preview.strategy_params)} · horaires : "
               f"{(cfg_preview.trading_hours or spec.trading_hours).model_dump()} · contrat : "
               f"{base.contract.contract_size} unités/lot ({base.contract.source}) · risque : "
               f"{base.risk.risk_per_trade_pct} %/trade, perte jour max {base.risk.max_daily_loss_pct} %")
    if go:
        if d_to < d_from:
            st.error("La date de fin précède la date de début.")
            return
        cfg = cfg_preview.model_copy(update={
            "initial_equity": equity,
            "costs": ExecutionCosts(spread=spread, slippage=slip, commission_per_lot_per_side=comm),
            "trade_start": None if d_from == start_d else pd.Timestamp(d_from, tz="UTC").isoformat(),
            "trade_end": None if d_to == end_d else (pd.Timestamp(d_to, tz="UTC") + pd.Timedelta(days=1)
                                                     - pd.Timedelta(seconds=1)).isoformat(),
            "close_at_session_end": close_eos, "max_bars_in_trade": int(max_bars) or None})
        cfg = BacktestConfig.model_validate(cfg.model_dump())
        with st.spinner("Simulation en cours…"):
            try:
                res = run_and_store(cat, ds_id, spec, cfg, label=label)
            except Exception as exc:
                st.error(f"Simulation impossible : {exc}")
                return
        st.session_state["selected_run"] = res.run_id
        st.success(f"Backtest enregistré : run `{res.run_id}` · empreinte des résultats `{res.manifest['result_hash']}`")

    st.divider()
    res = _select_run("bt_run")
    if res is None:
        empty_state("Aucun résultat pour l'instant : lancez un backtest.")
        return
    show_results(res)


def show_results(res) -> None:
    m, man = res.metrics, res.manifest
    st.markdown(kind_badge(man["data_kind"]) + f'<span class="ato-muted">{man["strategy"]["name"]} v'
                f'{man["strategy"]["version"]} · {man["dataset"]["name"]} · run {man["run_id"]}</span>',
                unsafe_allow_html=True)
    data_kind_warning(man["data_kind"])
    if man["strategy"].get("illustrative"):
        st.caption("Stratégie illustrative : ses résultats ne sont pas ceux d'une stratégie rentable.")
    cur = man["config"]["account_currency"]
    a = st.columns(4)
    a[0].metric("Capital initial", fmt_money(m["initial_equity"], cur))
    a[1].metric("Capital final", fmt_money(m["final_equity"], cur))
    a[2].metric("P&L net", fmt_money(m["net_pnl"], cur), f"{m['return_pct']:.2f} %")
    a[3].metric("Transactions", m["trades"])
    b = st.columns(4)
    b[0].metric("Win rate", fmt_pct(m["win_rate_pct"], 1))
    b[1].metric("Profit factor", fmt_num(m["profit_factor"]),
                help=m["unavailable"].get("profit_factor"))
    b[2].metric("Espérance / trade", fmt_money(m["expectancy"], cur),
                None if m.get("expectancy_r") is None else f"{m['expectancy_r']:.3f} R")
    b[3].metric("Drawdown max MTM", fmt_pct(m["max_dd_mtm_pct"]), f"clôturé {m['max_dd_closed_pct']:.2f} %",
                delta_color="off", help=m["drawdown_note"])
    c = st.columns(4)
    c[0].metric("Coûts estimés", fmt_money(m["total_costs"], cur), help="Spread + glissement + commissions")
    c[1].metric("P&L avant coûts", fmt_money(m.get("pnl_before_costs"), cur))
    c[2].metric("Signaux / entrés", f"{m['signals']} / {m['signals_entered']}")
    c[3].metric("Pertes > risque prévu", m.get("losses_beyond_planned_risk", 0), help="Gaps / glissement au-delà du stop")
    if not m["sample_sufficient"]:
        st.warning(m["sample_note"])
    for k, why in m["unavailable"].items():
        st.caption(f"Indisponible — {k} : {why}")

    if len(res.equity):
        st.subheader("Courbe de capital")
        st.altair_chart(equity_chart(res.equity, m["initial_equity"]), width="stretch")
        st.altair_chart(drawdown_chart(res.equity, m["initial_equity"]), width="stretch")
    if res.trades.empty:
        empty_state("Aucune transaction simulée sur cette période.",
                    "Consultez les refus ci-dessous et les raisons d'attente : la stratégie n'a peut-être produit "
                    "aucun signal, ou le Risk Guardian les a tous refusés.")
    else:
        left, right = st.columns(2)
        with left:
            st.subheader("Répartition des résultats")
            st.altair_chart(pnl_histogram(res.trades), width="stretch")
        with right:
            st.subheader("Résultats par période")
            freq = st.segmented_control("Période", ["M", "W", "D", "H", "DOW"], default="M", key="freq",
                                        format_func={"M": "Mois", "W": "Semaine", "D": "Jour", "H": "Heure",
                                                     "DOW": "Jour de semaine"}.get)
            per = results_by_period(res.trades, freq or "M")
            st.altair_chart(period_chart(per), width="stretch")
        d1, d2, d3 = st.columns(3)
        d1.markdown("**Par sens**")
        d1.dataframe(pd.DataFrame(m["by_direction"]).T, width="stretch")
        d2.markdown("**Raisons de sortie**")
        d2.dataframe(pd.Series(m["exit_reasons"], name="trades"), width="stretch")
        d3.markdown("**Coûts**")
        d3.dataframe(pd.Series({"commissions": m["commission_total"], "spread": m["spread_cost_total"],
                                "glissement": m["slippage_cost_total"]}, name=cur).round(2), width="stretch")
    if m["rejection_reasons"]:
        st.subheader("Signaux refusés")
        st.altair_chart(reasons_chart(m["rejection_reasons"]), width="stretch")
    with st.expander("Raisons d'attente de la stratégie (bougies sans signal)"):
        st.dataframe(pd.Series(m.get("wait_reasons", {}), name="bougies"), width="stretch")
    with st.expander("Hypothèses de simulation — à lire avant d'interpréter"):
        for a_ in man.get("fill_assumptions", FILL_ASSUMPTIONS_FR):
            st.markdown(f"- {a_}")
    with st.expander("Manifeste (traçabilité données / stratégie / configuration)"):
        st.json(man, expanded=False)

    e1, e2, e3, e4, e5 = st.columns(5)
    rid = man["run_id"]
    e1.download_button("Trades CSV", res.trades.to_csv(index=False).encode(), f"trades_{rid}.csv", "text/csv")
    e2.download_button("Décisions CSV", res.decisions.to_csv(index=False).encode(), f"decisions_{rid}.csv", "text/csv")
    e3.download_button("Métriques JSON", json.dumps(m, indent=2, default=str, ensure_ascii=False).encode(),
                       f"metrics_{rid}.json", "application/json")
    e4.download_button("Manifeste JSON", json.dumps(man, indent=2, default=str, ensure_ascii=False).encode(),
                       f"manifest_{rid}.json", "application/json")
    if e5.button("Reproduire", help="Relance la simulation depuis le manifeste et compare les empreintes"):
        try:
            rep = reproduce(catalog(), rid, strategies())
            ok, old, new = rep["identical"], rep["stored_hash"], rep["new_hash"]
        except Exception as exc:
            st.error(f"Reproduction impossible : {exc}")
        else:
            (st.success if ok else st.error)(
                f"{'Résultats identiques' if ok else 'RÉSULTATS DIFFÉRENTS'} : empreinte enregistrée {old}, "
                f"nouvelle {new}.")


# ------------------------------------------------------------------ Trade journal
def journal_page() -> None:
    st.title("Trade Journal")
    safety_banner()
    res = _select_run("journal_run")
    if res is None:
        empty_state("Aucun backtest enregistré.", "Lancez une simulation dans **Backtesting**.")
        return
    data_kind_warning(res.manifest["data_kind"])
    tab_t, tab_d = st.tabs(["Transactions simulées", "Toutes les décisions (signaux)"])
    with tab_t:
        t = res.trades
        if t.empty:
            empty_state("Aucune transaction dans ce run.")
        else:
            f1, f2, f3 = st.columns(3)
            dirs = f1.multiselect("Sens", ["BUY", "SELL"], ["BUY", "SELL"])
            reasons = sorted(t["exit_reason"].unique())
            exits = f2.multiselect("Sortie", reasons, reasons)
            outcome = f3.selectbox("Résultat", ["Tous", "Gagnants", "Perdants / nuls"])
            view = t[t["direction"].isin(dirs) & t["exit_reason"].isin(exits)]
            if outcome == "Gagnants":
                view = view[view["net_pnl"] > 0]
            elif outcome == "Perdants / nuls":
                view = view[view["net_pnl"] <= 0]
            st.dataframe(view.round(4), width="stretch", hide_index=True)
            tid = st.selectbox("Rejouer la transaction", view["trade_id"].tolist() or [None])
            if tid is not None:
                replay_trade(res, t.set_index("trade_id").loc[tid].copy(), tid)
    with tab_d:
        d = res.decisions
        if d.empty:
            empty_state("Aucun signal BUY/SELL dans ce run.")
        else:
            show = d.copy()
            show["raisons (FR)"] = show["reasons"].fillna("").map(reasons_fr)
            only = st.selectbox("Afficher", ["Toutes", "Entrées", "Refus"])
            if only == "Entrées":
                show = show[show["outcome"] == "ENTERED"]
            elif only == "Refus":
                show = show[show["outcome"] == "REJECTED"]
            st.dataframe(show, width="stretch", hide_index=True)


def replay_trade(res, trade: pd.Series, tid) -> None:
    trade["trade_id"] = tid
    dec = res.decisions.set_index("decision_id").loc[int(trade["decision_id"])]
    st.subheader(f"Transaction n° {tid} — {trade['direction']} · {trade['exit_reason']} · "
                 f"{trade['net_pnl']:+.2f} ({trade['r_multiple']:+.2f} R)")
    st.markdown(f"**Pourquoi l'entrée a été prise** — décision prise à la clôture de la bougie "
                f"{dec['signal_time']:%Y-%m-%d %H:%M} UTC, exécutée à l'ouverture de {trade['entry_time']:%H:%M} UTC.")
    feats = {k[2:]: v for k, v in dec.items() if str(k).startswith("f_")}
    st.markdown(f"- Règle de la stratégie : `{dec['strategy_reason']}`")
    st.markdown("- Valeurs connues au moment de la décision : " +
                ", ".join(f"{k} = {v:.4f}" if isinstance(v, float) else f"{k} = {v}" for k, v in feats.items()))
    st.markdown(f"- Risk Guardian : accepté · {trade['lots']} lot(s) · risque prévu {trade['planned_risk']:.2f} "
                f"(MAE {trade['mae_r']:.2f} R, MFE {trade['mfe_r']:.2f} R)")
    if trade.get("gap_during_trade"):
        st.warning("Trou de données pendant ce trade : son résultat est peu fiable.")
    try:
        ds = load_dataset(res.manifest["dataset"]["dataset_id"])
    except Exception as exc:
        st.error(f"Données sources indisponibles pour le rejeu : {exc}")
        return
    b = ds.bars
    i0 = b.index[b["timestamp"] >= trade["signal_time"]][0]
    i1 = b.index[b["timestamp"] >= trade["exit_time"]][0]
    window = b.iloc[max(0, i0 - 40): min(len(b), i1 + 15)]
    st.altair_chart(candles_chart(window, trade), width="stretch")
    side = res.manifest["dataset"].get("price_side", "bid").upper()
    st.caption(f"Ligne violette : bougie du signal (clôturée). Losanges : entrée et sortie simulées. "
               f"Bougies affichées en prix {side} (données sources) ; les exécutions utilisent BID/ASK = "
               f"{'BID' if side == 'BID' else 'MID ∓ spread/2'} (+ spread pour l'ASK) et le glissement.")


# ------------------------------------------------------------------ Risk
def risk_page() -> None:
    st.title("Risk Management")
    safety_banner()
    cat = catalog()
    cfg = default_config(cat)
    st.markdown("Le **Risk Guardian** est indépendant des stratégies et fonctionne en **fail-closed** : "
                "toute incertitude critique (contrat inconnu, données invalides, stop invalide, erreur interne) "
                "**bloque** la nouvelle opération. La taille est calculée à partir du capital, de la distance au stop "
                "et des spécifications réelles du contrat. Les stratégies de type martingale / grille sont interdites.")
    st.warning("Un stop-loss et un plafond journalier **ne garantissent pas** une perte maximale absolue : "
               "gaps et glissement peuvent exécuter au-delà du stop.")
    preset = st.radio("Profil de départ", ["Profil enregistré", "Recommandé v0.2", "Règles v0.1 (legacy, explicites)"],
                      horizontal=True)
    r = {"Profil enregistré": cfg.risk, "Recommandé v0.2": RiskConfig(), "Règles v0.1 (legacy, explicites)": LEGACY_V01_RISK}[preset]
    with st.form("risk"):
        c = st.columns(3)
        risk_pct = c[0].number_input("Risque max par opération (% du capital)", 0.01, 5.0, r.risk_per_trade_pct, 0.05)
        daily = c[1].number_input("Perte journalière max (%)", 0.05, 100.0, r.max_daily_loss_pct, 0.1)
        dd = c[2].number_input("Drawdown max — arrêt (%)", 0.1, 100.0, r.max_drawdown_pct, 0.5)
        c = st.columns(3)
        trades = c[0].number_input("Trades max par jour", 1, 100, r.max_trades_per_day)
        losses_day = c[1].number_input("Pertes max par jour (0 = sans limite)", 0, 100, r.max_losses_per_day or 0)
        consec = c[2].number_input("Pertes consécutives max (0 = sans limite)", 0, 100, r.max_consecutive_losses or 0)
        c = st.columns(3)
        scope = c[0].selectbox("Compteur de pertes consécutives", ["day", "run"], ["day", "run"].index(r.consecutive_loss_scope),
                               format_func={"day": "remis à zéro chaque jour", "run": "sur toute la simulation"}.get)
        tz = c[1].selectbox("Fuseau du « jour de trading »", ["UTC", "Europe/Paris", "Europe/Athens", "America/New_York",
                                                            "Africa/Kinshasa"],
                            ["UTC", "Europe/Paris", "Europe/Athens", "America/New_York", "Africa/Kinshasa"].index(r.day_timezone)
                            if r.day_timezone in ["UTC", "Europe/Paris", "Europe/Athens", "America/New_York",
                                                  "Africa/Kinshasa"] else 0)
        win_stop = c[2].checkbox("Arrêter la journée après le premier gain", r.stop_after_daily_win)
        c = st.columns(2)
        inc_daily = c[0].checkbox("La limite journalière inclut le risque du trade envisagé", r.daily_limit_includes_planned_risk)
        inc_dd = c[1].checkbox("La limite de drawdown inclut le risque du trade envisagé", r.drawdown_limit_includes_planned_risk)
        st.caption("Positions simultanées : 1 (le moteur v0.2 gère une position à la fois). Martingale : interdite, "
                   "non activable dans cette version.")
        saved = st.form_submit_button("Enregistrer le profil de risque", type="primary")
    if saved:
        try:
            new = RiskConfig(risk_per_trade_pct=risk_pct, max_daily_loss_pct=daily, max_drawdown_pct=dd,
                             max_trades_per_day=int(trades), max_losses_per_day=int(losses_day) or None,
                             max_consecutive_losses=int(consec) or None, consecutive_loss_scope=scope,
                             stop_after_daily_win=win_stop, daily_limit_includes_planned_risk=inc_daily,
                             drawdown_limit_includes_planned_risk=inc_dd, day_timezone=tz)
            save_risk(cat, new)
            st.success("Profil de risque enregistré ; il sera utilisé par les prochains backtests.")
        except Exception as exc:
            st.error(f"Profil refusé : {exc}")

    st.subheader("Contrat utilisé pour le dimensionnement")
    ct = cfg.contract
    problems = ct.problems(cfg.account_currency)
    if problems or not ct.currency_ok(cfg.account_currency):
        st.error("Contrat inconnu ou incompatible → **toutes les opérations seront refusées** : " +
                 "; ".join(problems or ["devise de cotation ≠ devise du compte"]))
    st.write(pd.DataFrame([ct.model_dump()]))
    st.caption("Modifiable dans **Settings**. Source : " + ct.source)

    st.subheader("Rejets du Risk Guardian")
    res = _select_run("risk_run")
    if res is None:
        empty_state("Aucun backtest enregistré.")
        return
    rej = res.metrics.get("rejection_reasons", {})
    if rej:
        st.altair_chart(reasons_chart(rej), width="stretch")
        st.dataframe(pd.DataFrame({"code": list(rej), "raison": [ALL_REASON_LABELS.get(k, k) for k in rej],
                                   "signaux": list(rej.values())}), width="stretch", hide_index=True)
    else:
        st.success("Aucun signal refusé dans ce run.")
    with st.expander("Dictionnaire des codes de refus"):
        st.dataframe(pd.Series(REJECTION_LABELS_FR, name="signification"), width="stretch")


# ------------------------------------------------------------------ Settings
def settings_page() -> None:
    st.title("Settings")
    safety_banner()
    cat = catalog()
    cfg = default_config(cat)
    with st.form("settings"):
        st.subheader("Compte simulé")
        c = st.columns(2)
        equity = c[0].number_input("Capital initial par défaut", 100.0, 10_000_000.0, float(cfg.initial_equity), 500.0)
        currency = c[1].selectbox("Devise du compte", ["USD", "EUR", "GBP"], ["USD", "EUR", "GBP"].index(cfg.account_currency)
                                  if cfg.account_currency in ["USD", "EUR", "GBP"] else 0,
                                  help="Aucune conversion de devises : si la devise de cotation diffère, le Risk Guardian refuse.")
        st.subheader("Coûts par défaut (hypothèses)")
        c = st.columns(3)
        spread = c[0].number_input("Spread fixe (prix)", 0.0, 50.0, float(cfg.costs.spread), 0.05, format="%.3f")
        slip = c[1].number_input("Glissement par exécution (prix)", 0.0, 50.0, float(cfg.costs.slippage), 0.01, format="%.3f")
        comm = c[2].number_input("Commission / lot / côté", 0.0, 100.0, float(cfg.costs.commission_per_lot_per_side), 0.5)
        st.subheader("Spécification du contrat")
        st.caption("Renseignez les valeurs RÉELLES de votre courtier. Laissez 0 si inconnu : le Risk Guardian refusera alors "
                   "toute opération (fail-closed).")
        ct = cfg.contract
        c = st.columns(3)
        symbol = c[0].text_input("Symbole", ct.symbol)
        csize = c[1].number_input("Taille du contrat (unités / lot)", 0.0, 10_000_000.0, float(ct.contract_size or 0), 1.0)
        quote = c[2].text_input("Devise de cotation", ct.quote_currency or "")
        c = st.columns(4)
        min_lot = c[0].number_input("Lot minimal", 0.0, 100.0, float(ct.min_lot or 0), 0.01)
        step = c[1].number_input("Pas de lot", 0.0, 100.0, float(ct.lot_step or 0), 0.01)
        max_lot = c[2].number_input("Lot maximal (0 = aucun)", 0.0, 10_000.0, float(ct.max_lot or 0), 1.0)
        source = c[3].text_input("Source de ces valeurs", ct.source)
        ok = st.form_submit_button("Enregistrer", type="primary")
    if ok:
        try:
            contract = ContractSpec(symbol=symbol, contract_size=csize or None, min_lot=min_lot or None,
                                    lot_step=step or None, max_lot=max_lot or None, quote_currency=quote or None,
                                    source=source)
            save_defaults(cat, cfg.model_copy(update={
                "initial_equity": equity, "account_currency": currency, "contract": contract,
                "costs": ExecutionCosts(spread=spread, slippage=slip, commission_per_lot_per_side=comm)}))
            st.success("Paramètres enregistrés.")
        except Exception as exc:
            st.error(f"Paramètres refusés : {exc}")
    if st.button("Réinitialiser le contrat à l'hypothèse XAUUSD 100 oz/lot"):
        save_defaults(cat, cfg.model_copy(update={"contract": XAUUSD_HYPOTHETICAL.model_copy()}))
        st.rerun()

    st.subheader("Système")
    st.markdown(f"- Version : **{__version__}** · moteur : `{ENGINE_VERSION}`\n"
                f"- Dossier de données : `{data_dir()}` (variable `ATO_DATA_DIR`)\n"
                f"- Dossier des stratégies : `{strategies_dir()}` (variable `ATO_STRATEGIES_DIR`)\n"
                f"- Trading réel : **{'activé' if LIVE_TRADING_ENABLED else 'désactivé (non implémenté)'}** · "
                f"compte démo : **{'activé' if DEMO_TRADING_ENABLED else 'désactivé (non implémenté)'}**\n"
                f"- Aucun identifiant de courtier n'est demandé ni stocké.")
