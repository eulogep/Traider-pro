"""Strict numeric types for financial inputs (audit Codex V0.3, I1).

* NaN, +inf and -inf are refused (including JSON exponents that overflow, e.g. ``1e309``).
* Strings and booleans are refused for numeric fields: ``"10000"`` or ``true`` is a client error,
  not a number to coerce silently.
* Operational upper bounds are set per field where they are declared (``Field(le=...)``).
"""

from __future__ import annotations

import math
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator


def _reject_text_and_bool(v):
    if isinstance(v, str | bytes | bytearray | bool):
        raise ValueError("nombre attendu (les chaînes et booléens sont refusés)")
    return v


def _finite(v: float) -> float:
    if not math.isfinite(v):
        raise ValueError("valeur non finie refusée (NaN / infini)")
    return v


FiniteFloat = Annotated[float, BeforeValidator(_reject_text_and_bool), AfterValidator(_finite)]
StrictNumberInt = Annotated[int, BeforeValidator(_reject_text_and_bool)]


def require_finite(value: float, what: str) -> float:
    """Guard for critical intermediate results of the engine."""
    if not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"calcul non fini pour {what} ({value!r}) : simulation interrompue, rien n'est enregistré")
    return value
