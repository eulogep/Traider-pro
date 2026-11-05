"""Scale-free features of a candidate signal, computed from bars CLOSED at decision time.

Row j only uses bars 0..j (the signal bar j is closed when the decision is taken at the open of j+1):
every rolling window ends at j, nothing is shifted backwards (tested: altering bars after j never
changes row j). Features are generic (price action, volatility, time, costs), so they apply to any
strategy; "aligned" features are multiplied by the signal direction (+1 BUY, −1 SELL).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..features.indicators import atr, ema

FEATURE_SET = "price-action-v1"
FEATURE_LABELS_FR = {
    "ret_5": "Élan 5 bougies (aligné, en ATR)",
    "ret_15": "Élan 15 bougies (aligné, en ATR)",
    "ret_60": "Élan 60 bougies (aligné, en ATR)",
    "ret_240": "Élan 240 bougies (aligné, en ATR)",
    "trend": "Écart EMA20 / EMA100 (aligné, en ATR)",
    "range_pos": "Position dans le range des 60 dernières bougies (alignée)",
    "body": "Corps de la bougie du signal (aligné, en ATR)",
    "vol_regime": "Volatilité actuelle / volatilité du dernier jour (log)",
    "stop_atr": "Distance du stop (en ATR)",
    "cost_r": "Coûts d'un aller-retour (en R)",
    "hour_sin": "Heure de la journée (sinus)",
    "hour_cos": "Heure de la journée (cosinus)",
}
FEATURES = list(FEATURE_LABELS_FR)


def bar_features(bars: pd.DataFrame) -> pd.DataFrame:
    """Direction-free building blocks for every bar (causal rolling windows only)."""
    close = bars["close"].astype(float)
    a = atr(bars, 14, "sma")
    out = pd.DataFrame(index=bars.index)
    out["atr"] = a
    for k in (5, 15, 60, 240):
        out[f"ret_{k}"] = (close - close.shift(k)) / a
    out["trend"] = (ema(close, 20) - ema(close, 100)) / a
    hi, lo = bars["high"].rolling(60).max(), bars["low"].rolling(60).min()
    out["range_pos"] = ((close - lo) / (hi - lo)).where(hi > lo)
    out["body"] = (close - bars["open"]) / a
    out["vol_regime"] = np.log(a / a.rolling(1440, min_periods=240).mean())
    minutes = bars["timestamp"].dt.hour * 60 + bars["timestamp"].dt.minute
    out["hour_sin"] = np.sin(2 * np.pi * minutes / 1440)
    out["hour_cos"] = np.cos(2 * np.pi * minutes / 1440)
    return out


def signal_features(bars: pd.DataFrame, labels: pd.DataFrame, spread: float, slippage: float,
                    commission_per_lot_per_side: float, contract_size: float) -> pd.DataFrame:
    """One row per labelled signal (same order as ``labels``); NaN rows (warm-up) are kept, callers drop them."""
    base = bar_features(bars.reset_index(drop=True))
    rows = base.iloc[labels["sig_idx"].to_numpy()].reset_index(drop=True)
    d = labels["direction"].to_numpy(float)
    X = pd.DataFrame(index=labels.index)
    for col in ("ret_5", "ret_15", "ret_60", "ret_240", "trend", "body"):
        X[col] = rows[col].to_numpy() * d
    rp = rows["range_pos"].to_numpy()
    X["range_pos"] = np.where(d > 0, rp, 1 - rp)
    X["vol_regime"] = rows["vol_regime"].to_numpy()
    sl = labels["sl_distance"].to_numpy(float)
    X["stop_atr"] = sl / rows["atr"].to_numpy()
    risk_per_lot = (sl + slippage) * contract_size + 2 * commission_per_lot_per_side
    X["cost_r"] = ((spread + 2 * slippage) * contract_size + 2 * commission_per_lot_per_side) / risk_per_lot
    X["hour_sin"], X["hour_cos"] = rows["hour_sin"].to_numpy(), rows["hour_cos"].to_numpy()
    return X[FEATURES].replace([np.inf, -np.inf], np.nan)
