"""Application services used by the UI (and usable from scripts/tests)."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from .ai.validation import chronological_split
from .backtest import BacktestConfig, BacktestResult, run_backtest
from .risk.guardian import XAUUSD_HYPOTHETICAL, RiskConfig
from .storage import LabCatalog
from .strategies import Catalog, StrategySpec

DEFAULT_SETTINGS_KEY = "defaults"
RISK_SETTINGS_KEY = "risk"


def default_config(cat: LabCatalog) -> BacktestConfig:
    """Saved Settings + Risk profile, falling back to documented defaults."""
    base = BacktestConfig(contract=XAUUSD_HYPOTHETICAL.model_copy())
    saved = cat.get_setting(DEFAULT_SETTINGS_KEY) or {}
    risk = cat.get_setting(RISK_SETTINGS_KEY)
    data = base.model_dump(mode="json")
    for k in ("initial_equity", "account_currency", "costs", "contract"):
        if k in saved:
            data[k] = saved[k]
    if risk:
        data["risk"] = risk
    return BacktestConfig.model_validate(data)


def save_defaults(cat: LabCatalog, config: BacktestConfig) -> None:
    d = config.model_dump(mode="json")
    cat.set_setting(DEFAULT_SETTINGS_KEY, {k: d[k] for k in ("initial_equity", "account_currency", "costs", "contract")})


def save_risk(cat: LabCatalog, risk: RiskConfig) -> None:
    cat.set_setting(RISK_SETTINGS_KEY, risk.model_dump(mode="json"))


class RiskPolicyViolation(PermissionError):
    """The request loosens a limit that the server-side policy enforces (supervised mode)."""


POLICY_MODES = ("research", "supervised")


def policy_mode() -> str:
    """Server-side policy, chosen by whoever runs the API (env), never by the caller.

    * ``research`` (default): risk limits and contract are research HYPOTHESES the caller may change;
      results say so explicitly (``risk_policy.enforced = false``).
    * ``supervised``: the saved risk profile and contract are ENFORCED — a request may only be
      stricter. Required before any future supervised or execution mode.
    """
    mode = os.environ.get("ATO_RISK_POLICY", "research").strip().lower()
    if mode not in POLICY_MODES:
        raise RuntimeError(f"ATO_RISK_POLICY invalide : {mode!r} (attendu : {', '.join(POLICY_MODES)})")
    return mode


def _looser(req: RiskConfig, saved: RiskConfig) -> list[str]:
    out = []
    for f in ("risk_per_trade_pct", "max_daily_loss_pct", "max_drawdown_pct", "max_trades_per_day"):
        if getattr(req, f) > getattr(saved, f):
            out.append(f"{f} {getattr(req, f)} > {getattr(saved, f)}")
    for f in ("max_losses_per_day", "max_consecutive_losses"):
        a, b = getattr(req, f), getattr(saved, f)
        if b is not None and (a is None or a > b):
            out.append(f"{f} {a} plus permissif que {b}")
    for f in ("daily_limit_includes_planned_risk", "drawdown_limit_includes_planned_risk", "stop_after_daily_win"):
        if getattr(saved, f) and not getattr(req, f):
            out.append(f"{f} désactivé")
    if saved.consecutive_loss_scope == "run" and req.consecutive_loss_scope == "day":
        out.append("consecutive_loss_scope day au lieu de run")
    if req.day_timezone != saved.day_timezone:
        out.append("day_timezone différent")
    return out


def resolve_risk_policy(cat: LabCatalog, config: BacktestConfig) -> dict:
    mode = policy_mode()
    saved = default_config(cat)
    differs = config.risk != saved.risk or config.contract != saved.contract
    if mode == "supervised":
        problems = _looser(config.risk, saved.risk)
        if config.contract != saved.contract:
            problems.append("contrat différent du contrat enregistré")
        if config.account_currency != saved.account_currency:
            problems.append("devise du compte différente")
        if problems:
            raise RiskPolicyViolation("Mode supervisé : la politique de risque enregistrée est imposée ; refus : "
                                      + " ; ".join(problems))
    return {"mode": mode, "enforced": mode == "supervised", "differs_from_saved_profile": differs,
            "saved_profile": saved.risk.model_dump(mode="json"),
            "note": "Limites imposées par le serveur (au plus aussi permissives que le profil enregistré)."
            if mode == "supervised" else
            "Mode recherche : limites et contrat sont des hypothèses modifiables, pas une politique imposée."}


def run_and_store(cat: LabCatalog, dataset_id: str, spec: StrategySpec, config: BacktestConfig,
                  label: str = "") -> BacktestResult:
    policy = resolve_risk_policy(cat, config)  # before any simulation (I2)
    ds = cat.load_dataset(dataset_id)
    result = run_backtest(ds, spec, config)
    result.manifest["risk_policy"] = policy
    cat.save_run(result, label=label)
    return result


def reproduce(cat: LabCatalog, run_id: str, strategies: Catalog) -> dict:
    """Two separate questions, two separate answers:

    * ``artifacts_intact`` — the stored files pass verification (checksums, digest, consistency).
      ``load_run`` raises ``CorruptRunError`` otherwise, so a damaged run never reaches the comparison.
    * ``deterministic`` — re-running the engine on the same inputs yields the same result fingerprint
      as the one computed from the VERIFIED stored artefacts (not merely the declared manifest value).
    ``identical`` = both.
    """
    stored_run = cat.load_run(run_id)  # verified read
    stored = stored_run.manifest
    spec = strategies.specs.get(stored["strategy"]["key"])
    if spec is None:
        raise KeyError(f"Stratégie {stored['strategy']['key']} introuvable")
    if spec.spec_hash() != stored["strategy"]["spec_hash"]:
        raise ValueError("La spécification de la stratégie a changé depuis ce run (empreinte différente) : "
                         "créez une nouvelle version au lieu de modifier une version existante.")
    from .backtest.codehash import code_fingerprint
    if stored.get("code_hash") and stored["code_hash"] != code_fingerprint():
        raise ValueError(f"Le code du moteur/des stratégies a changé depuis ce run (empreinte {stored['code_hash']} ≠ "
                         f"{code_fingerprint()}) : relancez un nouveau run plutôt que de comparer.")
    # load_run already checked that this declared value equals the fingerprint of the bytes read.
    stored_hash = stored["result_hash"]
    ds = cat.load_dataset(stored["dataset"]["dataset_id"])
    res = run_backtest(ds, spec, BacktestConfig.model_validate(stored["config"]))
    deterministic = res.manifest["result_hash"] == stored_hash
    return {"identical": deterministic, "deterministic": deterministic, "artifacts_intact": True,
            "stored_hash": stored_hash, "new_hash": res.manifest["result_hash"]}


def compare_variants(cat: LabCatalog, dataset_id: str, spec: StrategySpec, base: BacktestConfig,
                     param: str, values: list[Any], train_fraction: float = 0.7) -> pd.DataFrame:
    """Same data, same costs, same risk; in-sample vs out-of-sample shown separately.

    Selecting the 'best' variant from the out-of-sample column turns it into
    in-sample data: the UI warns about this.
    """
    ds = cat.load_dataset(dataset_id)
    t = ds.bars["timestamp"]
    # IS: bars closing <= cut ; OOS: executions at opens >= cut (warm-up may read earlier bars) — see Split.
    split = chronological_split(t.iloc[0], t.iloc[-1] + pd.Timedelta(seconds=ds.bar_seconds), train_fraction)
    rows = []
    for v in values:
        params = {**base.strategy_params, param: v}
        for seg, start, end in (("in-sample", None, split.train_end), ("hors échantillon", split.test_start, None)):
            cfg = base.model_copy(update={"strategy_params": params,
                                          "trade_start": None if start is None else start.isoformat(),
                                          "trade_end": None if end is None else end.isoformat()})
            r = run_backtest(ds, spec, cfg)
            m = r.metrics
            win = r.manifest["evaluation_window"]
            rows.append({"param": param, "valeur": v, "segment": seg,
                         "evaluated_from": win["first_evaluated_bar_open"],
                         "evaluated_until": win["last_evaluated_bar_close"], "trades": m["trades"],
                         "net_pnl": m["net_pnl"], "win_rate_pct": m["win_rate_pct"],
                         "profit_factor": m["profit_factor"], "expectancy_r": m.get("expectancy_r"),
                         "max_dd_mtm_pct": m["max_dd_mtm_pct"], "échantillon_suffisant": m["sample_sufficient"]})
    return pd.DataFrame(rows)
