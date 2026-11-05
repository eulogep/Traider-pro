"""Immutable catalogue of EXTERNAL simulations, separate from the engine's runs (``<lab>/external/``).

* ``sources/<sha256>.<ext>`` — the uploaded file, byte for byte, create-only, read-only (0444). Never rewritten.
* ``simulations/<sim_id>.json`` — canonical container ``{"format", "sha256", "simulation"}``, create-only,
  read-only; verified on EVERY read (canonical bytes, digest, identity → id, source present with the same
  SHA-256, figures re-derived from the stored deals).
* ``imports.jsonl`` — append-only, hash-chained log of every import attempt (created / already present).

Idempotent: the same file gives the same id and the same bytes → "already imported". The same id with
different content is refused (409). Nothing is written before the file has been fully parsed and validated.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..storage.integrity import canonical_json
from .mt5_report import read_members
from .simulation import SIM_FORMAT, build, semantic_problems

GENESIS = "0" * 64


class ExternalSimIntegrityError(RuntimeError):
    """A stored external simulation (or the import log) does not verify."""


class ExternalSimConflictError(ValueError):
    """Same identifier, different content — never overwritten."""


def _dir(root: Path) -> Path:
    d = Path(root) / "external"
    for sub in ("sources", "simulations"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def _container(body: dict) -> bytes:
    return canonical_json({"format": SIM_FORMAT, "sha256": hashlib.sha256(canonical_json(body)).hexdigest(),
                           "simulation": body})


def _create_only(path: Path, data: bytes) -> bool:
    """Atomic create-only write; returns False if the file already existed (left untouched)."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o444)
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
    finally:
        Path(tmp).unlink(missing_ok=True)


@contextmanager
def _locked(d: Path):
    lock = d / "imports.lock"
    lock.touch(exist_ok=True)
    with open(lock, "r+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _log_entries(d: Path) -> list[dict]:
    p = d / "imports.jsonl"
    if not p.exists():
        return []
    out, prev = [], GENESIS
    for n, line in enumerate(p.read_bytes().splitlines(), 1):
        try:
            rec = json.loads(line)
            entry, h = rec["entry"], rec["hash"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ExternalSimIntegrityError(f"Journal des imports illisible (ligne {n}).") from exc
        if rec.get("prev") != prev or hashlib.sha256((prev + canonical_json(entry).decode()).encode()).hexdigest() != h:
            raise ExternalSimIntegrityError(f"Journal des imports altéré (ligne {n}).")
        out.append(entry)
        prev = h
    return out


def _log(d: Path, entry: dict) -> None:
    entries_path = d / "imports.jsonl"
    raw = entries_path.read_bytes().splitlines() if entries_path.exists() else []
    prev = json.loads(raw[-1])["hash"] if raw else GENESIS
    _log_entries(d)  # refuse to append to a broken chain
    h = hashlib.sha256((prev + canonical_json(entry).decode()).encode()).hexdigest()
    with open(entries_path, "ab") as f:
        f.write(canonical_json({"prev": prev, "entry": entry, "hash": h}) + b"\n")


def _ext(name: str) -> str:
    low = name.lower()
    for e in (".html", ".htm", ".xlsx", ".csv", ".zip", ".txt"):
        if low.endswith(e):
            return e
    return ".bin"


def import_file(root: Path, filename: str, raw: bytes, fallback_contract_size: float, origin: str) -> dict:
    """Parse + validate FIRST (no write), then publish source and simulation create-only."""
    sha = hashlib.sha256(raw).hexdigest()
    reports, members = read_members(filename, raw)
    body = build(reports, members, filename, sha, fallback_contract_size)
    data = _container(body)
    d = _dir(root)
    with _locked(d):
        path = d / "simulations" / f"{body['sim_id']}.json"
        if path.exists():
            existing = path.read_bytes()
            verify(root, existing, body["sim_id"])
            if existing != data:
                raise ExternalSimConflictError(
                    f"La simulation {body['sim_id']} existe déjà avec un contenu différent (version d'analyse "
                    "différente ou fichier modifié) : rien n'est écrasé.")
            outcome = "déjà importée"
        else:
            src = d / "sources" / f"{sha}{_ext(filename)}"
            if not _create_only(src, raw) and hashlib.sha256(src.read_bytes()).hexdigest() != sha:
                raise ExternalSimIntegrityError("Fichier source déjà présent mais altéré : import refusé.")
            _create_only(path, data)
            outcome = "créée"
        _log(d, {"sim_id": body["sim_id"], "source_sha256": sha, "source_name": filename, "origin": origin,
                 "outcome": outcome, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    stored = load(root, body["sim_id"])
    return {"outcome": outcome, "simulation": stored}


def verify(root: Path, raw: bytes, sim_id: str) -> dict:
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} illisible.") from exc
    if not isinstance(doc, dict) or doc.get("format") != SIM_FORMAT or not isinstance(doc.get("simulation"), dict):
        raise ExternalSimIntegrityError(f"Simulation {sim_id} : format inconnu.")
    body = doc["simulation"]
    try:
        canonical = _container(body)
    except ValueError as exc:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} : contenu non canonique.") from exc
    if hashlib.sha256(canonical_json(body)).hexdigest() != doc.get("sha256"):
        raise ExternalSimIntegrityError(f"Simulation {sim_id} altérée : empreinte SHA-256 différente.")
    if canonical != raw:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} : octets non canoniques (fichier réécrit).")
    ident = body.get("identity") or {}
    if body.get("sim_id") != sim_id or hashlib.sha256(canonical_json(ident)).hexdigest()[:16] != sim_id:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} : identité incohérente avec son contenu.")
    sha = ident.get("source_sha256")
    srcs = list((_dir(root) / "sources").glob(f"{sha}.*")) if isinstance(sha, str) and len(sha) == 64 else []
    if not srcs or hashlib.sha256(srcs[0].read_bytes()).hexdigest() != sha:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} : fichier source d'origine absent ou modifié.")
    problems = semantic_problems(body)
    if problems:
        raise ExternalSimIntegrityError(f"Simulation {sim_id} incohérente : " + " ; ".join(problems))
    return body


def load(root: Path, sim_id: str) -> dict | None:
    p = _dir(root) / "simulations" / f"{sim_id}.json"
    if not p.exists():
        return None
    return verify(root, p.read_bytes(), sim_id)


def _summary(body: dict) -> dict:
    r = body.get("recomputed") or {}
    c = body.get("collapse") or {}
    return {"sim_id": body["sim_id"], "robot": body["robot"]["name"], "self_identification": body["robot"]["self_identification"],
            "symbol": body["environment"]["symbol"], "timeframe": body["environment"]["timeframe"],
            "server": body["environment"]["server"], "requested_period": body["environment"]["requested_period"],
            "observed_period": [body["period"]["first_deal"], body["period"]["last_deal"]],
            "ends_early": body["period"]["ends_early"], "net_profit": r.get("net_profit"),
            "total_trades": r.get("total_trades"), "balance_dd_maximal_pct": r.get("balance_dd_maximal_pct"),
            "collapse_drawdown": c.get("drawdown"), "behaviour": body["behaviour"]["verdict"]["code"],
            "validation": body["validation"]["status"], "source_name": body["source"]["name"],
            "source_format": body["source"]["format"], "config_key": body["config_key"], "test_key": body["test_key"],
            "inputs_sha256": body["identity"]["inputs_sha256"], "deals_sha256": body["identity"]["deals_sha256"]}


def list_simulations(root: Path) -> dict:
    d = _dir(root)
    log = []
    log_error = None
    try:
        log = _log_entries(d)
    except ExternalSimIntegrityError as exc:
        log_error = str(exc)
    first_seen = {}
    for e in log:
        first_seen.setdefault(e["sim_id"], e["at"])
    items = []
    for p in sorted((d / "simulations").glob("*.json")):
        try:
            s = _summary(verify(root, p.read_bytes(), p.stem))
            s["integrity"] = "vérifiée"
        except ExternalSimIntegrityError as exc:
            s = {"sim_id": p.stem, "integrity": "refusée", "integrity_error": str(exc)}
        s["imported_at"] = first_seen.get(p.stem)
        items.append(s)
    # same configuration, different deals = contradiction worth showing; same deals from several files = agreement
    by_config: dict[str, list[dict]] = {}
    for s in items:
        if s.get("integrity") == "vérifiée":
            by_config.setdefault(s["config_key"], []).append(s)
    for group in by_config.values():
        digests = {s["deals_sha256"] for s in group}
        for s in group:
            s["same_test_sources"] = sum(1 for o in group if o["deals_sha256"] == s["deals_sha256"])
            s["contradictory"] = len(digests) > 1
    robots: dict[str, int] = {}
    for s in items:
        if s.get("robot"):
            robots[s["robot"]] = robots.get(s["robot"], 0) + 1
    items.sort(key=lambda s: s.get("imported_at") or "", reverse=True)
    return {"simulations": items, "robots": [{"robot": k, "simulations": v} for k, v in sorted(robots.items())],
            "log_error": log_error}
