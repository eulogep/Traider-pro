"""Dashboard, Market Data and Strategy Lab pages."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from ..data import import_csv, read_source, synthetic_dataset
from ..safety import DataKind
from ..services import compare_variants, default_config
from .common import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    apply_session_overrides,
    catalog,
    data_kind_warning,
    downsample,
    empty_state,
    fmt_money,
    fmt_num,
    fmt_pct,
    kind_badge,
    load_dataset,
    safety_banner,
    strategies,
)

COMMON_TZ = ["UTC", "Europe/Athens", "Europe/London", "Europe/Paris", "America/New_York", "Asia/Tokyo",
             "Africa/Kinshasa", "Africa/Lagos", "Asia/Dubai"]


# ------------------------------------------------------------------ Dashboard
def dashboard_page() -> None:
    st.title("Tableau de bord")
    safety_banner()
    cat, strats = catalog(), strategies()
    datasets, runs = cat.list_datasets(), cat.list_runs()

    c1, c2, c3, c4 = st.columns(4)
    hist = int((datasets["kind"] == "historical").sum()) if len(datasets) else 0
    synth = int((datasets["kind"] == "synthetic").sum()) if len(datasets) else 0
    c1.metric("Jeux de données historiques", hist)
    c2.metric("Jeux synthétiques (démo)", synth)
    c3.metric("Stratégies exécutables", len(strats.runnable()), help="Actives, implémentées, droits clarifiés")
    c4.metric("Backtests enregistrés", len(runs))

    if not len(datasets) or not len(runs):
        st.subheader("Démarrer")
        st.markdown(
            "1. **Market Data** — importez un CSV historique (ou générez la démo synthétique).\n"
            "2. **Strategy Lab** — choisissez la stratégie de référence et ajustez ses paramètres autorisés.\n"
            "3. **Risk Management** — vérifiez les limites de risque (mode fail-closed).\n"
            "4. **Backtesting** — lancez la simulation, puis analysez-la dans **Trade Journal**.")
    if runs.empty:
        empty_state("Aucun backtest enregistré pour l'instant.")
        return

    last = cat.load_run(runs.iloc[0]["run_id"])
    m, man = last.metrics, last.manifest
    st.subheader("Dernier backtest")
    st.markdown(kind_badge(man["data_kind"]) + f'<span class="ato-muted">{man["strategy"]["name"]} · v'
                f'{man["strategy"]["version"]} · données {man["dataset"]["name"]} · run {man["run_id"]}</span>',
                unsafe_allow_html=True)
    k = st.columns(5)
    k[0].metric("P&L net simulé", fmt_money(m["net_pnl"]))
    k[1].metric("Trades", m["trades"])
    k[2].metric("Win rate", fmt_pct(m["win_rate_pct"], 1))
    k[3].metric("Profit factor", fmt_num(m["profit_factor"]))
    k[4].metric("Drawdown max (MTM)", fmt_pct(m["max_dd_mtm_pct"]))
    if not m["sample_sufficient"]:
        st.warning(m["sample_note"])

    st.subheader("Comparaison des backtests (par stratégie et type de données)")
    st.caption("Ne comparez que des runs sur les MÊMES données et les MÊMES hypothèses de coûts. "
               "Les résultats synthétiques ne sont jamais comparables à des résultats historiques.")
    view = runs.rename(columns={"created_at": "date", "strategy_key": "stratégie", "data_kind": "données",
                                "net_pnl": "P&L net", "win_rate_pct": "win rate %", "max_dd_mtm_pct": "DD max MTM %"})
    st.dataframe(view.drop(columns=["result_hash"]), width="stretch", hide_index=True)
    summary = runs.groupby(["strategy_key", "data_kind", "dataset_id"]).agg(
        runs=("run_id", "count"), pnl_moyen=("net_pnl", "mean"), trades_moyens=("trades", "mean")).reset_index()
    st.dataframe(summary, width="stretch", hide_index=True)


# ------------------------------------------------------------------ Market data
def market_data_page() -> None:
    st.title("Market Data")
    safety_banner()
    cat = catalog()
    tab_import, tab_list = st.tabs(["Importer", "Jeux de données & qualité"])

    with tab_import:
        st.markdown("Formats acceptés : CSV `timestamp,open,high,low,close` (colonnes optionnelles `tick_volume`, "
                    "`spread`) ou **export MetaTrader 5** (`<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> …`). "
                    "Le fichier est **refusé entièrement** en cas d'erreur ; rien n'est corrigé, trié ou comblé.")
        with st.form("import"):
            up = st.file_uploader("Fichier CSV", type=["csv", "txt"])
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Nom du jeu de données", "XAUUSD M1 — broker")
            symbol = c2.text_input("Symbole", "XAUUSD")
            source = c3.text_input("Source (broker / fournisseur)", "", placeholder="ex. compte démo MT5 de …")
            c4, c5, c6 = st.columns(3)
            side = c4.selectbox("Prix fournis", ["bid", "mid"], help="MT5 exporte des prix BID.")
            tz_mode = c5.selectbox("Fuseau des horodatages", ["Décalage UTC explicite dans le fichier",
                                                              "Déclarer le fuseau de la source"])
            tz = c6.selectbox("Fuseau de la source (si déclaré)", COMMON_TZ,
                              help="Beaucoup de serveurs MT5 utilisent l'heure d'Europe/Athens (UTC+2/+3).")
            c7, c8 = st.columns(2)
            tf = c7.selectbox("Unité de temps attendue", ["(détecter)", "M1", "M5", "M15", "M30", "H1", "H4", "D1"])
            kind_label = c8.selectbox("Nature des données", ["Historique réel (broker / fournisseur)",
                                                             "Synthétique / démonstration (fausses cotations)"])
            notes = st.text_area("Notes (conditions du compte, période, remarques)", "")
            submitted = st.form_submit_button("Valider et enregistrer", type="primary")
        if submitted:
            if up is None:
                st.error("Choisissez un fichier.")
            elif not source.strip():
                st.error("Indiquez la source des données (traçabilité obligatoire).")
            elif kind_label.startswith("Historique") and "synth" in up.name.lower():
                st.error("Ce fichier est nommé comme des données synthétiques : déclarez-le « Synthétique / "
                         "démonstration ». Des prix fictifs ne doivent jamais être étiquetés historiques.")
            else:
                raw = read_source(up)
                with st.spinner("Validation…"):
                    rep, ds = import_csv(raw, name=name, symbol=symbol, source_label=source, price_side=side,
                                         source_timezone=tz if tz_mode.startswith("Déclarer") else None,
                                         expected_timeframe=None if tf.startswith("(") else tf, notes=notes,
                                         kind=DataKind.HISTORICAL if kind_label.startswith("Historique")
                                         else DataKind.SYNTHETIC)
                show_report(rep.as_dict(), rep.gaps)
                if ds is not None:
                    cat.save_dataset(ds, raw)
                    st.session_state["selected_dataset"] = ds.meta.dataset_id
                    st.success(f"Jeu de données enregistré : `{ds.meta.dataset_id}` ({ds.meta.rows} bougies).")
                else:
                    st.error("Fichier refusé : corrigez la source et réimportez. Aucune donnée n'a été enregistrée.")

        st.divider()
        st.markdown("**Données de démonstration** — prix **entièrement fictifs**, pour vérifier le logiciel.")
        c1, c2, c3 = st.columns([1, 1, 2])
        seed = c1.number_input("Graine", 0, 10_000, 42)
        days = c2.number_input("Jours calendaires", 3, 120, 10)
        if c3.button("Générer le jeu synthétique"):
            ds = synthetic_dataset(seed=int(seed), days=int(days))
            cat.save_dataset(ds)
            st.session_state["selected_dataset"] = ds.meta.dataset_id
            st.success(f"Jeu synthétique enregistré : `{ds.meta.dataset_id}`.")

    with tab_list:
        datasets = cat.list_datasets()
        if datasets.empty:
            empty_state("Aucun jeu de données.", "Importez un CSV ou générez la démo dans l'onglet « Importer ».")
            return
        st.dataframe(datasets, width="stretch", hide_index=True)
        ids = datasets["dataset_id"].tolist()
        labels = dict(zip(ids, datasets["name"] + " · " + datasets["kind"] + " · " + datasets["dataset_id"], strict=False))
        cur = st.session_state.get("selected_dataset")
        sel = st.selectbox("Examiner", ids, index=ids.index(cur) if cur in ids else 0, format_func=labels.get)
        st.session_state["selected_dataset"] = sel
        meta = cat.dataset_meta(sel)
        st.markdown(kind_badge(meta.kind.value), unsafe_allow_html=True)
        if meta.kind == DataKind.SYNTHETIC:
            st.error("Données synthétiques : fausses cotations, uniquement pour tester le logiciel.")
        c = st.columns(4)
        c[0].metric("Bougies", f"{meta.rows:,}".replace(",", " "))
        c[1].metric("Unité de temps", meta.timeframe)
        c[2].metric("Début (UTC)", meta.start[:16].replace("T", " "))
        c[3].metric("Fin (UTC)", meta.end[:16].replace("T", " "))
        st.caption(f"Source : {meta.source} · fuseau : {meta.source_timezone} · prix : {meta.price_side.upper()} · "
                   f"empreinte : {meta.dataset_id}" + (f" · SHA-256 du fichier brut : {meta.raw_sha256[:16]}…"
                                                      if meta.raw_sha256 else ""))
        try:
            ds = load_dataset(sel)
        except Exception as exc:
            st.error(f"Impossible de charger ce jeu de données : {exc}")
            return
        gaps = pd.DataFrame()
        if meta.quality.get("gaps_count"):
            from ..data import validate_bars
            gaps = validate_bars(ds.bars)[0].gaps
        show_report(meta.quality, gaps)
        st.subheader("Clôtures")
        line = downsample(ds.bars[["timestamp", "close"]], 4000)
        st.altair_chart(alt.Chart(line).mark_line(strokeWidth=1).encode(
            x=alt.X("timestamp:T", title=None), y=alt.Y("close:Q", scale=alt.Scale(zero=False), title="Clôture")
        ).properties(height=260), width="stretch")
        with st.expander("Aperçu des premières bougies"):
            st.dataframe(ds.bars.head(200), width="stretch", hide_index=True)
        with st.expander("Retirer ce jeu de l'index"):
            st.caption("Les fichiers bruts et validés restent sur disque (aucune suppression destructive).")
            if st.button("Retirer de l'index", key="del_ds"):
                cat.delete_dataset(sel)
                st.session_state.pop("selected_dataset", None)
                st.rerun()


def show_report(q: dict, gaps: pd.DataFrame) -> None:
    errors = [i for i in q["issues"] if i["severity"] == "error"]
    warns = [i for i in q["issues"] if i["severity"] == "warning"]
    infos = [i for i in q["issues"] if i["severity"] == "info"]
    st.subheader("Rapport de qualité")
    c = st.columns(4)
    c[0].metric("Statut", "VALIDE" if q["ok"] else "REFUSÉ")
    c[1].metric("Lignes lues", q["rows_raw"])
    c[2].metric("Erreurs", len(errors))
    c[3].metric("Avertissements", len(warns))
    for i in errors:
        st.error(f"**{i['code']}** — {i['message']}" + (f" Lignes : {i['rows']}" if i["rows"] else ""))
    for i in warns:
        st.warning(f"**{i['code']}** — {i['message']}" + (f" (exemples : {i['rows'][:10]})" if i["rows"] else ""))
    for i in infos:
        st.caption(f"ℹ️ {i['code']} — {i['message']}")
    if q.get("stats"):
        st.json(q["stats"], expanded=False)
    if gaps is not None and len(gaps):
        with st.expander(f"Trous dans la chronologie ({len(gaps)}) — jamais comblés"):
            st.dataframe(gaps, width="stretch", hide_index=True)


# ------------------------------------------------------------------ Strategy lab
def strategy_lab_page() -> None:
    st.title("Strategy Lab")
    safety_banner()
    strats = strategies()
    if strats.errors:
        for f, err in strats.errors.items():
            st.error(f"Fichier de stratégie invalide `{f}` : {err}")
    if not strats.specs:
        empty_state("Aucune stratégie trouvée dans le dossier `strategies/`.")
        return
    keys = list(strats.specs)
    groups = {k: CATEGORY_LABELS[strats.specs[k].category] for k in keys}
    cur = st.session_state.get("selected_strategy")
    key = st.selectbox("Stratégie", keys, index=keys.index(cur) if cur in keys else 0,
                       format_func=lambda k: f"[{groups[k]}] {strats.specs[k].name} — v{strats.specs[k].version}")
    st.session_state["selected_strategy"] = key
    spec = strats.specs[key]

    badges = (f'<span class="ato-badge">{CATEGORY_LABELS[spec.category]}</span>'
              f'<span class="ato-badge">statut : {STATUS_LABELS[spec.status]}</span>'
              f'<span class="ato-badge">v{spec.version}</span>')
    if spec.illustrative:
        badges += '<span class="ato-badge ato-synthetic">ILLUSTRATIVE — aucun avantage supposé</span>'
    st.markdown(badges, unsafe_allow_html=True)
    st.write(spec.description)
    problems = spec.runnable_problems()
    if problems:
        st.warning("Non exécutable : " + " ; ".join(problems))

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Propriétaire** : {spec.owner}  \n**Droits** : {spec.usage_rights}  \n"
                f"**Implémentation** : `{spec.implementation or '—'}`")
    c2.markdown(f"**Marché** : {spec.market.get('symbol')}  \n**Exécution** : {spec.timeframes.execution}  \n"
                f"**Contexte** : {', '.join(spec.timeframes.context) or '—'}")
    th = spec.trading_hours
    days = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
    c3.markdown(f"**Horaires** ({th.timezone}) : {', '.join(th.sessions)}  \n"
                f"**Jours** : {', '.join(days[d] for d in th.weekdays)}  \n**Gestion de position** : {spec.position_scaling}")

    st.subheader("Règles déclarées")
    rc = st.columns(5)
    for col, (title, items) in zip(rc, [("BUY", spec.rules.buy), ("SELL", spec.rules.sell), ("WAIT", spec.rules.wait),
                                        ("Invalidation", spec.rules.invalidation), ("Sortie", spec.rules.exit)], strict=False):
        col.markdown(f"**{title}**")
        for it in items or ["—"]:
            col.markdown(f"- {it}")
    if spec.indicators:
        st.caption("Indicateurs : " + " · ".join(
            f"{i.name}({', '.join(f'{k}={v}' for k, v in i.params.items())}){' ' + i.timeframe if i.timeframe else ''}"
            for i in spec.indicators))
    if spec.open_questions:
        with st.expander(f"Questions ouvertes à valider avec le trader ({len(spec.open_questions)})", expanded=True):
            for q in spec.open_questions:
                st.markdown(f"- {q}")

    if problems or not spec.params:
        return
    st.subheader("Paramètres autorisés")
    st.caption("Les bornes viennent du fichier de spécification ; toute valeur hors bornes est refusée.")
    overrides = dict(st.session_state.get("param_overrides", {}).get(key, {}))
    new = {}
    cols = st.columns(3)
    for n, (pname, p) in enumerate(spec.params.items()):
        col = cols[n % 3]
        val = overrides.get(pname, p.default)
        if not p.editable:
            col.text_input(pname, str(val), disabled=True, help=p.description)
            continue
        if p.type == "choice":
            new[pname] = col.selectbox(pname, p.choices, index=p.choices.index(val), help=p.description)
        elif p.type == "bool":
            new[pname] = col.checkbox(pname, bool(val), help=p.description)
        elif p.type == "int":
            new[pname] = col.number_input(pname, int(p.min), int(p.max), int(val), step=1, help=p.description)
        else:
            new[pname] = col.number_input(pname, float(p.min), float(p.max), float(val), step=0.1, help=p.description)
    st.markdown("**Horaires de trading** (enregistrés dans la configuration du run)")
    hc = st.columns(3)
    hours_ov = st.session_state.get("hours_overrides", {}).get(key, th.model_dump())
    sess = hc[0].text_input("Sessions (HH:MM-HH:MM, séparées par des virgules)", ", ".join(hours_ov["sessions"]))
    tz = hc[1].selectbox("Fuseau des horaires", COMMON_TZ, index=COMMON_TZ.index(hours_ov["timezone"])
                         if hours_ov["timezone"] in COMMON_TZ else 0)
    wd = hc[2].multiselect("Jours", list(range(7)), hours_ov["weekdays"], format_func=lambda d: days[d])
    if st.button("Utiliser ces paramètres pour les prochains backtests", type="primary"):
        try:
            spec.resolve_params(new)
            from ..strategies import TradingHours, build_strategy
            build_strategy(spec, new)
            hours = TradingHours(timezone=tz, sessions=[s.strip() for s in sess.split(",") if s.strip()], weekdays=wd)
        except Exception as exc:
            st.error(f"Paramètres refusés : {exc}")
        else:
            st.session_state.setdefault("param_overrides", {})[key] = new
            st.session_state.setdefault("hours_overrides", {})[key] = hours.model_dump()
            st.success("Paramètres enregistrés pour cette session (ils seront inscrits dans le manifeste de chaque run).")

    st.subheader("Comparer des variantes")
    st.caption("Mêmes données, mêmes coûts, même profil de risque. Les résultats in-sample et hors échantillon "
               "sont séparés chronologiquement (70 / 30). **Choisir la meilleure variante d'après la colonne "
               "hors échantillon la transforme en données d'entraînement** : gardez une période de test vierge.")
    cat = catalog()
    datasets = cat.list_datasets()
    if datasets.empty:
        empty_state("Importez d'abord un jeu de données.")
        return
    numeric = [n for n, p in spec.params.items() if p.type in ("int", "float", "choice") and p.editable]
    with st.form("variants"):
        c1, c2, c3 = st.columns(3)
        ds_id = c1.selectbox("Données", datasets["dataset_id"].tolist(),
                             format_func=lambda i: datasets.set_index("dataset_id").loc[i, "name"])
        pname = c2.selectbox("Paramètre à faire varier", numeric)
        values_txt = c3.text_input("Valeurs (séparées par des virgules)", "1.0, 1.5, 2.0")
        go = st.form_submit_button("Comparer")
    if go:
        p = spec.params[pname]
        try:
            values = [p.coerce(v.strip() if p.type == "choice" else float(v)) for v in values_txt.split(",") if v.strip()]
            if not values or len(values) > 6:
                raise ValueError("entre 1 et 6 valeurs")
        except Exception as exc:
            st.error(f"Valeurs invalides pour {pname} : {exc}")
            return
        base = apply_session_overrides(default_config(cat), key).model_copy(update={"strategy_params": new})
        with st.spinner("Simulations…"):
            try:
                table = compare_variants(cat, ds_id, spec, base, pname, values)
            except Exception as exc:
                st.error(f"Comparaison impossible : {exc}")
                return
        data_kind_warning(cat.dataset_meta(ds_id).kind.value)
        st.dataframe(table, width="stretch", hide_index=True)
