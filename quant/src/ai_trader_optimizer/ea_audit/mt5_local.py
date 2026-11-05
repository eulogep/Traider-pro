"""Read-only local bridge to the MetaTrader 5 terminal installed on this machine.

MT5 for macOS runs inside a Wine prefix whose ``drive_c`` is a normal folder. The Strategy Tester saves its
reports in the user's Documents folder by default, and MQL5 scripts can only write to ``MQL5/Files``. This module
LISTS report / export files found there and READS one on request. It never writes to the terminal, never
launches it, never sends an order, never reads credentials (``config/``, ``*.dat`` are not scanned).

Location: ``ATO_MT5_DIR`` (a ``drive_c`` folder or an MT5 data folder), otherwise the default macOS prefix.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MACOS = Path.home() / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c"
EXTENSIONS = (".htm", ".html", ".csv", ".xlsx", ".zip")
MAX_FILES = 200


def root() -> Path | None:
    env = os.environ.get("ATO_MT5_DIR")
    p = Path(env).expanduser() if env else DEFAULT_MACOS
    return p if p.is_dir() else None


def _folders(base: Path) -> list[tuple[str, Path]]:
    """(label, folder) pairs scanned — never the terminal's config or account files."""
    out: list[tuple[str, Path]] = []
    users = base / "users"
    if users.is_dir():
        for u in sorted(users.iterdir()):
            if (u / "Documents").is_dir():
                out.append((f"Documents ({u.name})", u / "Documents"))
    for term in [base / "Program Files" / "MetaTrader 5", base]:
        files = term / "MQL5" / "Files"
        if files.is_dir():
            out.append(("MQL5/Files", files))
            if (files / "ATO").is_dir():
                out.append(("MQL5/Files/ATO (export du script)", files / "ATO"))
    seen, uniq = set(), []
    for label, f in out:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            uniq.append((label, f))
    return uniq


def _id(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]


def list_files(max_bytes: int) -> dict:
    base = root()
    if base is None:
        return {"available": False, "root": None, "files": [],
                "note": "Aucun terminal MT5 trouvé sur cette machine (définissez ATO_MT5_DIR si besoin)."}
    files = []
    for label, folder in _folders(base):
        allowed = folder.resolve()
        for p in sorted(folder.iterdir()):
            if not p.is_file() or p.suffix.lower() not in EXTENSIONS:
                continue
            real = p.resolve()
            if real.parent != allowed:  # a symlink pointing elsewhere is not followed
                continue
            st = real.stat()
            files.append({"id": _id(real), "name": p.name, "folder": label, "bytes": st.st_size,
                          "too_large": st.st_size > max_bytes,
                          "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                          "_path": real})
    files.sort(key=lambda f: f["modified"], reverse=True)
    files = files[:MAX_FILES]
    return {"available": True, "root": str(base), "files": files,
            "note": "Lecture seule : fichiers listés dans les dossiers de rapports et d'export de MT5."}


def read_file(file_id: str, max_bytes: int) -> tuple[dict, bytes] | None:
    """Bytes of a LISTED file only (no path ever comes from the client)."""
    for f in list_files(max_bytes)["files"]:
        if f["id"] == file_id:
            if f["too_large"]:
                raise ValueError(f"Fichier trop volumineux ({f['bytes']} octets).")
            return f, f["_path"].read_bytes()
    return None


def public(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if not k.startswith("_")}
