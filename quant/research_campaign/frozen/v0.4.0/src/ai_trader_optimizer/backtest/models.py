"""Backtest configuration and result containers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..numeric import FiniteFloat, StrictNumberInt
from ..risk.guardian import XAUUSD_HYPOTHETICAL, ContractSpec, RiskConfig
from ..strategies.base import TradingHours


class ExecutionCosts(BaseModel):
    """Fixed-cost ASSUMPTIONS (price units = quote currency per base unit, e.g. USD/oz)."""

    model_config = ConfigDict(extra="forbid")
    spread: FiniteFloat = Field(0.30, ge=0, le=100_000, description="Spread fixe hypothétique (ask - bid)")
    slippage: FiniteFloat = Field(0.05, ge=0, le=100_000, description="Glissement défavorable par exécution")
    commission_per_lot_per_side: FiniteFloat = Field(3.0, ge=0, le=1_000_000,
                                                     description="Commission par lot et par côté (devise du compte)")


class BacktestConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial_equity: FiniteFloat = Field(10_000.0, gt=0, le=1e12)
    account_currency: str = "USD"
    costs: ExecutionCosts = Field(default_factory=ExecutionCosts)
    contract: ContractSpec = Field(default_factory=lambda: XAUUSD_HYPOTHETICAL.model_copy())
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    trading_hours: TradingHours | None = None  # None = the strategy spec's hours
    trade_start: str | None = None  # ISO datetime (UTC if naive): entries only from here
    trade_end: str | None = None  # ISO datetime: data after this point is NOT loaded
    same_bar_policy: Literal["stop_first"] = "stop_first"
    close_at_session_end: bool = False
    max_bars_in_trade: StrictNumberInt | None = Field(None, ge=1, le=10_000_000)

    @field_validator("trade_start", "trade_end")
    @classmethod
    def _iso_utc(cls, v):
        """M3: real instants only; normalised to ISO-8601 UTC (one spelling per instant)."""
        if v is None:
            return None
        try:
            ts = pd.Timestamp(v)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"date invalide : {v!r}") from exc
        if pd.isna(ts):
            raise ValueError(f"date invalide : {v!r}")
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return ts.isoformat()

    @model_validator(mode="after")
    def _window(self):
        if self.trade_start and self.trade_end and pd.Timestamp(self.trade_start) >= pd.Timestamp(self.trade_end):
            raise ValueError("période vide ou inversée : trade_start doit précéder trade_end")
        return self

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


FILL_ASSUMPTIONS_FR = [
    "Données OHLC (pas de ticks) : l'ordre des prix à l'intérieur d'une bougie est inconnu.",
    "Signal calculé à la CLÔTURE d'une bougie ; entrée au marché à l'OUVERTURE de la bougie suivante.",
    "Achat au prix ASK = BID + spread fixe ; vente au BID ; + glissement défavorable à chaque exécution.",
    "Un niveau déjà franchi à l'OUVERTURE (chronologie connue) est exécuté avant toute touche intrabougie.",
    "Gap au-delà du stop : sortie au prix d'ouverture (pire que le stop) — la perte peut dépasser le risque prévu.",
    "Gap au-delà du TP : sortie au niveau du TP moins le glissement, le gap favorable n'est pas crédité (conservateur).",
    "Si le SL et le TP sont touchés À L'INTÉRIEUR d'une même bougie, le SL est retenu (ordre inconnu, conservateur).",
    "MAE/MFE = bornes inférieures prouvées sur OHLC : une bougie ne compte entièrement que si la position y a "
    "survécu ; dans la bougie de sortie, seul le niveau atteint est connu (pas une trajectoire exacte).",
    "Aucune entrée à travers un trou de données ; les trous ne sont jamais comblés.",
    "Spread, glissement et commission constants : ils varient en réalité (sessions, news, volatilité).",
    "Pas de marge, d'effet de levier, de stop-out, de swap, de conversion de devises ni de rejet d'ordre.",
    "Ceci n'est PAS une simulation d'exécution réaliste sur ticks bid/ask.",
]


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    decisions: pd.DataFrame
    equity: pd.DataFrame
    metrics: dict
    manifest: dict
    signals: pd.DataFrame | None = None  # full strategy output (features + signal + reason)
    extra: dict = field(default_factory=dict)

    @property
    def run_id(self) -> str:
        return self.manifest["run_id"]
