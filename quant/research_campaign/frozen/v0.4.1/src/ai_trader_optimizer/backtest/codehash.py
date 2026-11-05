"""Fingerprints of the code.

* ``code_fingerprint`` — CALCULATION: code that can influence a simulation result. Included in ``run_id``:
  changing the engine, a strategy, the risk or metrics code yields a new run id instead of silently
  overwriting results produced by older code. (Unchanged in v0.4.1, so existing run ids stay valid.)
* ``validation_fingerprint`` — VALIDATION / PROVENANCE (audit N6): code that decides whether evidence is
  accepted, how it is serialised and which policy applied (storage, numeric guards, services, safety, API).
  Recorded in each newly published run's ``integrity.json``; a change of tolerance or serialisation is
  therefore visible even though the calculation fingerprint is the same.
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


_VALIDATION = ("storage", "api", "numeric.py", "services.py", "safety.py", "paths.py")


def validation_paths() -> list[str]:
    out = []
    for item in _VALIDATION:
        p = _PKG / item
        out += [str(x.relative_to(_PKG)) for x in sorted(p.rglob("*.py"))] if p.is_dir() else [item]
    return out


@lru_cache(maxsize=1)
def validation_fingerprint() -> str:
    h = hashlib.sha256()
    for rel in validation_paths():
        h.update(rel.encode())
        h.update((_PKG / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]
