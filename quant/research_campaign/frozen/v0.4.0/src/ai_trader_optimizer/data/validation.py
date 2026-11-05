"""CSV import and validation — fail-closed.

Rules
-----
* Errors (missing columns, unparseable or missing values, unknown timezone,
  duplicates, unsorted rows, irregular spacing, invalid OHLC, non-positive
  prices) reject the WHOLE file. Nothing is silently repaired or sorted.
* Gaps are reported and classified, NEVER filled with invented prices.
* Timestamps must carry an explicit UTC offset, or the user must explicitly
  declare the source timezone (IANA name). DST-ambiguous local times are
  rejected rather than guessed.
* ``timestamp`` is the bar OPEN time (MetaTrader convention).
"""

from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

from ..safety import DataKind
from .models import (
    BAR_COLUMNS,
    OPTIONAL_COLUMNS,
    SECONDS_TIMEFRAME,
    TIMEFRAME_SECONDS,
    Dataset,
    DatasetMeta,
    QualityReport,
    fingerprint,
    normalize_symbol,
)

_OFFSET_RE = r"(?:Z|[+-]\d{2}:?\d{2})$"
_ALIASES = {
    "time": "timestamp", "datetime": "timestamp", "date_time": "timestamp", "timestamp": "timestamp",
    "open": "open", "high": "high", "low": "low", "close": "close",
    "tickvol": "tick_volume", "tick_volume": "tick_volume", "vol": "volume", "volume": "volume",
    "spread": "spread_points",
}
MIN_ROWS_WARNING = 500


def read_source(source) -> bytes:
    """Accept a path, raw bytes, or a file-like object (incl. Streamlit uploads)."""
    if isinstance(source, bytes | bytearray):
        return bytes(source)
    if isinstance(source, str | Path):
        return Path(source).read_bytes()
    data = source.read()
    if hasattr(source, "seek"):
        try:
            source.seek(0)
        except Exception:  # pragma: no cover - non seekable streams
            pass
    return data.encode() if isinstance(data, str) else data


def _parse_table(content: bytes) -> tuple[pd.DataFrame, str]:
    text_head = content[:4096].decode("utf-8-sig", errors="replace")
    first = text_head.splitlines()[0] if text_head else ""
    sep = "\t" if "\t" in first else (";" if first.count(";") > first.count(",") else ",")
    raw = pd.read_csv(io.BytesIO(content), sep=sep, dtype=str, keep_default_na=False,
                      encoding="utf-8-sig")
    cols = {c: c.strip().strip("<>").strip().lower() for c in raw.columns}
    raw = raw.rename(columns=cols)
    fmt = "standard"
    if "date" in raw.columns and "time" in raw.columns:  # MetaTrader 5 export
        fmt = "mt5"
        date = raw["date"].str.strip().str.replace(".", "-", regex=False)
        raw["timestamp"] = date + " " + raw["time"].str.strip()
        raw = raw.drop(columns=["date", "time"])
    elif "date" in raw.columns and "timestamp" not in raw.columns:
        raw = raw.rename(columns={"date": "timestamp"})
    raw = raw.rename(columns={c: _ALIASES.get(c, c) for c in raw.columns})
    return raw, fmt


def _to_float(col: pd.Series) -> pd.Series:
    """Exact decimal->float conversion (pd.to_numeric's fast parser is not round-trip exact)."""
    if pd.api.types.is_float_dtype(col):
        return col.astype(float)
    text = col.astype(str).str.strip()
    try:
        return text.astype(float)
    except ValueError:  # some cells are not numbers -> NaN there, reported as errors by the caller
        out = pd.Series(np.nan, index=col.index)
        for i, v in text.items():
            try:
                out[i] = float(v)
            except ValueError:
                pass
        return out


def _rows(mask) -> list[int]:
    return (np.flatnonzero(np.asarray(mask)) + 1).tolist()


def _classify_gap(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """start = last bar before the hole, end = first bar after it (UTC)."""
    days = pd.date_range(start.normalize(), end.normalize(), freq="D")
    if any(d.weekday() == 5 for d in days):
        return "week-end"
    hole = end - start
    if pd.Timedelta(minutes=30) <= hole <= pd.Timedelta(hours=3) and 20 <= start.hour <= 23:
        return "pause quotidienne probable"
    if hole >= pd.Timedelta(hours=12):
        return "fermeture / jour férié probable"
    return "intrajournalier — à vérifier"


def validate_bars(content_or_frame, *, source_timezone: str | None = None,
                  expected_timeframe: str | None = None) -> tuple[QualityReport, pd.DataFrame | None]:
    """Validate raw bars. Returns (report, clean_frame or None if any error)."""
    rep = QualityReport()
    if isinstance(content_or_frame, pd.DataFrame):
        raw = content_or_frame.copy()
        if "timestamp" in raw.columns:
            if pd.api.types.is_datetime64_any_dtype(raw["timestamp"]):
                raw["timestamp"] = raw["timestamp"].map(lambda t: t.isoformat())
            else:
                raw["timestamp"] = raw["timestamp"].astype(str)
        fmt = "dataframe"
    else:
        try:
            raw, fmt = _parse_table(content_or_frame)
        except Exception as exc:
            rep.add("error", "UNREADABLE", f"Fichier illisible comme CSV : {exc}")
            return rep, None
    rep.detected_format = fmt
    rep.rows_raw = int(len(raw))

    missing = [c for c in BAR_COLUMNS if c not in raw.columns]
    if missing:
        rep.add("error", "MISSING_COLUMNS",
                f"Colonnes obligatoires absentes : {', '.join(missing)}. Attendu : timestamp,open,high,low,close "
                "(ou export MT5 <DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>).")
        return rep, None
    if len(raw) == 0:
        rep.add("error", "EMPTY", "Le fichier ne contient aucune bougie.")
        return rep, None

    keep = list(BAR_COLUMNS) + [c for c in OPTIONAL_COLUMNS if c in raw.columns]
    df = raw[keep].copy()

    # ---- timestamps & timezone -------------------------------------------------
    ts_str = df["timestamp"].astype(str).str.strip()
    empty_ts = ts_str.eq("") | ts_str.str.lower().isin(["nan", "nat", "none"])
    if empty_ts.any():
        rep.add("error", "MISSING_TIMESTAMP", "Horodatages manquants.", _rows(empty_ts))
        return rep, None
    has_offset = ts_str.str.contains(_OFFSET_RE, regex=True)
    if has_offset.all():
        tz_label = "explicit-offsets"
        ts = pd.to_datetime(ts_str, utc=True, errors="coerce", format="ISO8601")
        if source_timezone:
            rep.add("info", "TZ_DECLARATION_IGNORED",
                    "Les horodatages contiennent un décalage explicite : le fuseau déclaré n'est pas utilisé.")
    elif has_offset.any():
        rep.add("error", "TZ_MIXED", "Certains horodatages ont un décalage UTC, d'autres non.",
                _rows(~has_offset))
        return rep, None
    else:
        if not source_timezone:
            rep.add("error", "TZ_MISSING",
                    "Horodatages sans fuseau. Déclarez explicitement le fuseau de la source "
                    "(ex. UTC, Europe/Athens pour beaucoup de serveurs MT5) — aucune hypothèse silencieuse.")
            return rep, None
        try:
            ZoneInfo(source_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            rep.add("error", "TZ_UNKNOWN", f"Fuseau inconnu : {source_timezone!r} (nom IANA attendu).")
            return rep, None
        tz_label = source_timezone
        naive = pd.to_datetime(ts_str, errors="coerce", format="mixed")
        bad = naive.isna()
        if bad.any():
            rep.add("error", "BAD_TIMESTAMP", "Horodatages illisibles.", _rows(bad))
            return rep, None
        try:
            ts = naive.dt.tz_localize(source_timezone, ambiguous="raise", nonexistent="raise").dt.tz_convert("UTC")
        except Exception as exc:  # AmbiguousTimeError / NonExistentTimeError
            rep.add("error", "TZ_AMBIGUOUS",
                    f"Heure locale ambiguë ou inexistante (changement d'heure) : {exc}. "
                    "Exportez les données avec un décalage UTC explicite.")
            return rep, None
    bad = ts.isna()
    if bad.any():
        rep.add("error", "BAD_TIMESTAMP", "Horodatages illisibles.", _rows(bad))
        return rep, None
    df["timestamp"] = ts.astype("datetime64[ns, UTC]")
    rep.stats["source_timezone"] = tz_label

    # ---- prices -----------------------------------------------------------------
    for c in ("open", "high", "low", "close", *[c for c in OPTIONAL_COLUMNS if c in df.columns]):
        df[c] = _to_float(df[c])
    px = df[["open", "high", "low", "close"]].to_numpy(dtype=float)
    nan_rows = ~np.isfinite(px).all(axis=1)
    if nan_rows.any():
        rep.add("error", "MISSING_VALUES", "Prix manquants ou non numériques (aucune valeur n'est inventée).",
                _rows(nan_rows))
    nonpos = (px <= 0).any(axis=1) & ~nan_rows
    if nonpos.any():
        rep.add("error", "NON_POSITIVE_PRICE", "Prix nuls ou négatifs.", _rows(nonpos))
    o, h, lo, c = (px[:, k] for k in range(4))
    with np.errstate(invalid="ignore"):
        bad_ohlc = ((h < np.maximum(o, c)) | (lo > np.minimum(o, c)) | (h < lo)) & ~nan_rows
    if bad_ohlc.any():
        rep.add("error", "INVALID_OHLC", "Bougies incohérentes (high < max(open, close) ou low > min(open, close)).",
                _rows(bad_ohlc))

    # ---- chronology -------------------------------------------------------------
    dup = df["timestamp"].duplicated(keep=False)
    if dup.any():
        rep.add("error", "DUPLICATED_TIMESTAMP", "Horodatages dupliqués (après conversion UTC).", _rows(dup))
    diffs = df["timestamp"].diff().dt.total_seconds().to_numpy()[1:]
    backwards = np.r_[False, diffs < 0]
    if backwards.any():
        rep.add("error", "UNSORTED", "Lignes non triées chronologiquement (aucun tri automatique).",
                _rows(backwards))
    positive = diffs[diffs > 0]
    if len(positive) == 0:
        rep.add("error", "TOO_SHORT", "Impossible de déterminer l'unité de temps (au moins 2 bougies distinctes).")
        return rep, None
    values, counts = np.unique(positive, return_counts=True)
    modal = int(values[np.argmax(counts)])  # most frequent spacing = native timeframe
    detected = SECONDS_TIMEFRAME.get(modal)
    if detected is None:
        rep.add("error", "UNKNOWN_TIMEFRAME", f"Intervalle dominant de {modal}s non supporté "
                f"(supportés : {', '.join(TIMEFRAME_SECONDS)}).")
        return rep, None
    if expected_timeframe and detected != expected_timeframe:
        rep.add("error", "TIMEFRAME_MISMATCH", f"Unité de temps détectée {detected}, attendue {expected_timeframe}.")
        return rep, None
    tf, tf_seconds = detected, modal
    rep.timeframe = tf
    irregular = np.r_[False, (diffs > 0) & (np.mod(diffs, tf_seconds) != 0)]
    if irregular.any():
        rep.add("error", "IRREGULAR_SPACING", f"Écarts non multiples de {tf} entre bougies.", _rows(irregular))
    epoch_ns = df["timestamp"].astype("int64").to_numpy()
    # Exact identity (I6): sub-second parts are refused for every timeframe, never truncated.
    misaligned = np.mod(epoch_ns, 1_000_000_000) != 0
    if tf_seconds < 86400:
        misaligned |= np.mod(epoch_ns, tf_seconds * 1_000_000_000) != 0
    if misaligned.any():
        rep.add("error", "MISALIGNED", f"Horodatages non alignés sur des bougies {tf} (fractions de seconde ou "
                "secondes/minutes parasites) : refus plutôt que troncature silencieuse.", _rows(misaligned))

    if not rep.ok:
        return rep, None

    # ---- warnings (dataset still accepted) ------------------------------------
    df = df.reset_index(drop=True)
    rep.rows_valid = int(len(df))
    rep.start, rep.end = df["timestamp"].iloc[0], df["timestamp"].iloc[-1]
    if len(df) < MIN_ROWS_WARNING:
        rep.add("warning", "FEW_ROWS", f"Seulement {len(df)} bougies : échantillon très court.")
    gap_idx = np.flatnonzero(diffs > tf_seconds) + 1
    if len(gap_idx):
        rows = []
        for i in gap_idx:
            a, b = df["timestamp"].iloc[i - 1], df["timestamp"].iloc[i]
            rows.append({"gap_start": a, "gap_end": b,
                         "missing_bars": int((b - a).total_seconds() // tf_seconds - 1),
                         "category": _classify_gap(a, b)})
        rep.gaps = pd.DataFrame(rows)
        intraday = rep.gaps[rep.gaps["category"].str.startswith("intrajournalier")]
        if len(intraday):
            rep.add("warning", "INTRADAY_GAPS",
                    f"{len(intraday)} trou(s) intrajournalier(s), {int(intraday['missing_bars'].sum())} bougie(s) "
                    "manquante(s). Non comblés : aucune entrée n'est simulée à travers un trou.",
                    (intraday.index + 1).tolist())
        others = len(rep.gaps) - len(intraday)
        if others:
            rep.add("info", "MARKET_CLOSURES", f"{others} interruption(s) cohérente(s) avec week-ends / pauses / fériés.")
    sat = df["timestamp"].dt.weekday.eq(5)
    if sat.any():
        rep.add("warning", "SATURDAY_BARS", "Bougies le samedi (UTC) : vérifier le fuseau de la source.", _rows(sat))
    rng = (df["high"] - df["low"]).to_numpy()
    zero = int((rng == 0).sum())
    if zero / len(df) > 0.05:
        rep.add("warning", "FLAT_BARS", f"{zero} bougies sans amplitude ({zero / len(df):.1%}) : liquidité/qualité à vérifier.")
    logret = np.abs(np.diff(np.log(df["close"].to_numpy())))
    if len(logret) > 20:
        med = float(np.median(logret[logret > 0])) if (logret > 0).any() else 0.0
        jumps = np.flatnonzero((logret > 0.01) & (logret > 25 * med)) + 2 if med > 0 else np.array([], dtype=int)
        if len(jumps):
            rep.add("warning", "PRICE_JUMPS", f"{len(jumps)} variation(s) clôture→clôture anormale(s) (> 1 % et > 25× la médiane).",
                    jumps.tolist())
    rep.stats.update({
        "price_min": float(df["low"].min()), "price_max": float(df["high"].max()),
        "median_bar_range": float(np.median(rng)), "zero_range_bars": zero,
        "missing_bars_in_gaps": int(rep.gaps["missing_bars"].sum()) if len(rep.gaps) else 0,
    })
    if "spread_points" in df.columns and df["spread_points"].notna().any():
        sp = df["spread_points"].dropna()
        rep.stats.update({"spread_points_median": float(sp.median()), "spread_points_p95": float(sp.quantile(0.95))})
    return rep, df


def import_csv(source, *, name: str, symbol: str, source_label: str, price_side: str = "bid",
               source_timezone: str | None = None, expected_timeframe: str | None = None,
               kind: DataKind = DataKind.HISTORICAL, notes: str = "") -> tuple[QualityReport, Dataset | None]:
    content = read_source(source)
    symbol = normalize_symbol(symbol)
    rep, df = validate_bars(content, source_timezone=source_timezone, expected_timeframe=expected_timeframe)
    if df is None:
        return rep, None
    meta = DatasetMeta(
        dataset_id=fingerprint(df, symbol, rep.timeframe, price_side),
        name=name, symbol=symbol, timeframe=rep.timeframe, price_side=price_side, kind=kind,
        source=source_label, source_timezone=rep.stats.get("source_timezone", "?"), rows=len(df),
        start=df["timestamp"].iloc[0].isoformat(), end=df["timestamp"].iloc[-1].isoformat(),
        raw_sha256=hashlib.sha256(content).hexdigest(),
        imported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        notes=notes, quality=rep.as_dict(),
    )
    return rep, Dataset(df, meta)


def dataset_from_frame(df: pd.DataFrame, *, name: str, symbol: str, source_label: str, kind: DataKind,
                       price_side: str = "bid", notes: str = "") -> Dataset:
    """Validate an in-memory frame (e.g. synthetic). Raises ValueError on any error."""
    symbol = normalize_symbol(symbol)
    rep, clean = validate_bars(df)
    if clean is None:
        raise ValueError("; ".join(f"{i.code}: {i.message}" for i in rep.errors()))
    meta = DatasetMeta(
        dataset_id=fingerprint(clean, symbol, rep.timeframe, price_side), name=name, symbol=symbol,
        timeframe=rep.timeframe, price_side=price_side, kind=kind, source=source_label,
        source_timezone=rep.stats.get("source_timezone", "explicit-offsets"), rows=len(clean),
        start=clean["timestamp"].iloc[0].isoformat(), end=clean["timestamp"].iloc[-1].isoformat(),
        notes=notes, quality=rep.as_dict(),
    )
    return Dataset(clean, meta)
