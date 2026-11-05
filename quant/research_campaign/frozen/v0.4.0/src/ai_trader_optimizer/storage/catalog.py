"""Local lab catalog: SQLite index + files (single source of truth for the prototype).

Layout under ``data_dir()`` (default ``<project>/data/lab``)::

    lab.db                       datasets / runs / settings index
    raw/<sha256>.csv             imported file, byte-for-byte (immutable)
    datasets/<dataset_id>.csv.gz validated bars (derived from raw, never edited)
    runs/<run_id>/               manifest.json, metrics.json, trades.csv, decisions.csv, equity.csv.gz
"""

from __future__ import annotations

import fcntl
import gzip
import io
import json
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..backtest.models import BacktestResult
from ..data.models import Dataset, DatasetMeta
from ..paths import data_dir
from . import integrity as integ

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id TEXT PRIMARY KEY, name TEXT, symbol TEXT, timeframe TEXT, kind TEXT, source TEXT,
  rows INTEGER, start TEXT, end TEXT, imported_at TEXT, meta_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, created_at TEXT, dataset_id TEXT, data_kind TEXT, strategy_key TEXT,
  strategy_version TEXT, result_hash TEXT, label TEXT, metrics_json TEXT NOT NULL, manifest_json TEXT NOT NULL,
  run_digest TEXT
);
CREATE TABLE IF NOT EXISTS dataset_provenance (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id TEXT NOT NULL, declared_at TEXT, kind TEXT NOT NULL,
  source TEXT, name TEXT, notes TEXT, raw_sha256 TEXT, source_timezone TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
"""


class ReproducibilityError(RuntimeError):
    pass


class RunNotFoundError(KeyError):
    pass


class ProvenanceConflictError(ValueError):
    """Same content, contradictory provenance declaration (e.g. synthetic vs historical)."""


class CorruptRunError(RuntimeError):
    """A stored run failed verification (checksum, digest or consistency). Nothing is served."""


def _write_durable(path: Path, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _safe_id(value: str, kind: str = "identifiant") -> str:
    """Ids become file names: only 16-hex fingerprints are accepted (no path traversal)."""
    if not isinstance(value, str) or not _HEX16.match(value):
        raise ValueError(f"{kind} invalide : {value!r}")
    return value


def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)


class LabCatalog:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else data_dir()
        for sub in ("raw", "datasets", "runs"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        with closing(self._conn()) as con:
            con.executescript(SCHEMA)
            cols = {r[1] for r in con.execute("PRAGMA table_info(runs)")}
            if "run_digest" not in cols:  # index created by 0.3.0
                con.execute("ALTER TABLE runs ADD COLUMN run_digest TEXT")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.root / "lab.db")

    # ---- datasets ---------------------------------------------------------------
    def save_dataset(self, ds: Dataset, raw_bytes: bytes | None = None) -> str:
        """Store a dataset by CONTENT identity; record its provenance declaration (I6/I7).

        * The stored bars are the exact canonical bytes that were fingerprinted.
        * The first declaration (kind, source, name…) defines the dataset's provenance; it is never
          replaced. A later import of the same content with a different kind is refused
          (``ProvenanceConflictError``); with the same kind it is appended to the history.
        """
        m = ds.meta
        _safe_id(m.dataset_id, "dataset_id")
        if m.raw_sha256 is not None and not _SHA256.match(m.raw_sha256):
            raise ValueError("raw_sha256 invalide")
        from ..data.models import canonical_bytes, fingerprint
        if fingerprint(ds.bars, m.symbol, m.timeframe, m.price_side) != m.dataset_id:
            raise ValueError("dataset_id incohérent avec le contenu des bougies")
        existing = self.dataset_meta(m.dataset_id)
        if existing is not None and existing.kind != m.kind:
            raise ProvenanceConflictError(
                f"Ce contenu est déjà enregistré ({m.dataset_id}) avec la nature « {existing.kind.value} » "
                f"(source : {existing.source}). Une déclaration « {m.kind.value} » contradictoire est refusée.")
        if raw_bytes is not None and m.raw_sha256:
            raw_path = self.root / "raw" / f"{m.raw_sha256}.csv"
            if not raw_path.exists():
                _write_durable(raw_path, raw_bytes)
        path = self.root / "datasets" / f"{m.dataset_id}.csv.gz"
        if not path.exists():
            tmp = path.with_suffix(f".tmp-{uuid.uuid4().hex}")
            _write_durable(tmp, integ.gzip_fixed(canonical_bytes(ds.bars)))
            os.replace(tmp, path)
        with closing(self._conn()) as con, con:
            if existing is None:
                con.execute("INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                    m.dataset_id, m.name, m.symbol, m.timeframe, m.kind.value, m.source, m.rows, m.start, m.end,
                    m.imported_at, m.model_dump_json()))
            con.execute("INSERT INTO dataset_provenance (dataset_id, declared_at, kind, source, name, notes, "
                        "raw_sha256, source_timezone) VALUES (?,?,?,?,?,?,?,?)",
                        (m.dataset_id, m.imported_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         m.kind.value, m.source, m.name, m.notes, m.raw_sha256, m.source_timezone))
        return m.dataset_id

    def dataset_provenance(self, dataset_id: str) -> list[dict]:
        _safe_id(dataset_id, "dataset_id")
        with closing(self._conn()) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT declared_at, kind, source, name, notes, raw_sha256, source_timezone "
                               "FROM dataset_provenance WHERE dataset_id=? ORDER BY seq", (dataset_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_datasets(self) -> pd.DataFrame:
        with closing(self._conn()) as con:
            return pd.read_sql_query("SELECT dataset_id, name, symbol, timeframe, kind, source, rows, start, end, "
                                     "imported_at FROM datasets ORDER BY imported_at DESC, name", con)

    def dataset_meta(self, dataset_id: str) -> DatasetMeta | None:
        _safe_id(dataset_id, "dataset_id")
        with closing(self._conn()) as con:
            row = con.execute("SELECT meta_json FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        return DatasetMeta.model_validate_json(row[0]) if row else None

    def load_dataset(self, dataset_id: str) -> Dataset:
        meta = self.dataset_meta(dataset_id)
        if meta is None:
            raise KeyError(dataset_id)
        data = gzip.decompress((self.root / "datasets" / f"{_safe_id(dataset_id)}.csv.gz").read_bytes())
        bars = pd.read_csv(io.BytesIO(data), float_precision="round_trip")
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True).astype("datetime64[ns, UTC]")
        from ..data.models import canonical_bytes, fingerprint
        if canonical_bytes(bars) != data or fingerprint(bars, meta.symbol, meta.timeframe, meta.price_side) != dataset_id:
            raise ValueError(f"Jeu de données {dataset_id} altéré sur disque (empreinte différente).")
        return Dataset(bars, meta)

    def delete_dataset(self, dataset_id: str) -> None:
        with closing(self._conn()) as con, con:
            con.execute("DELETE FROM datasets WHERE dataset_id=?", (dataset_id,))

    # ---- runs -------------------------------------------------------------------
    # Publication protocol (format ato-run/1, see storage/integrity.py):
    #   1. canonical payloads + consistency check of the in-memory result (refuse inconsistent results);
    #   2. exclusive per-run lock (fcntl.flock on runs/.locks/<run_id>.lock);
    #   3. if runs/<run_id>/ exists: verify it; same result -> idempotent no-op, different -> refused;
    #   4. write every artefact + integrity.json into runs/.staging/<run_id>-<random>/, fsync,
    #      re-read and verify the staged copy;
    #   5. atomic rename staging -> runs/<run_id>/ (readers only ever see complete runs);
    #   6. index row (INSERT, never REPLACE) carrying run_digest.
    # An interrupted publication leaves only a staging directory, ignored by readers and
    # removed by the next publication of the same run.
    def _runs_root(self) -> Path:
        return self.root / "runs"

    @contextmanager
    def _run_lock(self, run_id: str):
        locks = self._runs_root() / ".locks"
        locks.mkdir(parents=True, exist_ok=True)
        with open(locks / f"{run_id}.lock", "a+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def save_run(self, result: BacktestResult, label: str = "") -> str:
        """Publish a run atomically. Same run_id + same results = idempotent (nothing rewritten);
        same run_id + different results is refused; a corrupted existing run is never overwritten."""
        man = result.manifest
        run_id = _safe_id(man["run_id"], "run_id")
        payloads = integ.result_payloads(result.trades, result.decisions, result.equity, result.metrics)
        fp = integ.fingerprint_payloads(payloads)
        if man.get("result_hash") != fp:
            raise ReproducibilityError(
                f"Run {run_id} : le manifeste déclare l'empreinte {man.get('result_hash')} mais le contenu à "
                f"enregistrer a l'empreinte {fp} (résultat modifié après calcul) — rien n'a été enregistré.")
        problems = integ.check_consistency(result.trades, result.decisions, result.equity, result.metrics, man)
        if problems:
            raise CorruptRunError(f"Run {run_id} incohérent, publication refusée : " + " ; ".join(problems))
        files = {
            "manifest.json": integ.canonical_json(man),
            "metrics.json": payloads["metrics.json"],
            "trades.csv": payloads["trades.csv"],
            "decisions.csv": payloads["decisions.csv"],
            "equity.csv.gz": integ.gzip_fixed(payloads["equity.csv.gz"]),
        }
        hashes = {n: integ.sha256_hex(b) for n, b in files.items()}
        integrity = {"format": integ.FORMAT, "run_id": run_id, "result_hash": fp,
                     "artifacts": {n: {"sha256": hashes[n], "bytes": len(files[n])} for n in integ.ARTIFACTS},
                     "run_digest": integ.run_digest(hashes)}
        runs = self._runs_root()
        final = runs / run_id
        with self._run_lock(run_id):
            if final.exists():
                return self._accept_existing(run_id, fp, man, result.metrics, integrity["run_digest"], label)
            staging = runs / ".staging" / f"{run_id}-{uuid.uuid4().hex}"
            staging.mkdir(parents=True)
            for old in (runs / ".staging").glob(f"{run_id}-*"):  # leftovers of interrupted publications
                if old != staging:
                    shutil.rmtree(old, ignore_errors=True)
            try:
                for name, data in {**files, "integrity.json": integ.canonical_json(integrity)}.items():
                    _write_durable(staging / name, data)
                self._verify_dir(staging, run_id, expected_digest=integrity["run_digest"])
                os.rename(staging, final)  # atomic publication on the same filesystem
                _fsync_dir(runs)
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
            self._index_run(man, fp, integrity["run_digest"], label, result.metrics)
        return run_id

    def _accept_existing(self, run_id, fp, man, metrics, digest, label) -> str:
        existing = self._read_verified(run_id, require_index=False)  # raises CorruptRunError if damaged
        if existing.manifest["result_hash"] != fp:
            raise ReproducibilityError(
                f"Run {run_id} déjà publié avec l'empreinte {existing.manifest['result_hash']} ≠ {fp} : "
                "résultat non reproductible ou modifié, rien n'a été écrasé.")
        self._index_run(existing.manifest, fp, existing.extra["run_digest"], label, existing.metrics)
        return run_id

    def _index_run(self, man, fp, digest, label, metrics) -> None:
        with closing(self._conn()) as con, con:
            row = con.execute("SELECT run_digest FROM runs WHERE run_id=?", (man["run_id"],)).fetchone()
            if row is None:
                con.execute("INSERT INTO runs (run_id, created_at, dataset_id, data_kind, strategy_key, "
                            "strategy_version, result_hash, label, metrics_json, manifest_json, run_digest) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                                man["run_id"], man["created_at"], man["dataset"]["dataset_id"], man["data_kind"],
                                man["strategy"]["key"], man["strategy"]["version"], fp, label,
                                integ.canonical_json(metrics).decode(), integ.canonical_json(man).decode(), digest))
            elif row[0] != digest:
                raise CorruptRunError(f"Run {man['run_id']} : l'index SQLite et les fichiers divergent.")

    def list_runs(self) -> pd.DataFrame:
        with closing(self._conn()) as con:
            df = pd.read_sql_query("SELECT run_id, created_at, label, dataset_id, data_kind, strategy_key, "
                                   "result_hash, metrics_json, manifest_json FROM runs ORDER BY created_at DESC",
                                   con)
        if df.empty:
            return df
        mets = df.pop("metrics_json").map(json.loads)
        mans = df.pop("manifest_json").map(json.loads)
        df["account_currency"] = mans.map(lambda m: m.get("config", {}).get("account_currency"))
        for k in ("trades", "net_pnl", "win_rate_pct", "profit_factor", "expectancy", "max_dd_mtm_pct"):
            df[k] = mets.map(lambda m, k=k: m.get(k))
        return df

    def run_dir(self, run_id: str) -> Path:
        d = self._runs_root() / _safe_id(run_id, "run_id")
        if not d.is_dir():
            raise RunNotFoundError(run_id)
        if not (d / "integrity.json").is_file():
            raise CorruptRunError(f"Run {run_id} sans fichier d'intégrité (format antérieur à 0.3.1 ou publication "
                                  "incomplète) : non vérifiable, relancez-le.")
        return d

    def _verify_dir(self, d: Path, run_id: str, expected_digest: str | None) -> tuple[dict, dict, dict]:
        """Read every artefact ONCE, verify it, return (raw bytes, payloads, integrity) of what was verified."""
        problems: list[str] = []
        try:
            integrity = json.loads((d / "integrity.json").read_bytes())
        except (OSError, ValueError) as exc:
            raise CorruptRunError(f"Run {run_id} : integrity.json illisible ({exc}).") from exc
        if integrity.get("format") != integ.FORMAT or integrity.get("run_id") != run_id:
            raise CorruptRunError(f"Run {run_id} : integrity.json de format ou d'identifiant inattendu.")
        raw: dict[str, bytes] = {}
        for name in integ.ARTIFACTS:
            try:
                raw[name] = (d / name).read_bytes()
            except OSError:
                problems.append(f"{name} manquant")
                continue
            declared = integrity.get("artifacts", {}).get(name, {}).get("sha256")
            if integ.sha256_hex(raw[name]) != declared:
                problems.append(f"{name} modifié (empreinte SHA-256 différente)")
        hashes = {n: integ.sha256_hex(raw[n]) for n in raw}
        if len(hashes) == len(integ.ARTIFACTS) and integ.run_digest(hashes) != integrity.get("run_digest"):
            problems.append("integrity.json incohérent avec les artefacts (run_digest)")
        if expected_digest is not None and integrity.get("run_digest") != expected_digest:
            problems.append("empreinte du run différente de celle enregistrée dans l'index")
        if problems:
            raise CorruptRunError(f"Run {run_id} corrompu : " + " ; ".join(problems) + ". Aucun résultat n'est servi.")
        try:
            payloads = {"trades.csv": raw["trades.csv"], "decisions.csv": raw["decisions.csv"],
                        "equity.csv.gz": gzip.decompress(raw["equity.csv.gz"]), "metrics.json": raw["metrics.json"]}
        except OSError as exc:
            raise CorruptRunError(f"Run {run_id} corrompu : equity.csv.gz illisible ({exc}).") from exc
        fp = integ.fingerprint_payloads(payloads)
        manifest = json.loads(raw["manifest.json"])
        if fp != integrity.get("result_hash") or fp != manifest.get("result_hash"):
            raise CorruptRunError(f"Run {run_id} corrompu : l'empreinte du contenu ({fp}) ne correspond pas à "
                                  "l'empreinte publiée.")
        return raw, payloads, integrity

    def _read_verified(self, run_id: str, require_index: bool = True) -> BacktestResult:
        d = self.run_dir(run_id)
        expected = None
        if require_index:
            with closing(self._conn()) as con:
                row = con.execute("SELECT run_digest FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise RunNotFoundError(run_id)
            expected = row[0]
        raw, payloads, integrity = self._verify_dir(d, run_id, expected)
        manifest = json.loads(raw["manifest.json"])
        metrics = json.loads(payloads["metrics.json"])
        trades = integ.parse_csv(payloads["trades.csv"], "trades.csv")
        decisions = integ.parse_csv(payloads["decisions.csv"], "decisions.csv")
        equity = integ.parse_csv(payloads["equity.csv.gz"], "equity.csv.gz")
        problems = integ.check_consistency(trades, decisions, equity, metrics, manifest)
        if problems:
            raise CorruptRunError(f"Run {run_id} incohérent : " + " ; ".join(problems) + ".")
        return BacktestResult(trades, decisions, equity, metrics, manifest,
                              extra={"run_digest": integrity["run_digest"], "raw": raw})

    def load_run(self, run_id: str) -> BacktestResult:
        """Return a run ONLY after verifying the bytes actually read (checksums, digest, consistency)."""
        return self._read_verified(run_id)

    def read_verified_artifact(self, run_id: str, name: str) -> bytes:
        if name not in integ.ARTIFACTS:
            raise ValueError(f"artefact inconnu : {name}")
        return self._read_verified(run_id).extra["raw"][name]

    def delete_run(self, run_id: str) -> None:
        with closing(self._conn()) as con, con:
            con.execute("DELETE FROM runs WHERE run_id=?", (run_id,))

    # ---- settings ---------------------------------------------------------------
    def get_setting(self, key: str, default=None):
        with closing(self._conn()) as con:
            row = con.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key: str, value) -> None:
        with closing(self._conn()) as con, con:
            con.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, _json(value)))
