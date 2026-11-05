"""Strategy specification (validated schema) and the common strategy interface.

A strategy is two things:
* a **spec** (YAML file under ``strategies/``): identity, version, owner, market,
  timeframes, trading hours, indicators, human-readable BUY/SELL/WAIT/
  invalidation/exit rules, bounded parameters, open questions;
* an **implementation** (Python class) that turns closed bars into signals.

Contract of ``Strategy.compute(bars)`` (checked by the engine):
row i of the output may only use bars[0..i]; it describes the decision taken
at the CLOSE of bar i, executed at the OPEN of bar i+1.
Columns: ``signal`` (1 BUY, -1 SELL, 0 WAIT), ``reason`` (short code),
``sl_distance`` (> 0 when signal != 0), ``tp_distance`` (> 0 or NaN = no TP),
plus the feature columns listed in ``feature_columns``.
Position SIZE is never decided by a strategy: that is the Risk Guardian's job.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from abc import ABC, abstractmethod
from datetime import time
from typing import Any, ClassVar, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..data.models import TIMEFRAME_SECONDS

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_SESSION = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")


class ParamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["int", "float", "choice", "bool"]
    default: Any
    min: float | None = None
    max: float | None = None
    choices: list[Any] | None = None
    description: str = ""
    editable: bool = True

    @model_validator(mode="after")
    def _check(self):
        if self.type == "choice" and not self.choices:
            raise ValueError("choice parameter needs 'choices'")
        self.coerce(self.default)
        return self

    def coerce(self, value):
        if self.type == "bool":
            if not isinstance(value, bool):
                raise ValueError(f"expected bool, got {value!r}")
            return value
        if self.type == "choice":
            if value not in self.choices:
                raise ValueError(f"{value!r} not in {self.choices}")
            return value
        if isinstance(value, bool | str | bytes):
            raise ValueError("nombre attendu (les chaînes et booléens sont refusés)")
        if not isinstance(value, int | float) or not math.isfinite(float(value)):
            raise ValueError(f"valeur numérique finie attendue, reçu {value!r}")
        num = int(value) if self.type == "int" else float(value)
        if self.type == "int" and float(value) != num:
            raise ValueError(f"expected integer, got {value!r}")
        if self.min is not None and num < self.min:
            raise ValueError(f"{num} < min {self.min}")
        if self.max is not None and num > self.max:
            raise ValueError(f"{num} > max {self.max}")
        return num


class TradingHours(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str = "UTC"
    sessions: list[str] = Field(default_factory=lambda: ["00:00-23:59"])
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])  # Monday = 0

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v):
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:  # M3: 422, not 500
            raise ValueError(f"fuseau horaire inconnu : {v!r} (nom IANA attendu, ex. Europe/Paris)") from exc
        return v

    @field_validator("sessions")
    @classmethod
    def _sessions(cls, v):
        if not v:
            raise ValueError("at least one session required")
        for s in v:
            if not _SESSION.match(s):
                raise ValueError(f"session {s!r} must look like HH:MM-HH:MM")
            a, b = s.split("-")
            time.fromisoformat(a)
            time.fromisoformat(b)
        return v

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v):
        if not v or any(d not in range(7) for d in v):
            raise ValueError("weekdays must be integers 0..6")
        return sorted(set(v))

    def parsed(self) -> list[tuple[time, time]]:
        return [tuple(time.fromisoformat(x) for x in s.split("-")) for s in self.sessions]


class Timeframes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution: str
    context: list[str] = Field(default_factory=list)

    @field_validator("execution")
    @classmethod
    def _tf(cls, v):
        if v not in TIMEFRAME_SECONDS:
            raise ValueError(f"unknown timeframe {v}")
        return v


class Rules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buy: list[str] = Field(default_factory=list)
    sell: list[str] = Field(default_factory=list)
    wait: list[str] = Field(default_factory=list)
    invalidation: list[str] = Field(default_factory=list)
    exit: list[str] = Field(default_factory=list)


class IndicatorRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str | None = None


class StrategySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    owner: str
    category: Literal["baseline", "pilot_trader", "third_party"]
    status: Literal["draft", "active", "archived"]
    illustrative: bool = False
    usage_rights: Literal["project", "owner_consent", "unclear"] = "unclear"
    implementation: str | None = None
    description: str = ""
    market: dict[str, str] = Field(default_factory=lambda: {"symbol": "XAUUSD"})
    timeframes: Timeframes
    trading_hours: TradingHours = Field(default_factory=TradingHours)
    indicators: list[IndicatorRef] = Field(default_factory=list)
    rules: Rules = Field(default_factory=Rules)
    params: dict[str, ParamSpec] = Field(default_factory=dict)
    risk_defaults: dict[str, float] = Field(default_factory=dict)  # suggestions; the Risk Guardian decides
    position_scaling: Literal["none", "martingale", "grid", "pyramiding"] = "none"
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _semver(cls, v):
        if not _SEMVER.match(v):
            raise ValueError("version must be semantic (MAJOR.MINOR.PATCH)")
        return v

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"

    def default_params(self) -> dict[str, Any]:
        return {k: p.coerce(p.default) for k, p in self.params.items()}

    def resolve_params(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Defaults + overrides, every value checked against its declared bounds."""
        overrides = overrides or {}
        unknown = set(overrides) - set(self.params)
        if unknown:
            raise ValueError(f"Unknown parameter(s) for {self.key}: {sorted(unknown)}")
        out = self.default_params()
        for k, v in overrides.items():
            spec = self.params[k]
            value = spec.coerce(v)
            if not spec.editable and value != out[k]:
                raise ValueError(f"Parameter {k} is not editable")
            out[k] = value
        return out

    def spec_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()[:16]

    def runnable_problems(self) -> list[str]:
        problems = []
        if self.status != "active":
            problems.append(f"statut « {self.status} » : seules les stratégies actives peuvent être testées")
        if not self.implementation:
            problems.append("aucune implémentation : règles encore à formaliser avec le trader")
        if self.position_scaling != "none":
            problems.append(f"gestion de position « {self.position_scaling} » interdite (martingale/grille)")
        if self.category == "third_party" and self.usage_rights == "unclear":
            problems.append("stratégie d'un tiers dont les droits d'utilisation ne sont pas clarifiés")
        return problems


class Strategy(ABC):
    implementation: ClassVar[str]
    feature_columns: ClassVar[list[str]] = []

    def __init__(self, spec: StrategySpec, params: dict[str, Any]):
        self.spec = spec
        self.params = params

    @property
    @abstractmethod
    def warmup_bars(self) -> int: ...

    @abstractmethod
    def compute(self, bars: pd.DataFrame) -> pd.DataFrame: ...

    def describe_decision(self, row: pd.Series) -> str:
        """Human-readable explanation of a signal row (used by the journal)."""
        return str(row.get("reason", ""))
