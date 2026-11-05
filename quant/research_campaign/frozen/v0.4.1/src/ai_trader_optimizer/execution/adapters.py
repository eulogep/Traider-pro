"""Execution adapters — separate interfaces for simulation, demo and live.

v0.2: only the simulation adapter exists (it is the backtest engine itself).
Demo and live adapters are deliberately NOT implemented: they raise
``ExecutionDisabledError``. There is no broker library import, no network
call and no credential parameter in this package.

Future (V0.5+, after human/technical/regulatory validation): a demo adapter
may forward APPROVED intents to an MT5 DEMO account through a separate
process holding the credentials outside this repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..safety import DEMO_TRADING_ENABLED, LIVE_TRADING_ENABLED, ExecutionDisabledError, ExecutionMode


@dataclass(frozen=True)
class OrderIntent:
    """What a future adapter would receive — always after Risk Guardian approval."""

    symbol: str
    direction: int
    lots: float
    stop_loss: float
    take_profit: float | None
    strategy_key: str
    decision_id: int


class ExecutionAdapter(Protocol):
    mode: ExecutionMode

    def submit(self, intent: OrderIntent) -> str: ...


class SimulationAdapter:
    """Records intents only (used for tests / journaling). Never leaves the process."""

    mode = ExecutionMode.SIMULATION

    def __init__(self):
        self.journal: list[OrderIntent] = []

    def submit(self, intent: OrderIntent) -> str:
        self.journal.append(intent)
        return f"SIM-{len(self.journal)}"


class DemoAccountAdapter:
    mode = ExecutionMode.DEMO

    def submit(self, intent: OrderIntent) -> str:
        raise ExecutionDisabledError("Exécution sur compte démo non disponible en v0.2 "
                                     f"(DEMO_TRADING_ENABLED={DEMO_TRADING_ENABLED}).")


class LiveAccountAdapter:
    mode = ExecutionMode.LIVE

    def submit(self, intent: OrderIntent) -> str:
        raise ExecutionDisabledError("Trading réel désactivé : aucune implémentation, validation humaine, "
                                     f"technique et réglementaire requise (LIVE_TRADING_ENABLED={LIVE_TRADING_ENABLED}).")


def get_adapter(mode: ExecutionMode) -> ExecutionAdapter:
    return {ExecutionMode.SIMULATION: SimulationAdapter, ExecutionMode.DEMO: DemoAccountAdapter,
            ExecutionMode.LIVE: LiveAccountAdapter}[mode]()
