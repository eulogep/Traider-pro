"""Append-only, hash-chained, locked registry of edge-study trials (audit B04-1 / I04-1).

Every study is REGISTERED before it is computed. The number of looks at a family of data therefore
survives deleted or corrupted study files, and two concurrent studies cannot draw the same rank (exclusive
``fcntl`` lock around count-and-append). Each line is ``{"prev", "entry", "hash"}`` with
``hash = sha256(prev + canonical(entry))``: an edited, removed or reordered line breaks the chain and the
registry is refused (no new study until a human looks at it).

The family definition and the alpha rule are isolated (``family_key`` / ``family_alpha`` / ``RULE``) so that
they can only change after the pre-registered campaign — see quant/research_campaign/PROTOCOL.md (H2).
Rule selected by ``USE_SPENDING`` (legacy v0.4.0: family = dataset id, alpha_m = 0.05 / m).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..storage.integrity import canonical_json

BASE_ALPHA = 0.05
LEGACY_RULE = "bonferroni-sequentiel-0.05/m (v0.4.0)"
SPENDING_RULE = "depense-sommable-0.05*6/(pi^2*m^2), famille=type+symbole+unite (v0.4.1, protocole H2)"
USE_SPENDING = True  # protocol H2, activated after the "before" diagnosis (non-summable rule, by construction)
RULE = SPENDING_RULE if USE_SPENDING else LEGACY_RULE
GENESIS = "0" * 64


class RegistryIntegrityError(RuntimeError):
    pass


def family_key(symbol, timeframe, kind, dataset_id) -> str:
    """Legacy: one family per dataset id (a re-import of a sub-period escapes it). H2: every history of the
    same data type, instrument and timeframe — conservative, a sub-period cannot reset the count."""
    if not USE_SPENDING:
        return f"dataset:{dataset_id}"
    base = str(symbol or "?").upper().split("-")[0].split(".")[0].split("_")[0]
    return f"{kind}:{base}:{timeframe}"


def family_alpha(m: int) -> float:
    """Legacy alpha_m = 0.05/m is NOT summable (sum over 60 looks ≈ 0.234). H2: alpha_m = 0.05·6/(π²m²),
    whose sum over every m ≥ 1 is exactly 0.05 — a family-wise budget that open-ended looks cannot exceed."""
    if m < 1:
        raise ValueError("rang d'étude invalide")
    return BASE_ALPHA * 6 / (math.pi ** 2 * m ** 2) if USE_SPENDING else BASE_ALPHA / m


class StudyRegistry:
    def __init__(self, directory: Path):
        self.path = Path(directory) / "registry.jsonl"
        self.lock_path = Path(directory) / "registry.lock"

    @contextmanager
    def _locked(self):
        self.lock_path.touch(exist_ok=True)
        with open(self.lock_path, "r+") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def entries(self) -> list[dict]:
        """Verified entries (raises ``RegistryIntegrityError`` if the chain is broken)."""
        if not self.path.exists():
            return []
        out, prev = [], GENESIS
        for n, line in enumerate(self.path.read_bytes().splitlines(), 1):
            try:
                rec = json.loads(line)
                entry, h = rec["entry"], rec["hash"]
            except (ValueError, KeyError, TypeError) as exc:
                raise RegistryIntegrityError(f"Registre des études illisible (ligne {n}).") from exc
            if rec.get("prev") != prev or hashlib.sha256((prev + canonical_json(entry).decode()).encode()).hexdigest() != h:
                raise RegistryIntegrityError(f"Registre des études altéré (ligne {n}) : chaîne d'empreintes rompue.")
            out.append({**entry, "hash": h})
            prev = h
        return out

    def reserve(self, study_id: str, dataset_id: str, family: str, legacy: Callable[[], int] | int = 0) -> dict:
        """Rank m of this study in its family (existing registration reused: same inputs, same rank)."""
        with self._locked():
            entries = self.entries()
            for e in entries:
                if e["study_id"] == study_id:
                    return e
            prior = sum(1 for e in entries if e["family"] == family)
            m = prior + (legacy() if callable(legacy) else legacy) + 1
            entry = {"study_id": study_id, "dataset_id": dataset_id, "family": family, "m": m,
                     "alpha": family_alpha(m), "rule": RULE,
                     "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            prev = entries[-1]["hash"] if entries else GENESIS
            h = hashlib.sha256((prev + canonical_json(entry).decode()).encode()).hexdigest()
            with open(self.path, "ab") as f:
                f.write(canonical_json({"prev": prev, "entry": entry, "hash": h}) + b"\n")
            return {**entry, "hash": h}
