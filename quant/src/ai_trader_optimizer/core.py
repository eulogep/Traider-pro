"""Reproducible, offline, bar-by-bar strategy tester.

WARNING: Research approximation only. Not a live trading engine or a validated
prediction system. Inputs are BID OHLC bars, in USD/oz for XAUUSD, timezone UTC.
Ask/spread, commissions and slippage are user-controlled *assumptions*.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal, ROUND_FLOOR
import numpy as np
import pandas as pd

REQUIRED = ("timestamp", "open", "high", "low", "close")


@dataclass(frozen=True)
class TestConfig:
    initial_equity: float = 10_000.0  # USD account only
    risk_per_trade_pct: float = 0.25   # % equity, not % underlying
    max_daily_loss_pct: float = 1.0
    max_trades_per_day: int = 2
    rr: float = 1.5
    sl_atr_mult: float = 1.5
    spread_usd_per_oz: float = 0.30
    slippage_usd_per_oz: float = 0.05
    commission_usd_per_lot_per_side: float = 3.0
    contract_oz_per_lot: float = 100.0
    min_lot: float = 0.01
    lot_step: float = 0.01
    session_start_utc: str = "12:00"
    session_end_utc: str = "17:00"

    def __post_init__(self):
        if not (self.initial_equity > 0 and 0 < self.risk_per_trade_pct <= 1 and
                0 < self.max_daily_loss_pct <= 5 and 0 < self.max_trades_per_day <= 10 and
                0 < self.rr <= 10 and 0 < self.sl_atr_mult <= 10 and
                self.spread_usd_per_oz >= 0 and self.slippage_usd_per_oz >= 0 and
                self.commission_usd_per_lot_per_side >= 0 and self.contract_oz_per_lot > 0 and
                self.min_lot > 0 and self.lot_step > 0):
            raise ValueError("Invalid backtesting/risk configuration")
        for value in (self.session_start_utc, self.session_end_utc):
            time.fromisoformat(value)


def load_m1_csv(source) -> pd.DataFrame:
    """Required CSV: timestamp (ISO UTC, WITH offset), open/high/low/close BID.

    Duplicate, disordered timestamps, nonpositive prices and implausible OHLC
    reject the entire dataset rather than silently fixing it.
    """
    raw = pd.read_csv(source)
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    df = raw[list(REQUIRED)].copy()
    if len(df) < 120:
        raise ValueError("At least 120 completed M1 candles required")
    # Require an explicit timezone: do not silently assume broker-local time is UTC.
    if not raw["timestamp"].astype(str).str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).all():
        raise ValueError("All timestamps must contain an explicit UTC offset or Z")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    if df["timestamp"].isna().any() or df["timestamp"].duplicated().any():
        raise ValueError("Missing/duplicated timestamps")
    if not df["timestamp"].is_monotonic_increasing:
        raise ValueError("Rows must be sorted chronologically")
    delta = df["timestamp"].diff().dropna().dt.total_seconds()
    if (delta < 60).any() or (delta % 60 != 0).any():
        raise ValueError("Expected one candle per minute, with optional missing minutes")
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    vals = df[list(REQUIRED[1:])].to_numpy(dtype=float)
    if not np.isfinite(vals).all() or (vals <= 0).any():
        raise ValueError("Prices must be finite and positive")
    if ((df["high"] < df[["open", "close", "low"]].max(axis=1)) |
        (df["low"] > df[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC candle")
    return df.reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """EMA trend + ATR, computed only from bars already closed."""
    out = df.copy()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()
    prev = out["close"].shift(1)
    tr = pd.concat([(out["high"] - out["low"]).abs(),
                    (out["high"] - prev).abs(),
                    (out["low"] - prev).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=14).mean()
    # Simple illustrative strategy. Not a claim about the pilot trader's rules.
    red = out["close"] < out["open"]
    green = out["close"] > out["open"]
    bullish = red.shift(2, fill_value=False) & green.shift(1, fill_value=False) & green
    bearish = green.shift(2, fill_value=False) & red.shift(1, fill_value=False) & red
    out["signal"] = np.select(
        [bullish & (out["close"] > out["ema20"]) & (out["ema20"] > out["ema50"]),
         bearish & (out["close"] < out["ema20"]) & (out["ema20"] < out["ema50"])],
        [1, -1], default=0,
    )
    # For reliable indicators, use a minimum warm-up period.
    out.loc[:49, "signal"] = 0
    return out


def _floor_lot(value: float, step: float) -> float:
    # Floored, never rounded up to an unaffordable lot.
    return float((Decimal(str(value)) / Decimal(str(step))).to_integral_value(
        rounding=ROUND_FLOOR) * Decimal(str(step)))


def _in_session(tstamp: pd.Timestamp, config: TestConfig) -> bool:
    start = time.fromisoformat(config.session_start_utc)
    end = time.fromisoformat(config.session_end_utc)
    t = tstamp.time()
    return start <= t < end if start <= end else (t >= start or t < end)


def run_backtest(df: pd.DataFrame, cfg: TestConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """At each M1 open, act on signals of LAST COMPLETED bar only.

    Only 1 position at a time. SL wins if a bar hits both SL and TP.
    Intrabar gap beyond SL uses worse of stop or bar open. Session limits entries,
    not forced closures. Weekends/holidays and missing data need broker-specific
    validation. No order submission is implemented.
    """
    f = add_features(df)
    equity = float(cfg.initial_equity)
    peak = equity
    trades: list[dict] = []
    curve = []
    position = None
    day = None
    day_start_equity = equity
    daily_pnl = 0.0
    daily_n = 0
    daily_win = False
    daily_losses = 0
    risk_skip = 0
    gaps = int((f["timestamp"].diff().dt.total_seconds().fillna(60) > 60).sum())

    def finalize(position, exit_price, exit_time, why):
        nonlocal equity, peak, daily_pnl, daily_win, daily_losses
        sign = position["direction"]
        gross = sign * (exit_price - position["entry_price"]) * position["lots"] * cfg.contract_oz_per_lot
        commission = 2 * cfg.commission_usd_per_lot_per_side * position["lots"]
        pnl = gross - commission
        equity += pnl
        peak = max(peak, equity)
        daily_pnl += pnl
        if pnl > 0:
            daily_win = True
        else:
            daily_losses += 1
        trades.append({
            "entry_time": position["entry_time"], "exit_time": exit_time,
            "direction": "BUY" if sign == 1 else "SELL",
            "lots": position["lots"], "entry_price": round(position["entry_price"], 5),
            "exit_price": round(exit_price, 5), "stop_loss": round(position["sl"], 5),
            "take_profit": round(position["tp"], 5), "gross_pnl_usd": round(gross, 2),
            "commission_usd": round(commission, 2), "net_pnl_usd": round(pnl, 2),
            "exit_reason": why, "equity_usd": round(equity, 2),
        })

    for i in range(50, len(f)):
        bar = f.iloc[i]
        ts = bar["timestamp"]
        if day != ts.date():
            day = ts.date()
            day_start_equity = equity
            daily_pnl, daily_n, daily_win, daily_losses = 0.0, 0, False, 0

        # Do not open new trades across a missing minute; and never pretend
        # SL/TP was known inside an unobserved gap.
        if position is not None:
            sign = position["direction"]
            spread = cfg.spread_usd_per_oz
            slip = cfg.slippage_usd_per_oz
            if sign == 1:
                stop_hit = bar["low"] <= position["sl"]
                target_hit = bar["high"] >= position["tp"]
                stop_exit = min(position["sl"], bar["open"]) - slip
                target_exit = position["tp"] - slip
            else:
                stop_hit = bar["high"] + spread >= position["sl"]
                target_hit = bar["low"] + spread <= position["tp"]
                stop_exit = max(position["sl"], bar["open"] + spread) + slip
                target_exit = position["tp"] + slip
            if stop_hit or target_hit:
                finalize(position, stop_exit if stop_hit else target_exit,
                         ts, "SL" if stop_hit else "TP")
                position = None

        # Never enter again within a candle in which a trade exited.
        just_exited = bool(trades and trades[-1]["exit_time"] == ts)
        prior = f.iloc[i - 1]
        gap_seconds = (ts - prior["timestamp"]).total_seconds()
        if (position is None and not just_exited and gap_seconds == 60 and
            _in_session(ts, cfg) and ts.weekday() < 5 and
            daily_n < cfg.max_trades_per_day and daily_losses < 2 and
            not daily_win and daily_pnl > -day_start_equity * cfg.max_daily_loss_pct / 100 and
            equity > 0 and int(prior["signal"]) != 0 and
            np.isfinite(prior["atr14"]) and prior["atr14"] > 0):
            sign = int(prior["signal"])
            sl_dist = float(prior["atr14"]) * cfg.sl_atr_mult
            entry = float(bar["open"]) + (cfg.spread_usd_per_oz if sign == 1 else 0)
            entry += sign * cfg.slippage_usd_per_oz
            stop = entry - sign * sl_dist
            target = entry + sign * sl_dist * cfg.rr
            # Include conservative stop-exit slippage + round-trip commissions.
            risk_per_lot = (sl_dist + cfg.slippage_usd_per_oz) * cfg.contract_oz_per_lot + 2 * cfg.commission_usd_per_lot_per_side
            risk_budget = equity * cfg.risk_per_trade_pct / 100
            lots = _floor_lot(risk_budget / risk_per_lot, cfg.lot_step)
            if lots + 1e-9 < cfg.min_lot or stop <= 0 or target <= 0:
                risk_skip += 1
            else:
                position = {"direction": sign, "entry_price": entry, "sl": stop,
                            "tp": target, "lots": lots, "entry_time": ts}
                daily_n += 1
                # Position can hit SL or TP during its *entry* candle.
                if sign == 1:
                    stop_hit = bar["low"] <= stop
                    tp_hit = bar["high"] >= target
                    stop_exit = min(stop, float(bar["open"])) - cfg.slippage_usd_per_oz
                    tp_exit = target - cfg.slippage_usd_per_oz
                else:
                    stop_hit = bar["high"] + cfg.spread_usd_per_oz >= stop
                    tp_hit = bar["low"] + cfg.spread_usd_per_oz <= target
                    stop_exit = max(stop, float(bar["open"]) + cfg.spread_usd_per_oz) + cfg.slippage_usd_per_oz
                    tp_exit = target + cfg.slippage_usd_per_oz
                if stop_hit or tp_hit:
                    finalize(position, stop_exit if stop_hit else tp_exit, ts,
                             "SL" if stop_hit else "TP")
                    position = None
        curve.append({"timestamp": ts, "closed_equity_usd": equity})

    if position is not None:
        last = f.iloc[-1]
        exit_price = float(last["close"]) + (cfg.spread_usd_per_oz if position["direction"] == -1 else 0)
        exit_price -= position["direction"] * cfg.slippage_usd_per_oz
        finalize(position, exit_price, last["timestamp"], "END_OF_DATA")
        if curve:
            curve[-1]["closed_equity_usd"] = equity
    td = pd.DataFrame(trades)
    cd = pd.DataFrame(curve)
    if cd.empty:
        maxdd = 0.0
    else:
        values = cd["closed_equity_usd"]
        running_peak = np.maximum.accumulate(np.r_[cfg.initial_equity, values])
        maxdd = float(np.min((np.r_[cfg.initial_equity, values] - running_peak) / running_peak) * 100)
    wins = td["net_pnl_usd"] > 0 if not td.empty else pd.Series(dtype=bool)
    gross_wins = td.loc[wins, "net_pnl_usd"].sum() if not td.empty else 0.0
    gross_losses = -td.loc[~wins, "net_pnl_usd"].sum() if not td.empty else 0.0
    metrics = {
        "trades": int(len(td)), "starting_equity_usd": cfg.initial_equity,
        "final_equity_usd": round(equity, 2),
        "net_pnl_usd": round(equity - cfg.initial_equity, 2),
        "win_rate_pct": round(float(wins.mean() * 100), 2) if len(wins) else None,
        "profit_factor": round(float(gross_wins / gross_losses), 3) if gross_losses > 0 else None,
        "max_closed_equity_drawdown_pct": round(maxdd, 2),
        "skipped_low_risk_budget": risk_skip,
        "data_gaps": gaps,
        "assumption_note": "Educational simulation, not actual broker fill, no guarantee or live orders",
    }
    return td, cd, metrics


def synthetic_m1(seed: int = 42, days: int = 10) -> pd.DataFrame:
    """FAKE prices for software smoke tests, never represent real gold history."""
    rng = np.random.default_rng(seed)
    timeidx = pd.date_range("2026-09-07T00:00:00Z", periods=days * 24 * 60, freq="min")
    timeidx = timeidx[timeidx.dayofweek < 5]
    if len(timeidx) < 120:
        raise ValueError("Not enough weekdays in synthetic sample")
    changes = rng.normal(0, 0.8, size=len(timeidx)) + np.sin(np.arange(len(timeidx)) / 200) * 0.10
    op = 3900 + np.cumsum(np.r_[0, changes[:-1]])
    cl = op + changes
    hi = np.maximum(op, cl) + rng.random(len(timeidx)) * 0.35
    lo = np.minimum(op, cl) - rng.random(len(timeidx)) * 0.35
    return pd.DataFrame({"timestamp": timeidx, "open": op, "high": hi, "low": lo, "close": cl})
