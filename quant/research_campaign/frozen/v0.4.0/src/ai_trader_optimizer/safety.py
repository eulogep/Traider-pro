"""Permanent safety switches. Read docs/DECISIONS.md before touching this file.

This build cannot send any order to any broker. There is no MetaTrader
import, no network order path and no credential handling anywhere in the
package; a test (tests/test_safety.py) scans the sources to keep it that way.
"""

from __future__ import annotations

from enum import Enum

#: Hard-coded. Changing it is not enough to trade: no live adapter exists.
LIVE_TRADING_ENABLED: bool = False
#: Demo-account execution is not implemented in v0.2 either.
DEMO_TRADING_ENABLED: bool = False


class ExecutionMode(str, Enum):
    SIMULATION = "simulation"
    DEMO = "demo"  # future — requires human validation
    LIVE = "live"  # future — requires human, technical and regulatory validation


class ExecutionDisabledError(RuntimeError):
    """Raised by every non-simulation adapter in this version."""


class DataKind(str, Enum):
    """Where a dataset / a result comes from. Never mix them in a conclusion."""

    SYNTHETIC = "synthetic"  # fake prices, software checks only
    HISTORICAL = "historical"  # imported broker/vendor history
    DEMO_ACCOUNT = "demo_account"  # future: fills from a demo account


DATA_KIND_LABELS_FR = {
    DataKind.SYNTHETIC: "Synthétique (démonstration, fausses cotations)",
    DataKind.HISTORICAL: "Historique importé (déclaré par l'utilisateur, non vérifié)",
    DataKind.DEMO_ACCOUNT: "Compte démo (non disponible en v0.2)",
}
