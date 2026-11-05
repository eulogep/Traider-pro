"""Shared Streamlit helpers: cached resources, formatting, banners, charts."""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from ..paths import data_dir
from ..risk.guardian import REJECTION_LABELS_FR
from ..safety import DATA_KIND_LABELS_FR, LIVE_TRADING_ENABLED, DataKind
from ..storage import LabCatalog
from ..strategies import load_catalog

ENGINE_REASON_LABELS_FR = {
    "OUTSIDE_TEST_WINDOW": "Avant le début de la période testée",
    "EXITED_THIS_BAR": "Une position vient de se fermer dans cette bougie",
    "NON_TRADING_DAY": "Jour non tradé par la stratégie",
    "OUTSIDE_SESSION": "Hors des horaires de trading",
    "INVALID_PRICES": "Prix de stop / objectif invalides",
}
ALL_REASON_LABELS = {**REJECTION_LABELS_FR, **ENGINE_REASON_LABELS_FR}
CATEGORY_LABELS = {"baseline": "Référence (baseline)", "pilot_trader": "Trader pilote", "third_party": "Tiers"}
STATUS_LABELS = {"draft": "brouillon", "active": "active", "archived": "archivée"}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1350px;}
div[data-testid="stMetric"] {background: var(--secondary-background-color); border-radius: 10px;
  padding: 10px 14px; border: 1px solid rgba(128,128,128,.18);}
div[data-testid="stMetricLabel"] p {font-size: .82rem; opacity: .8;}
.ato-badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:600;
  margin-right:6px; border:1px solid rgba(128,128,128,.35);}
.ato-synthetic {background:#fde2e1; color:#8a1c14; border-color:#f3b0ab;}
.ato-historical {background:#e1effd; color:#0d4a87; border-color:#a9cdf2;}
.ato-sim {background:#e6f4ea; color:#1e5e34; border-color:#a8d5b5;}
.ato-muted {opacity:.75; font-size:.86rem;}
</style>
"""


@st.cache_resource
def get_catalog(root: str) -> LabCatalog:
    return LabCatalog(root)


def catalog() -> LabCatalog:
    return get_catalog(str(data_dir()))


def strategies():
    return load_catalog()  # cheap; re-read so YAML edits are picked up


@st.cache_resource(max_entries=8)
def _load_dataset(root: str, dataset_id: str):
    return LabCatalog(root).load_dataset(dataset_id)


def load_dataset(dataset_id: str):
    return _load_dataset(str(data_dir()), dataset_id)


def setup_page() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def safety_banner() -> None:
    assert not LIVE_TRADING_ENABLED
    st.markdown('<span class="ato-badge ato-sim">MODE SIMULATION</span>'
                '<span class="ato-muted">Aucun ordre n\'est envoyé à un courtier · trading réel désactivé · '
                'aucun identifiant requis</span>', unsafe_allow_html=True)


def kind_badge(kind: str) -> str:
    k = DataKind(kind)
    css = "ato-synthetic" if k == DataKind.SYNTHETIC else "ato-historical"
    return f'<span class="ato-badge {css}">{DATA_KIND_LABELS_FR[k]}</span>'


def data_kind_warning(kind: str) -> None:
    if kind == DataKind.SYNTHETIC.value:
        st.error("**Données synthétiques (fausses cotations).** Ces résultats testent le logiciel ; "
                 "ils ne disent rien du marché réel et ne doivent jamais être présentés comme une performance.")
    elif kind == DataKind.HISTORICAL.value:
        st.info("**Données historiques importées.** Simulation sur bougies OHLC avec coûts fixes hypothétiques : "
                "ce n'est pas une exécution réelle et cela ne garantit aucun résultat futur.")


def fmt_money(v, cur="USD") -> str:
    return "indisponible" if v is None else f"{v:,.2f} {cur}".replace(",", " ")


def fmt_pct(v, digits=2) -> str:
    return "indisponible" if v is None else f"{v:.{digits}f} %"


def fmt_num(v, digits=2) -> str:
    return "indisponible" if v is None else f"{v:.{digits}f}"


def reasons_fr(codes: str) -> str:
    if not isinstance(codes, str) or not codes:
        return ""
    return " · ".join(ALL_REASON_LABELS.get(c, c) for c in codes.split(";"))


def empty_state(message: str, hint: str | None = None) -> None:
    st.info(message + (f"\n\n{hint}" if hint else ""))


def downsample(df: pd.DataFrame, max_points: int = 3000) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    step = int(np.ceil(len(df) / max_points))
    return pd.concat([df.iloc[::step], df.iloc[[-1]]]).drop_duplicates()


def equity_chart(equity: pd.DataFrame, initial: float) -> alt.Chart:
    e = downsample(equity)[["timestamp", "closed_equity", "mtm_equity"]].melt(
        "timestamp", var_name="série", value_name="equity")
    e["série"] = e["série"].map({"closed_equity": "Capital clôturé", "mtm_equity": "Mark-to-market (clôtures)"})
    base = alt.Chart(e).mark_line(strokeWidth=1.6).encode(
        x=alt.X("timestamp:T", title=None),
        y=alt.Y("equity:Q", title="Capital", scale=alt.Scale(zero=False)),
        color=alt.Color("série:N", title=None, scale=alt.Scale(range=["#2563eb", "#94a3b8"]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("timestamp:T", format="%Y-%m-%d %H:%M"), "série:N", alt.Tooltip("equity:Q", format=",.2f")])
    rule = alt.Chart(pd.DataFrame({"y": [initial]})).mark_rule(strokeDash=[4, 4], color="#64748b").encode(y="y:Q")
    return (base + rule).properties(height=300)


def drawdown_chart(equity: pd.DataFrame, initial: float) -> alt.Chart:
    e = downsample(equity)[["timestamp", "mtm_equity"]].copy()
    peak = np.maximum.accumulate(np.r_[initial, e["mtm_equity"].to_numpy()])[1:]
    e["drawdown_pct"] = (e["mtm_equity"] - peak) / peak * 100
    return alt.Chart(e).mark_area(color="#dc2626", opacity=0.35, line={"color": "#dc2626"}).encode(
        x=alt.X("timestamp:T", title=None), y=alt.Y("drawdown_pct:Q", title="Drawdown MTM (%)"),
        tooltip=[alt.Tooltip("timestamp:T", format="%Y-%m-%d %H:%M"), alt.Tooltip("drawdown_pct:Q", format=".2f")],
    ).properties(height=160)


def pnl_histogram(trades: pd.DataFrame) -> alt.Chart:
    t = trades.assign(résultat=np.where(trades["net_pnl"] > 0, "Gain", "Perte / nul"))
    return alt.Chart(t).mark_bar().encode(
        x=alt.X("r_multiple:Q", bin=alt.Bin(maxbins=30), title="Résultat net (multiples de R)"),
        y=alt.Y("count():Q", title="Trades"),
        color=alt.Color("résultat:N", scale=alt.Scale(domain=["Gain", "Perte / nul"], range=["#16a34a", "#dc2626"]),
                        legend=alt.Legend(orient="top", title=None)),
    ).properties(height=240)


def period_chart(df: pd.DataFrame) -> alt.Chart:
    d = df.assign(signe=np.where(df["net_pnl"] >= 0, "positif", "négatif"))
    return alt.Chart(d).mark_bar().encode(
        x=alt.X("period:N", title=None, sort=None), y=alt.Y("net_pnl:Q", title="P&L net"),
        color=alt.Color("signe:N", scale=alt.Scale(domain=["positif", "négatif"], range=["#16a34a", "#dc2626"]),
                        legend=None),
        tooltip=["period:N", "trades:Q", alt.Tooltip("net_pnl:Q", format=",.2f"), alt.Tooltip("win_rate_pct:Q", format=".1f")],
    ).properties(height=240)


def reasons_chart(counts: dict) -> alt.Chart:
    d = pd.DataFrame({"raison": [ALL_REASON_LABELS.get(k, k) for k in counts], "nombre": list(counts.values())})
    return alt.Chart(d).mark_bar(color="#f59e0b").encode(
        x=alt.X("nombre:Q", title="Signaux refusés"), y=alt.Y("raison:N", sort="-x", title=None),
        tooltip=["raison:N", "nombre:Q"]).properties(height=max(120, 28 * len(d)))


def candles_chart(bars: pd.DataFrame, trade: pd.Series | None = None) -> alt.Chart:
    b = bars.copy()
    b["sens"] = np.where(b["close"] >= b["open"], "hausse", "baisse")
    color = alt.Color("sens:N", scale=alt.Scale(domain=["hausse", "baisse"], range=["#16a34a", "#dc2626"]), legend=None)
    x = alt.X("timestamp:T", title=None)
    wick = alt.Chart(b).mark_rule().encode(x=x, y=alt.Y("low:Q", scale=alt.Scale(zero=False), title="Prix (BID)"),
                                           y2="high:Q", color=color)
    body = alt.Chart(b).mark_bar(size=5).encode(
        x=x, y="open:Q", y2="close:Q", color=color,
        tooltip=[alt.Tooltip("timestamp:T", format="%Y-%m-%d %H:%M"), "open:Q", "high:Q", "low:Q", "close:Q"])
    layers = [wick, body]
    if trade is not None:
        lines = pd.DataFrame({"niveau": ["Entrée", "Stop-loss", "Take-profit"],
                              "prix": [trade["entry_price"], trade["stop_loss"], trade.get("take_profit")]}).dropna()
        layers.append(alt.Chart(lines).mark_rule(strokeDash=[5, 3]).encode(
            y="prix:Q", color=alt.Color("niveau:N", scale=alt.Scale(domain=["Entrée", "Stop-loss", "Take-profit"],
                                                                    range=["#2563eb", "#dc2626", "#16a34a"]),
                                        legend=alt.Legend(orient="top", title=None))))
        pts = pd.DataFrame({"timestamp": [trade["entry_time"], trade["exit_time"]],
                            "prix": [trade["entry_price"], trade["exit_price"]], "point": ["entrée", "sortie"]})
        layers.append(alt.Chart(pts).mark_point(size=120, filled=True, color="#111827", shape="diamond").encode(
            x="timestamp:T", y="prix:Q", tooltip=["point:N", "prix:Q"]))
        sig = pd.DataFrame({"timestamp": [trade["signal_time"]]})
        layers.append(alt.Chart(sig).mark_rule(color="#7c3aed", strokeDash=[2, 2]).encode(x="timestamp:T"))
    return alt.layer(*layers).properties(height=360)


def runs_with_labels(cat: LabCatalog) -> pd.DataFrame:
    runs = cat.list_runs()
    if runs.empty:
        return runs
    runs["libellé"] = (runs["created_at"].str.slice(0, 16).str.replace("T", " ") + " · " + runs["strategy_key"]
                       + " · " + runs["data_kind"] + " · " + runs["run_id"])
    return runs


def apply_session_overrides(config, spec_key: str):
    """Strategy params and trading hours chosen in Strategy Lab (this browser session)."""
    from ..strategies import TradingHours
    params = st.session_state.get("param_overrides", {}).get(spec_key, {})
    hours = st.session_state.get("hours_overrides", {}).get(spec_key)
    return config.model_copy(update={"strategy_params": dict(params),
                                     "trading_hours": TradingHours.model_validate(hours) if hours else None})
