"""Risk Guardian — independent from strategies, FAIL-CLOSED.

Any critical uncertainty (unknown contract, invalid data, invalid stop,
internal error) blocks the new trade. Strategies never choose the size:
size = f(equity, risk %, stop distance, REAL contract specification).

Important: a stop-loss and a daily cap do NOT guarantee a maximum loss.
Gaps and slippage can fill beyond the stop; the realised loss can exceed
the planned risk (the engine fills gapped stops at the bar open).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..numeric import FiniteFloat, StrictNumberInt

_PAIR = re.compile(r"^[A-Z]{6}$")  # FX / metal pair: quote currency = last 3 letters

REJECTION_LABELS_FR: dict[str, str] = {
    "DATA_INVALID": "Données invalides ou trou de données avant l'entrée",
    "CONTRACT_UNKNOWN": "Spécifications du contrat inconnues ou invalides",
    "CONTRACT_CURRENCY_MISMATCH": "Devise de cotation ≠ devise du compte (conversion non gérée)",
    "CONTRACT_SYMBOL_MISMATCH": "Le contrat configuré ne correspond pas au symbole des données",
    "STOP_INSIDE_SPREAD": "Stop plus proche que spread + glissement : sortie immédiate, perte > risque prévu",
    "MARTINGALE_FORBIDDEN": "Gestion de type martingale / grille interdite",
    "MAX_DRAWDOWN_HALT": "Drawdown maximal atteint : trading arrêté pour le reste de la simulation",
    "DRAWDOWN_BUDGET_INSUFFICIENT": "Le risque prévu ferait dépasser le drawdown maximal",
    "MAX_OPEN_POSITIONS": "Nombre maximal de positions ouvertes atteint",
    "MAX_TRADES_PER_DAY": "Nombre maximal de trades du jour atteint",
    "MAX_LOSSES_PER_DAY": "Nombre maximal de pertes du jour atteint",
    "MAX_CONSECUTIVE_LOSSES": "Série maximale de pertes consécutives atteinte",
    "DAILY_WIN_STOP": "Arrêt après le premier gain du jour (règle activée)",
    "DAILY_LOSS_LIMIT": "Perte journalière maximale atteinte",
    "DAILY_LOSS_BUDGET_INSUFFICIENT": "Le risque prévu ferait dépasser la perte journalière maximale",
    "NO_EQUITY": "Capital nul ou négatif",
    "INVALID_STOP": "Distance de stop invalide",
    "SIZE_BELOW_MIN_LOT": "Taille calculée inférieure au lot minimal (risque trop faible pour ce stop)",
    "RISK_ABOVE_BUDGET": "Risque prévu supérieur au budget % du capital actuel (contrôle anti-martingale)",
    "GUARDIAN_ERROR": "Erreur interne du Risk Guardian (refus par sécurité)",
}


class ContractSpec(BaseModel):
    """Broker contract. Unknown values (None) make the guardian refuse every trade."""

    model_config = ConfigDict(extra="forbid")
    symbol: str = "XAUUSD"
    contract_size: FiniteFloat | None = Field(None, gt=0, le=1e9)  # base units per 1.00 lot (oz for XAUUSD)
    min_lot: FiniteFloat | None = Field(None, gt=0, le=1e6)
    lot_step: FiniteFloat | None = Field(None, gt=0, le=1e6)
    max_lot: FiniteFloat | None = Field(None, gt=0, le=1e6)
    quote_currency: str | None = "USD"
    source: str = "hypothèse — à vérifier auprès du courtier"

    @field_validator("symbol")
    @classmethod
    def _norm_symbol(cls, v: str) -> str:
        return (v or "").strip().upper()

    def problems(self, account_currency: str) -> list[str]:
        out = []
        sym = (self.symbol or "").upper()
        if _PAIR.match(sym) and self.quote_currency and self.quote_currency.upper() != sym[3:6]:
            out.append(f"devise de cotation {self.quote_currency} incohérente avec le symbole {sym}")
        for name in ("contract_size", "min_lot", "lot_step"):
            v = getattr(self, name)
            if v is None or not v > 0:
                out.append(f"{name} inconnu ou ≤ 0")
        if self.max_lot is not None and self.min_lot is not None and self.max_lot < self.min_lot:
            out.append("max_lot < min_lot")
        if not self.quote_currency:
            out.append("devise de cotation inconnue")
        return out

    def matches(self, instrument_symbol: str | None) -> bool:
        """Dataset symbol must start with the contract symbol (broker suffixes allowed: XAUUSD.m, XAUUSD-DEMO)."""
        if instrument_symbol is None:
            return True
        return bool(self.symbol) and instrument_symbol.strip().upper().startswith(self.symbol)

    def currency_ok(self, account_currency: str) -> bool:
        return bool(self.quote_currency) and self.quote_currency.upper() == account_currency.upper()


#: Typical XAUUSD CFD contract. HYPOTHESIS — every broker differs.
XAUUSD_HYPOTHETICAL = ContractSpec(symbol="XAUUSD", contract_size=100.0, min_lot=0.01, lot_step=0.01,
                                   max_lot=50.0, quote_currency="USD",
                                   source="hypothèse courante (100 oz/lot) — À VÉRIFIER chez le courtier")


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_per_trade_pct: FiniteFloat = Field(0.25, gt=0, le=5)
    max_open_positions: int = Field(1, ge=1, le=1, description="Le moteur v0.2 gère une position à la fois")
    max_daily_loss_pct: FiniteFloat = Field(1.0, gt=0, le=100)
    max_drawdown_pct: FiniteFloat = Field(10.0, gt=0, le=100)
    max_trades_per_day: StrictNumberInt = Field(2, ge=1, le=100)
    max_losses_per_day: StrictNumberInt | None = Field(2, ge=1, le=100)
    max_consecutive_losses: StrictNumberInt | None = Field(None, ge=1, le=1000)
    consecutive_loss_scope: Literal["day", "run"] = "day"
    stop_after_daily_win: bool = False
    daily_limit_includes_planned_risk: bool = True
    drawdown_limit_includes_planned_risk: bool = True
    day_timezone: str = "UTC"
    allow_martingale: Literal[False] = False  # cannot be enabled in this version

    @field_validator("day_timezone")
    @classmethod
    def _tz(cls, v):
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:  # M3: 422, not 500
            raise ValueError(f"fuseau horaire inconnu : {v!r} (nom IANA attendu, ex. Europe/Paris)") from exc
        return v


#: Reproduces the rules hard-coded in v0.1 (now explicit).
LEGACY_V01_RISK = RiskConfig(risk_per_trade_pct=0.25, max_daily_loss_pct=1.0, max_drawdown_pct=100.0,
                             max_trades_per_day=2, max_losses_per_day=2, stop_after_daily_win=True,
                             daily_limit_includes_planned_risk=False, drawdown_limit_includes_planned_risk=False)


def floor_to_step(value: float, step: float) -> float:
    """Floor (never round up to an unaffordable size)."""
    return float((Decimal(str(value)) / Decimal(str(step))).to_integral_value(rounding=ROUND_FLOOR)
                 * Decimal(str(step)))


def position_size(equity: float, risk_pct: float, stop_distance: float, stop_slippage: float,
                  commission_per_lot_per_side: float, contract: ContractSpec) -> tuple[float, float]:
    """Return (lots, risk_per_lot in account currency). Quote currency must equal account currency."""
    risk_per_lot = ((stop_distance + stop_slippage) * contract.contract_size
                    + 2 * commission_per_lot_per_side)
    budget = equity * risk_pct / 100
    lots = floor_to_step(budget / risk_per_lot, contract.lot_step)
    if contract.max_lot is not None and lots > contract.max_lot:
        lots = floor_to_step(contract.max_lot, contract.lot_step)
    return lots, risk_per_lot


@dataclass
class TradeProposal:
    direction: int  # 1 BUY, -1 SELL
    stop_distance: float  # entry -> stop, price units
    stop_slippage: float
    commission_per_lot_per_side: float
    data_ok: bool = True
    position_scaling: str = "none"
    spread: float = 0.0  # a stop within spread + slippage is hit at once


@dataclass
class RiskDecision:
    approved: bool
    lots: float = 0.0
    planned_risk: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def labels_fr(self) -> list[str]:
        return [REJECTION_LABELS_FR.get(r, r) for r in self.reasons]


@dataclass
class AccountState:
    equity: float
    peak_equity: float
    day: date | None = None
    day_start_equity: float = 0.0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    daily_losses: int = 0
    daily_win: bool = False
    consecutive_losses: int = 0
    open_positions: int = 0
    halted_reason: str | None = None
    last_risk_amount: float | None = None
    last_trade_was_loss: bool = False


class RiskGuardian:
    def __init__(self, config: RiskConfig, contract: ContractSpec, initial_equity: float,
                 account_currency: str = "USD", instrument_symbol: str | None = None):
        self.cfg = config
        self.contract = contract
        self.account_currency = account_currency
        self.contract_problems = contract.problems(account_currency)
        self.symbol_ok = contract.matches(instrument_symbol)
        self.state = AccountState(equity=initial_equity, peak_equity=initial_equity,
                                  day_start_equity=initial_equity)
        self.rejections: dict[str, int] = {}

    # ---- state transitions -------------------------------------------------------
    def on_new_day(self, day: date) -> None:
        s = self.state
        s.day, s.day_start_equity = day, s.equity
        s.daily_pnl, s.daily_trades, s.daily_losses, s.daily_win = 0.0, 0, 0, False
        if self.cfg.consecutive_loss_scope == "day":
            s.consecutive_losses = 0

    def on_position_opened(self, planned_risk: float) -> None:
        self.state.open_positions += 1
        self.state.daily_trades += 1
        self.state.last_risk_amount = planned_risk

    def on_position_closed(self, pnl: float) -> None:
        s = self.state
        s.open_positions = max(0, s.open_positions - 1)
        s.equity += pnl
        s.daily_pnl += pnl
        s.peak_equity = max(s.peak_equity, s.equity)
        if pnl > 0:
            s.daily_win = True
            s.consecutive_losses = 0
            s.last_trade_was_loss = False
        else:  # break-even counts as non-winning
            s.daily_losses += 1
            s.consecutive_losses += 1
            s.last_trade_was_loss = True
        if s.peak_equity > 0 and (s.peak_equity - s.equity) / s.peak_equity * 100 >= self.cfg.max_drawdown_pct:
            s.halted_reason = "MAX_DRAWDOWN_HALT"

    # ---- decision ----------------------------------------------------------------
    def evaluate(self, p: TradeProposal) -> RiskDecision:
        try:
            decision = self._evaluate(p)
        except Exception:  # fail closed
            decision = RiskDecision(False, reasons=["GUARDIAN_ERROR"])
        for r in decision.reasons:
            self.rejections[r] = self.rejections.get(r, 0) + 1
        return decision

    def _evaluate(self, p: TradeProposal) -> RiskDecision:
        cfg, s, reasons = self.cfg, self.state, []
        if not p.data_ok:
            reasons.append("DATA_INVALID")
        if self.contract_problems:
            reasons.append("CONTRACT_UNKNOWN")
        elif not self.contract.currency_ok(self.account_currency):
            reasons.append("CONTRACT_CURRENCY_MISMATCH")
        if not self.symbol_ok:
            reasons.append("CONTRACT_SYMBOL_MISMATCH")
        if p.position_scaling != "none" and not cfg.allow_martingale:
            reasons.append("MARTINGALE_FORBIDDEN")
        if s.halted_reason:
            reasons.append(s.halted_reason)
        if s.equity <= 0:
            reasons.append("NO_EQUITY")
        if s.open_positions >= cfg.max_open_positions:
            reasons.append("MAX_OPEN_POSITIONS")
        if s.daily_trades >= cfg.max_trades_per_day:
            reasons.append("MAX_TRADES_PER_DAY")
        if cfg.max_losses_per_day is not None and s.daily_losses >= cfg.max_losses_per_day:
            reasons.append("MAX_LOSSES_PER_DAY")
        if cfg.max_consecutive_losses is not None and s.consecutive_losses >= cfg.max_consecutive_losses:
            reasons.append("MAX_CONSECUTIVE_LOSSES")
        if cfg.stop_after_daily_win and s.daily_win:
            reasons.append("DAILY_WIN_STOP")
        daily_limit = s.day_start_equity * cfg.max_daily_loss_pct / 100
        if s.daily_pnl <= -daily_limit:
            reasons.append("DAILY_LOSS_LIMIT")

        if not (p.stop_distance > 0 and p.stop_distance == p.stop_distance and p.stop_distance != float("inf")):
            reasons.append("INVALID_STOP")
            return RiskDecision(False, reasons=reasons)
        if p.stop_distance <= p.spread + p.stop_slippage:
            reasons.append("STOP_INSIDE_SPREAD")
        if {"CONTRACT_UNKNOWN", "CONTRACT_CURRENCY_MISMATCH", "CONTRACT_SYMBOL_MISMATCH"} & set(reasons) or s.equity <= 0:
            return RiskDecision(False, reasons=reasons)

        lots, risk_per_lot = position_size(s.equity, cfg.risk_per_trade_pct, p.stop_distance, p.stop_slippage,
                                           p.commission_per_lot_per_side, self.contract)
        planned = lots * risk_per_lot
        if not (math.isfinite(lots) and math.isfinite(planned) and lots >= 0):
            raise ValueError("taille ou risque non fini")  # -> GUARDIAN_ERROR (fail closed)
        if lots + 1e-9 < self.contract.min_lot:
            reasons.append("SIZE_BELOW_MIN_LOT")
        else:
            if cfg.daily_limit_includes_planned_risk and s.daily_pnl - planned < -daily_limit - 1e-9:
                reasons.append("DAILY_LOSS_BUDGET_INSUFFICIENT")
            floor_equity = s.peak_equity * (1 - cfg.max_drawdown_pct / 100)
            if cfg.drawdown_limit_includes_planned_risk and s.equity - planned < floor_equity - 1e-9:
                reasons.append("DRAWDOWN_BUDGET_INSUFFICIENT")
            # Anti-martingale safety net: the risk is always a fixed % of CURRENT equity
            # (so it shrinks after losses); strategies cannot pass a size.
            if planned > s.equity * cfg.risk_per_trade_pct / 100 * (1 + 1e-9):
                reasons.append("RISK_ABOVE_BUDGET")
        return RiskDecision(not reasons, lots if not reasons else 0.0, planned if not reasons else 0.0, reasons)
