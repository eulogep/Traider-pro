"""Baseline from v0.1: EMA trend filter + 3-candle sequence. ILLUSTRATIVE ONLY.

It is not the pilot trader's strategy and no statistical edge is assumed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..features.indicators import atr, candle_color, ema
from .base import Strategy


class EmaTrend3Bars(Strategy):
    implementation = "ema_trend_3bars"
    feature_columns = ["ema_fast", "ema_slow", "atr", "color", "color_1", "color_2"]

    def __init__(self, spec, params):
        super().__init__(spec, params)
        if params["ema_fast"] >= params["ema_slow"]:
            raise ValueError("ema_fast doit être strictement inférieure à ema_slow")

    @property
    def warmup_bars(self) -> int:
        p = self.params
        return int(max(p["warmup_bars"], p["ema_slow"], p["atr_period"]))

    def compute(self, bars: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        out = pd.DataFrame(index=bars.index)
        close = bars["close"]
        out["ema_fast"] = ema(close, p["ema_fast"])
        out["ema_slow"] = ema(close, p["ema_slow"])
        out["atr"] = atr(bars, p["atr_period"], p["atr_method"])
        col = candle_color(bars)
        out["color"], out["color_1"], out["color_2"] = col, col.shift(1, fill_value=0), col.shift(2, fill_value=0)
        bull_pattern = (out["color_2"] == -1) & (out["color_1"] == 1) & (out["color"] == 1)
        bear_pattern = (out["color_2"] == 1) & (out["color_1"] == -1) & (out["color"] == -1)
        up = (close > out["ema_fast"]) & (out["ema_fast"] > out["ema_slow"])
        down = (close < out["ema_fast"]) & (out["ema_fast"] < out["ema_slow"])
        warm = np.arange(len(bars)) < self.warmup_bars
        atr_ok = np.isfinite(out["atr"]) & (out["atr"] > 0)
        buy = bull_pattern & up & ~warm & atr_ok
        sell = bear_pattern & down & ~warm & atr_ok
        out["signal"] = np.select([buy, sell], [1, -1], default=0).astype(int)
        out["reason"] = np.select(
            [warm, buy, sell, (bull_pattern | bear_pattern) & ~atr_ok,
             bull_pattern & ~up, bear_pattern & ~down],
            ["WAIT:warm-up indicateurs", "BUY:R-V-V + close>EMA rapide>EMA lente",
             "SELL:V-R-R + close<EMA rapide<EMA lente", "WAIT:ATR indisponible",
             "WAIT:motif haussier sans tendance haussière", "WAIT:motif baissier sans tendance baissière"],
            default="WAIT:pas de motif 3 bougies",
        )
        dist = out["atr"] * p["sl_atr_mult"]
        out["sl_distance"] = np.where(out["signal"] != 0, dist, np.nan)
        out["tp_distance"] = np.where(out["signal"] != 0, dist * p["rr"], np.nan)
        return out

    def describe_decision(self, row: pd.Series) -> str:
        p = self.params
        names = {1: "verte", -1: "rouge", 0: "doji"}
        seq = " → ".join(names[int(row[c])] for c in ("color_2", "color_1", "color"))
        return (f"{row['reason']} | bougies {seq} | EMA{p['ema_fast']}={row['ema_fast']:.2f}, "
                f"EMA{p['ema_slow']}={row['ema_slow']:.2f}, ATR{p['atr_period']}({p['atr_method']})={row['atr']:.3f} | "
                f"SL à {p['sl_atr_mult']}×ATR, TP à {p['rr']}R")
