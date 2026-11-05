"""Request/response models of the HTTP API (v1).

Domain models (``BacktestConfig``, ``DatasetMeta``, ``StrategySpec``…) are reused as-is;
only thin envelopes are defined here. The API never computes anything financial itself:
every number comes from the engine through ``services.py`` and the catalog.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from ..backtest import BacktestConfig

ID_PATTERN = r"^[0-9a-f]{16}$"  # dataset_id and run_id are 16-hex fingerprints
STRATEGY_KEY_PATTERN = r"^[a-z0-9_.\-]{1,80}@\d+\.\d+\.\d+$"


class ApiError(BaseModel):
    error: str
    detail: Any = None


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    software_version: str
    engine_version: str
    code_hash: str
    execution_mode: Literal["simulation"] = "simulation"
    live_trading_enabled: bool
    demo_trading_enabled: bool
    order_routes: int = 0  # always 0: this API exposes no order endpoint


class DemoDatasetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(42, ge=0, le=1_000_000)
    days: int = Field(10, ge=3, le=120)


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(pattern=ID_PATTERN)
    strategy_key: str = Field(pattern=STRATEGY_KEY_PATTERN)
    config: BacktestConfig | None = None  # None = saved defaults (Settings + Risk profile)
    label: str = Field("", max_length=120)


class EdgeStudyRequest(BaseModel):
    """Out-of-sample edge study (research only: no order, no position)."""
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(pattern=ID_PATTERN)
    strategy_key: str = Field(pattern=STRATEGY_KEY_PATTERN)
    config: BacktestConfig | None = None  # None = saved defaults (costs, contract, strategy params)
    horizon_bars: int = Field(240, ge=1, le=5000)
    folds: int = Field(4, ge=2, le=12)
    initial_train_fraction: float = Field(0.5, ge=0.2, le=0.8)


class ReproduceResult(BaseModel):
    identical: bool  # deterministic AND artifacts_intact
    deterministic: bool  # re-computation gives the same result fingerprint
    artifacts_intact: bool  # stored files passed verification (always true here: corrupted runs -> 409)
    stored_hash: str
    new_hash: str


def to_jsonable(value: Any) -> Any:
    """Recursively convert numpy / pandas values; NaN and ±inf become None (never a fake number)."""
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        f = float(value)
        return f if math.isfinite(f) else None
    if value is pd.NaT:
        return None
    return value


def frame_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    out = df.astype(object).where(pd.notna(df), None)
    return [to_jsonable(r) for r in out.to_dict(orient="records")]
