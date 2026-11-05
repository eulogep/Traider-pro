"""Filesystem locations (overridable with environment variables, e.g. in tests)."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return Path(os.environ.get("ATO_DATA_DIR", PROJECT_ROOT / "data" / "lab"))


def strategies_dir() -> Path:
    return Path(os.environ.get("ATO_STRATEGIES_DIR", PROJECT_ROOT / "strategies"))
