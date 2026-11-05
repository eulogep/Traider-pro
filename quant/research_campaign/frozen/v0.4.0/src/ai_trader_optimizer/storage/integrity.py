"""Run integrity — canonical serialisation, fingerprints and consistency checks (format ``ato-run/1``).

What this provides
------------------
* **Canonical serialisation** of every financial artefact. Each run artefact is stored on disk
  as exactly the bytes hashed here (equity is gzip-compressed with a fixed header; the hash
  covers the decompressed canonical CSV):

  - CSV: header = column names in engine order; ``\\n`` line ends; RFC 4180 quoting;
    floats = ``repr(float)`` (shortest exact round-trip), ints = decimal, booleans = ``true``/``false``,
    timestamps = ISO-8601 UTC with nanoseconds when present (``Timestamp.isoformat()``),
    missing value (None / NaN / NaT) = empty field. Non-finite floats are refused.
  - JSON: UTF-8, keys sorted, ``(",", ":")`` separators, ``allow_nan=False`` (NaN/±inf forbidden).
* ``result_fingerprint`` = SHA-256 over the canonical bytes of trades, decisions, equity and metrics
  (in that order, each prefixed by its name and length). It identifies the **computation result**:
  two runs of a deterministic engine on the same inputs must give the same fingerprint.
* ``integrity.json`` lists the SHA-256 of every stored artefact (manifest included) and is itself
  hashed into ``run_digest``, recorded in the SQLite index at publication.
* ``check_consistency`` recomputes the metrics from the stored journal / equity / decisions and
  verifies the accounting identities.

What this does NOT provide
--------------------------
Local hashes **detect corruption** (disk error, partial write, manual edit, buggy writer). They do
not prove authenticity: someone able to rewrite the files, ``integrity.json`` AND the SQLite index
can forge a consistent run. A signature / external timestamp would be needed for that.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from datetime import datetime

import numpy as np
import pandas as pd

FORMAT = "ato-run/1"
ARTIFACTS = ("manifest.json", "metrics.json", "trades.csv", "decisions.csv", "equity.csv.gz")
RESULT_ARTIFACTS = ("trades.csv", "decisions.csv", "equity.csv.gz", "metrics.json")
TIMESTAMP_COLUMNS = {
    "trades.csv": ("signal_time", "entry_time", "exit_time"),
    "decisions.csv": ("signal_time", "decision_time", "entry_bar_time"),
    "equity.csv.gz": ("timestamp",),
}
# metrics recomputed by check_consistency (all produced by analytics.compute_metrics)
_RECOMPUTED = ("initial_equity", "final_equity", "net_pnl", "return_pct", "trades", "wins", "non_wins",
               "win_rate_pct", "gross_profit", "gross_loss", "expectancy", "expectancy_r", "avg_win", "avg_loss",
               "largest_win", "largest_loss", "max_consecutive_losses", "avg_bars_held", "commission_total",
               "spread_cost_total", "slippage_cost_total", "total_costs", "pnl_before_costs", "profit_factor",
               "payoff_ratio", "max_dd_closed_pct", "max_dd_closed", "max_dd_mtm_pct", "max_dd_mtm", "signals",
               "signals_entered", "signals_rejected", "exit_reasons", "rejection_reasons", "by_direction",
               "losses_beyond_planned_risk", "trades_with_data_gap")


class NonCanonicalValueError(ValueError):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- canonical serialisation
def _cell(v) -> str:
    if v is None or v is pd.NaT:
        return ""
    if isinstance(v, bool | np.bool_):
        return "true" if v else "false"
    if isinstance(v, int | np.integer):
        return str(int(v))
    if isinstance(v, float | np.floating):
        f = float(v)
        if math.isnan(f):
            return ""
        if not math.isfinite(f):
            raise NonCanonicalValueError(f"valeur non finie dans un artefact : {f}")
        return repr(f)
    if isinstance(v, pd.Timestamp):
        if pd.isna(v):
            return ""
        if v.tzinfo is None:
            raise NonCanonicalValueError("horodatage sans fuseau dans un artefact")
        return v.tz_convert("UTC").isoformat()
    if isinstance(v, datetime):
        return pd.Timestamp(v).tz_convert("UTC").isoformat()
    if isinstance(v, str):
        return v
    raise NonCanonicalValueError(f"type non sérialisable dans un artefact : {type(v).__name__}")


def canonical_csv(df: pd.DataFrame) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow([str(c) for c in df.columns])
    for row in df.itertuples(index=False, name=None):
        w.writerow([_cell(v) for v in row])
    return out.getvalue().encode("utf-8")


def _jsonable(v):
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_jsonable(x) for x in v]
    if isinstance(v, bool | np.bool_):
        return bool(v)
    if isinstance(v, int | np.integer):
        return int(v)
    if isinstance(v, float | np.floating):
        f = float(v)
        if not math.isfinite(f):
            raise NonCanonicalValueError(f"valeur non finie dans un artefact JSON : {f}")
        return f
    if isinstance(v, pd.Timestamp | datetime):
        return pd.Timestamp(v).isoformat()
    return v


def canonical_json(obj) -> bytes:
    return json.dumps(_jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def gzip_fixed(data: bytes) -> bytes:
    """Deterministic gzip (mtime 0, no file name) so identical content gives identical files."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0, filename="") as gz:
        gz.write(data)
    return buf.getvalue()


def result_payloads(trades, decisions, equity, metrics) -> dict[str, bytes]:
    """Canonical (uncompressed) bytes of the four result artefacts."""
    return {"trades.csv": canonical_csv(trades), "decisions.csv": canonical_csv(decisions),
            "equity.csv.gz": canonical_csv(equity), "metrics.json": canonical_json(metrics)}


def fingerprint_payloads(payloads: dict[str, bytes]) -> str:
    h = hashlib.sha256(f"{FORMAT}|result|".encode())
    for name in RESULT_ARTIFACTS:
        data = payloads[name]
        h.update(f"{name}:{len(data)}:".encode())
        h.update(data)
    return h.hexdigest()


def result_fingerprint(trades, decisions, equity, metrics) -> str:
    return fingerprint_payloads(result_payloads(trades, decisions, equity, metrics))


def run_digest(artifact_hashes: dict[str, str]) -> str:
    body = "|".join(f"{n}={artifact_hashes[n]}" for n in ARTIFACTS)
    return sha256_hex(f"{FORMAT}|{body}".encode())


# ---------------------------------------------------------------- parsing verified bytes
def parse_csv(data: bytes, artifact: str) -> pd.DataFrame:
    if not data.strip():
        return pd.DataFrame()
    df = pd.read_csv(io.BytesIO(data), float_precision="round_trip", keep_default_na=False, na_values=[""])
    if len(df) == 0:
        return df
    for c in TIMESTAMP_COLUMNS.get(artifact, ()):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601")
    for c in df.columns:  # canonical booleans
        if df[c].dtype == object and set(df[c].dropna().unique()) <= {"true", "false"} and df[c].notna().any():
            df[c] = df[c].map({"true": True, "false": False})
    return df


# ---------------------------------------------------------------- consistency
def _close(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)) or set(a) != set(b):
            return False
        return all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, bool | str) or isinstance(b, bool | str):
        return a == b
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def check_consistency(trades: pd.DataFrame, decisions: pd.DataFrame, equity: pd.DataFrame,
                      metrics: dict, manifest: dict) -> list[str]:
    """Return human-readable problems (empty list = consistent)."""
    from ..analytics.metrics import compute_metrics

    problems: list[str] = []
    initial = manifest.get("config", {}).get("initial_equity")
    if initial is None or not _close(metrics.get("initial_equity"), initial):
        problems.append("metrics.initial_equity ≠ capital initial du manifeste")
        return problems
    recomputed = compute_metrics(trades, equity, float(initial), decisions)
    for k in _RECOMPUTED:
        if k in recomputed or k in metrics:
            if not _close(metrics.get(k), recomputed.get(k)):
                problems.append(f"métrique {k} incohérente avec le journal/la courbe "
                                f"(stockée {metrics.get(k)!r}, recalculée {recomputed.get(k)!r})")
    n = len(trades)
    if n:
        if not _close(float(trades["equity_after"].iloc[-1]), metrics.get("final_equity")):
            problems.append("dernier equity_after du journal ≠ final_equity")
        running = float(initial) + float(trades["net_pnl"].cumsum().iloc[-1])
        if not _close(running, metrics.get("final_equity"), 1e-7):
            problems.append("capital initial + somme des net_pnl ≠ final_equity")
    if len(equity) and not _close(float(equity["closed_equity"].iloc[-1]), metrics.get("final_equity")):
        problems.append("dernier point de la courbe de capital ≠ final_equity")
    if len(decisions):
        entered = decisions[decisions["outcome"] == "ENTERED"]
        if len(entered) != n:
            problems.append("nombre de décisions ENTERED ≠ nombre de trades")
        elif n and set(entered["trade_id"].astype(int)) != set(trades["trade_id"].astype(int)):
            problems.append("trades sans décision correspondante")
    elif n:
        problems.append("trades présents sans journal de décisions")
    return problems
