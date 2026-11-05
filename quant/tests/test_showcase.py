"""Static showcase: the exporter's file naming must match showcaseFile() in client/lib/quantApi.ts
(same cases as client/lib/showcase.spec.ts)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_showcase.py"
spec = importlib.util.spec_from_file_location("export_showcase", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CASES = [
    ("/health", "health.json"),
    ("/backtests/010f866522a4cdf7/equity?max_points=1500", "backtests__010f866522a4cdf7__equity--max_points-1500.json"),
    ("/external-sims/a45999a0c4a1b14f/what-if?rule=max_positions",
     "external-sims__a45999a0c4a1b14f__what-if--rule-max_positions.json"),
    ("/x?a=1&b=2", "x--a-1_b-2.json"),
]


def test_showcase_file_names_match_the_typescript_client():
    for path, name in CASES:
        assert mod.showcase_file(path) == name


def test_committed_showcase_covers_what_the_client_needs():
    data = Path(__file__).resolve().parents[2] / "showcase" / "data"
    manifest = (data / "manifest.json")
    assert manifest.exists(), "showcase/data absent : lancez « pnpm showcase:data »"
    import json
    m = json.loads(manifest.read_text())
    assert m["execution_mode"] == "simulation"
    for name, digest in m["files_sha256"].items():
        import hashlib
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest, name
    assert (data / "mt5__local-files.json").exists() and json.loads((data / "mt5__local-files.json").read_text())["available"] is False
