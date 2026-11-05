"""Data-layer value objects: quality report, dataset metadata, validated dataset."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from ..safety import DataKind

TIMEFRAME_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}
SECONDS_TIMEFRAME = {v: k for k, v in TIMEFRAME_SECONDS.items()}

PriceSide = Literal["bid", "mid"]
Severity = Literal["error", "warning", "info"]

#: Columns of a validated bar frame. ``timestamp`` = bar OPEN time, tz-aware UTC.
BAR_COLUMNS = ("timestamp", "open", "high", "low", "close")
OPTIONAL_COLUMNS = ("tick_volume", "volume", "spread_points")


@dataclass
class Issue:
    severity: Severity
    code: str
    message: str
    rows: list[int] = field(default_factory=list)  # 1-based data-row numbers (header excluded)

    def as_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code, "message": self.message,
                "rows": self.rows[:20]}


@dataclass
class QualityReport:
    issues: list[Issue] = field(default_factory=list)
    rows_raw: int = 0
    rows_valid: int = 0
    timeframe: str | None = None
    detected_format: str = "standard"
    start: pd.Timestamp | None = None
    end: pd.Timestamp | None = None
    gaps: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=["gap_start", "gap_end", "missing_bars", "category"]))
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    def add(self, severity: Severity, code: str, message: str, rows=None) -> None:
        self.issues.append(Issue(severity, code, message, [int(r) for r in (rows or [])][:50]))

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "rows_raw": self.rows_raw,
            "rows_valid": self.rows_valid,
            "timeframe": self.timeframe,
            "detected_format": self.detected_format,
            "start": None if self.start is None else self.start.isoformat(),
            "end": None if self.end is None else self.end.isoformat(),
            "issues": [i.as_dict() for i in self.issues],
            "gaps_count": int(len(self.gaps)),
            "gaps_by_category": self.gaps["category"].value_counts().to_dict() if len(self.gaps) else {},
            "stats": self.stats,
        }


class DatasetMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    name: str
    symbol: str
    timeframe: str
    price_side: PriceSide
    kind: DataKind
    source: str  # broker / vendor / "générateur synthétique"
    source_timezone: str  # "explicit-offsets" or the IANA zone the user declared
    rows: int
    start: str
    end: str
    raw_sha256: str | None = None
    imported_at: str | None = None
    notes: str = ""
    quality: dict = {}


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._\-]{1,19}$")


def normalize_symbol(symbol: str) -> str:
    """One spelling per instrument (I5): trimmed, upper case, then validated (broker suffixes allowed)."""
    s = (symbol or "").strip().upper()
    if not SYMBOL_PATTERN.match(s):
        raise ValueError(f"symbole invalide : {symbol!r} (lettres, chiffres, « . », « _ », « - », 2 à 20 caractères)")
    return s


def canonical_bytes(bars: pd.DataFrame) -> bytes:
    """Exact, deterministic serialisation of a validated bar frame (I6).

    It is both what the dataset fingerprint hashes AND what is stored on disk, so the simulated
    data is byte-for-byte the accepted data. Timestamps: whole seconds UTC (sub-second inputs are
    refused by validation); floats: ``repr`` (exact round trip, no rounding); all stored columns.
    """
    if (bars["timestamp"].astype("int64") % 1_000_000_000 != 0).any():
        raise ValueError("horodatages avec fractions de seconde : non représentables à l'identique")
    out = io.StringIO()
    cols = list(bars.columns)
    out.write(",".join(cols) + "\n")
    ts = bars["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()
    other = [bars[c].tolist() for c in cols[1:]]
    for i, t in enumerate(ts):
        cells = [t]
        for col in other:
            v = col[i]
            cells.append("" if v is None or (isinstance(v, float) and v != v) else repr(float(v)))
        out.write(",".join(cells) + "\n")
    return out.getvalue().encode()


def fingerprint(bars: pd.DataFrame, symbol: str, timeframe: str, price_side: str) -> str:
    """Content identity: instrument semantics + exact canonical bars. Provenance is NOT part of it (I7)."""
    h = hashlib.sha256()
    h.update(f"ato-dataset/2|{normalize_symbol(symbol)}|{timeframe}|{price_side}|".encode())
    h.update(canonical_bytes(bars))
    return h.hexdigest()[:16]


@dataclass
class Dataset:
    """A validated, immutable-by-convention bar series plus its identity."""

    bars: pd.DataFrame
    meta: DatasetMeta

    @property
    def is_synthetic(self) -> bool:
        return self.meta.kind == DataKind.SYNTHETIC

    @property
    def bar_seconds(self) -> int:
        return TIMEFRAME_SECONDS[self.meta.timeframe]
