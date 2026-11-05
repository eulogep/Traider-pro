"""Fingerprint of the code that can influence a simulation result.

Included in ``run_id``: changing the engine, a strategy, the risk or metrics code
yields a new run id instead of silently overwriting results produced by older code.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
_RELEVANT = ("backtest", "strategies", "risk", "analytics", "features", "data")


@lru_cache(maxsize=1)
def code_fingerprint() -> str:
    h = hashlib.sha256()
    for sub in _RELEVANT:
        for path in sorted((_PKG / sub).rglob("*.py")):
            h.update(str(path.relative_to(_PKG)).encode())
            h.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]
