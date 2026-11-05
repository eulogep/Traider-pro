"""Shared helpers: hand-built bars and a scripted strategy with known signals."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trader_optimizer.backtest import BacktestConfig, ExecutionCosts
from ai_trader_optimizer.data import dataset_from_frame
from ai_trader_optimizer.risk import ContractSpec, RiskConfig
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.strategies import Strategy, StrategySpec

MONDAY_NOON = pd.Timestamp("2026-09-07T12:00:00Z")


def make_bars(ohlc, start=MONDAY_NOON, times=None) -> pd.DataFrame:
    ts = times if times is not None else pd.date_range(start, periods=len(ohlc), freq="min")
    arr = np.asarray(ohlc, dtype=float)
    return pd.DataFrame({"timestamp": pd.DatetimeIndex(ts), "open": arr[:, 0], "high": arr[:, 1],
                         "low": arr[:, 2], "close": arr[:, 3]})


def make_dataset(ohlc=None, frame=None, **kw):
    frame = frame if frame is not None else make_bars(ohlc, **kw)
    return dataset_from_frame(frame, name="test", symbol="XAUUSD", source_label="unit-test",
                              kind=DataKind.SYNTHETIC)


def flat_bar(p=100.0):
    return (p, p + 0.2, p - 0.2, p)


class Scripted(Strategy):
    """Emits the signals given in params['script'] = {bar_index: (direction, sl_dist, tp_dist)}."""

    implementation = "scripted"
    feature_columns = ["marker"]

    @property
    def warmup_bars(self) -> int:
        return 0

    def compute(self, bars):
        out = pd.DataFrame(index=bars.index)
        out["signal"] = 0
        out["sl_distance"] = np.nan
        out["tp_distance"] = np.nan
        out["marker"] = np.arange(len(bars), dtype=float)
        for i, (d, sl, tp) in self.params["script"].items():
            if i < len(bars):
                out.loc[i, ["signal", "sl_distance", "tp_distance"]] = [d, sl, tp]
        out["signal"] = out["signal"].astype(int)
        out["reason"] = np.where(out["signal"] != 0, "SCRIPT", "WAIT")
        return out


def scripted_spec(**overrides) -> StrategySpec:
    data = dict(id="test.scripted", name="scripted", version="1.0.0", owner="tests", category="baseline",
                status="active", usage_rights="project", implementation="scripted",
                timeframes={"execution": "M1"},
                trading_hours={"timezone": "UTC", "sessions": ["00:00-23:59"], "weekdays": [0, 1, 2, 3, 4, 5, 6]})
    data.update(overrides)
    return StrategySpec.model_validate(data)


def scripted(script, spec=None):
    spec = spec or scripted_spec()
    return spec, Scripted(spec, {"script": script})


def base_config(**kw) -> BacktestConfig:
    risk = kw.pop("risk", RiskConfig(max_daily_loss_pct=5, max_drawdown_pct=50, max_trades_per_day=50,
                                     max_losses_per_day=None))
    return BacktestConfig(
        initial_equity=10_000, costs=ExecutionCosts(spread=0.3, slippage=0.05, commission_per_lot_per_side=3.0),
        contract=ContractSpec(symbol="XAUUSD", contract_size=100, min_lot=0.01, lot_step=0.01, max_lot=50,
                              quote_currency="USD"),
        risk=risk, **kw)


@pytest.fixture
def lab_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ATO_DATA_DIR", str(tmp_path / "lab"))
    return tmp_path / "lab"


def _local_client_class():
    from fastapi.testclient import TestClient

    class LocalClient(TestClient):
        """Behaves like the local React UI: loopback Host and the X-ATO-Request header that the API
        guard requires on mutations. ``local_header=False`` simulates a foreign / naive caller."""

        def __init__(self, app, local_header: bool = True, **kw):
            kw.setdefault("base_url", "http://localhost")
            headers = dict(kw.pop("headers", None) or {})
            if local_header:
                headers.setdefault("X-ATO-Request", "1")
            super().__init__(app, headers=headers, **kw)
    return LocalClient


LocalClient = _local_client_class()
