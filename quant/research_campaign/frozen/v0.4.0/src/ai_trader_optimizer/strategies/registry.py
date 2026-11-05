"""Load versioned strategy specs from YAML and build runnable strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ..paths import strategies_dir
from .base import Strategy, StrategySpec
from .ema_trend_3bars import EmaTrend3Bars

IMPLEMENTATIONS: dict[str, type[Strategy]] = {EmaTrend3Bars.implementation: EmaTrend3Bars}


class StrategyNotRunnableError(ValueError):
    pass


@dataclass
class Catalog:
    specs: dict[str, StrategySpec] = field(default_factory=dict)  # key = id@version
    paths: dict[str, Path] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)  # file -> validation error

    def by_category(self, category: str) -> list[StrategySpec]:
        return [s for s in self.specs.values() if s.category == category]

    def runnable(self) -> list[StrategySpec]:
        return [s for s in self.specs.values() if not s.runnable_problems() and s.implementation in IMPLEMENTATIONS]


def load_spec(path: str | Path) -> StrategySpec:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return StrategySpec.model_validate(data)


def load_catalog(root: str | Path | None = None) -> Catalog:
    root = Path(root) if root else strategies_dir()
    cat = Catalog()
    for path in sorted(root.rglob("*.yaml")):
        try:
            spec = load_spec(path)
        except (ValidationError, yaml.YAMLError, ValueError) as exc:
            cat.errors[str(path.relative_to(root))] = str(exc)
            continue
        if spec.key in cat.specs:
            cat.errors[str(path.relative_to(root))] = f"duplicate strategy key {spec.key}"
            continue
        cat.specs[spec.key] = spec
        cat.paths[spec.key] = path
    return cat


def build_strategy(spec: StrategySpec, overrides: dict[str, Any] | None = None) -> Strategy:
    problems = spec.runnable_problems()
    if spec.implementation and spec.implementation not in IMPLEMENTATIONS:
        problems.append(f"implémentation inconnue : {spec.implementation}")
    if problems:
        raise StrategyNotRunnableError(f"{spec.key} non exécutable : " + " ; ".join(problems))
    cls = IMPLEMENTATIONS[spec.implementation]
    return cls(spec, spec.resolve_params(overrides))
