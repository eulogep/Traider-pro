"""Runner of the pre-registered statistical campaign (PROTOCOL.md).

    cd quant
    .venv/bin/python research_campaign/run_campaign.py --phase before --src research_campaign/frozen/v0.4.0/src
    .venv/bin/python research_campaign/run_campaign.py --phase after  --src src

``--src`` selects WHICH copy of the application code is evaluated (the "before" phase runs on a frozen copy
of v0.4.0 so that later edits of the working tree cannot leak into it). Each replicate is one line of
``results/<phase>/<scenario>.jsonl``; the manifest records code hashes, versions, seeds and timings.
Only temporary catalogues are used; nothing is traded, no broker is contacted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN_SEED = 20261104
# replicates per family (fixed in PROTOCOL.md before any verdict was looked at)
REPS = {"codex": 1000, "null": 800, "e2e_null": 800, "search": 150, "power": 300}
CALIBRATION_REPS = 40
CALIBRATION_OFFSET = 1_000_000  # separate seed stream: calibration never reuses a campaign seed


def _setup(src: str) -> None:
    sys.path.insert(0, str(Path(src).resolve()))
    sys.path.insert(0, str(HERE))
    os.environ.setdefault("OMP_NUM_THREADS", "1")


def seeds_for(sc_index: int, rep: int) -> tuple[int, int]:
    """(data seed entropy, evaluation seed) — deterministic, documented in PROTOCOL.md."""
    import numpy as np
    ss = np.random.SeedSequence([CAMPAIGN_SEED, sc_index, rep])
    data, ev = ss.spawn(2)
    return int(data.generate_state(1, dtype=np.uint32)[0]) | (sc_index << 32) | (rep << 40), \
        int(ev.generate_state(1, dtype=np.uint32)[0])


def _zero_cost_config(params: dict | None = None):
    from ai_trader_optimizer.backtest.models import BacktestConfig, ExecutionCosts
    return BacktestConfig(costs=ExecutionCosts(spread=0.0, slippage=0.0, commission_per_lot_per_side=0.0),
                          strategy_params=params or {})


def _first_alpha(study_mod) -> float:
    fa = getattr(study_mod, "family_alpha", None)
    return float(fa(1)) if fa else 0.05  # v0.4.0: alpha = 0.05 / m, m = 1 for a first study


def _summary(res: dict) -> dict:
    f, b = res.get("filtered") or {}, res.get("baseline") or {}
    v = res["verdict"]
    return {"verdict": v["code"], "n_oos": res.get("n_oos"), "n_taken": res.get("n_taken"),
            "n_units_oos": (res.get("inference") or {}).get("n_units"),
            "block": (res.get("inference") or {}).get("block_length"),
            "baseline_mean_r": b.get("mean_r"), "baseline_ci": b.get("ci"),
            "filtered_mean_r": f.get("mean_r"), "filtered_ci": f.get("ci"),
            "auc": (res.get("auc") or {}).get("value")}


def _pipeline(ds, frame, sig, spec, cfg, settings, eval_seed, alpha):
    """prices → signals → labels → features → walk-forward → verdict, with the code under test."""
    import numpy as np
    from ai_trader_optimizer.research import features as F
    from ai_trader_optimizer.research import labels as L
    from ai_trader_optimizer.research import study as S
    labels = L.label_signals(ds, spec, cfg, sig, settings.horizon_bars)
    X = F.signal_features(ds.bars.reset_index(drop=True), labels, 0.0, 0.0, 0.0,
                          float(cfg.contract.contract_size))
    ok = X.notna().all(axis=1).to_numpy()
    labels, X = labels[ok].reset_index(drop=True), X[ok].reset_index(drop=True)
    pooled = {"n_labelled": int(len(labels)), "sum_r": float(labels["r"].sum()),
              "sum_r2": float((labels["r"] ** 2).sum())}
    if len(labels) == 0:
        return {"verdict": "INSUFFICIENT", **pooled}
    if hasattr(S, "evaluate_labelled"):  # v0.4.1+: the exact function run_edge_study uses
        res = S.evaluate_labelled(labels, X, settings, seed=eval_seed, alpha=alpha)
    else:  # v0.4.0: identical to the body of run_edge_study (checked by --check-equivalence)
        res = S.evaluate_signals(labels["entry_time"].astype("int64").to_numpy(),
                                 labels["exit_time"].astype("int64").to_numpy(), X.to_numpy(float),
                                 labels["r"].to_numpy(float), settings, seed=eval_seed, alpha=alpha)
    return {**_summary(res), **pooled, "alpha": alpha}


def run_one(task: tuple) -> dict:
    src, sc_dict, sc_index, rep, phase = task
    _setup(src)
    import numpy as np
    from scenarios import Scenario, baseline_signals, baseline_spec, codex_signals, frame_sha256, lattice_bars, \
        make_dataset, make_signals
    from ai_trader_optimizer.research import study as S
    sc = Scenario(**{**sc_dict, "q_hours": tuple(sc_dict["q_hours"]) if sc_dict.get("q_hours") else None})
    data_seed, eval_seed = seeds_for(sc_index, rep)
    t0 = time.time()
    out = {"scenario": sc.key, "rep": rep, "data_seed": data_seed, "eval_seed": eval_seed}
    try:
        if sc.family == "codex":
            seed = (100 if sc.codex_cluster == 1 else 400) + rep  # Codex's seeds, extended
            out.update(data_seed=seed, eval_seed=seed)
            res = S.evaluate_signals(*codex_signals(sc, np.random.default_rng(seed)), S.StudySettings(n_boot=300),
                                     seed=seed, alpha=_first_alpha(S))
            out.update(_summary(res))
            return {**out, "seconds": round(time.time() - t0, 3)}
        rng = np.random.default_rng(data_seed)
        frame, m_t = lattice_bars(sc, rng)
        out["frame_sha256"] = frame_sha256(frame)
        ds = make_dataset(sc, frame, f"rep{rep}")
        out["dataset_id"] = ds.meta.dataset_id
        spec = baseline_spec()
        if sc.family in ("null", "power"):
            sig = make_signals(sc, frame, m_t, rng)
            out.update(_pipeline(ds, frame, sig, spec, _zero_cost_config(), S.StudySettings(), eval_seed,
                                 _first_alpha(S)))
        elif sc.family == "e2e_null":
            from ai_trader_optimizer.storage import LabCatalog
            with tempfile.TemporaryDirectory() as tmp:
                cat = LabCatalog(tmp)
                cat.save_dataset(ds)
                st = S.run_edge_study(cat, ds.meta.dataset_id, spec, _zero_cost_config(), S.StudySettings())
                out.update(_summary(st["result"]))
                out.update(study_id=st["study_id"], alpha=st["multiple_testing"]["alpha"],
                           n_labelled=st["signals"]["labelled"])
        elif sc.family == "search":
            from scenarios import SEARCH_VARIANTS
            from ai_trader_optimizer.storage import LabCatalog
            shared, fresh = [], []
            with tempfile.TemporaryDirectory() as tmp:
                cat = LabCatalog(tmp)
                cat.save_dataset(ds)
                for v in SEARCH_VARIANTS:  # the app's own multiplicity rule (same catalogue, in order)
                    st = S.run_edge_study(cat, ds.meta.dataset_id, spec, _zero_cost_config(v["params"]),
                                          S.StudySettings(horizon_bars=v["horizon_bars"]))
                    shared.append({"verdict": st["result"]["verdict"]["code"], "alpha": st["multiple_testing"]["alpha"],
                                   "n_oos": st["result"].get("n_oos")})
            for v in SEARCH_VARIANTS:  # no correction at all: every analysis treated as the first one
                with tempfile.TemporaryDirectory() as tmp:
                    cat = LabCatalog(tmp)
                    cat.save_dataset(ds)
                    st = S.run_edge_study(cat, ds.meta.dataset_id, spec, _zero_cost_config(v["params"]),
                                          S.StudySettings(horizon_bars=v["horizon_bars"]))
                    fresh.append(st["result"]["verdict"]["code"])
            out.update(shared=shared, fresh=fresh, any_edge_shared=any(s["verdict"] == "EDGE" for s in shared),
                       any_edge_fresh=any(f == "EDGE" for f in fresh), verdict="SEARCH")
        else:
            raise ValueError(sc.family)
    except Exception as exc:  # recorded, never silently dropped
        out.update(verdict="ERROR", error=f"{type(exc).__name__}: {exc}")
    out["seconds"] = round(time.time() - t0, 3)
    return out


def calibrate(src: str, scenarios, workers: int) -> dict:
    """Power scenarios: E[R] = (2q − 1) × A with symmetric barriers; A = pooled mean R at q = 1 (pilot,
    separate seed stream). q = 0.5 + target / (2A). Only pooled means are used — never a verdict."""
    _setup(src)
    out = {}
    tasks = []
    for i, sc in enumerate(scenarios):
        if sc.family != "power":
            continue
        pilot = replace(sc, q=1.0)
        for rep in range(CALIBRATION_REPS):
            tasks.append((src, pilot.as_dict(), i, CALIBRATION_OFFSET + rep, "calibration"))
    with mp.get_context("spawn").Pool(workers) as pool:
        rows = pool.map(run_one, tasks, chunksize=1)
    for sc in scenarios:
        if sc.family != "power":
            continue
        rs = [r for r in rows if r["scenario"] == sc.key and r.get("n_labelled")]
        n = sum(r["n_labelled"] for r in rs)
        A = sum(r["sum_r"] for r in rs) / n
        target = sc.extra.get("target_r", sc.extra.get("target_r_informative"))
        q = min(1.0, 0.5 + target / (2 * A))
        out[sc.key] = {"A_pooled_mean_r_at_q1": A, "n_signals": n, "target": target, "q": q,
                       "errors": sum(r["verdict"] == "ERROR" for r in rows if r["scenario"] == sc.key)}
    return out


def env_record(src: str) -> dict:
    _setup(src)
    from ai_trader_optimizer import ENGINE_VERSION, __version__
    from ai_trader_optimizer.research.study import research_code_hash
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    import numpy
    import pandas
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except OSError:
        head = None
    srch = hashlib.sha256()
    for p in sorted(Path(src, "ai_trader_optimizer").rglob("*.py")):
        srch.update(str(p.relative_to(src)).encode())
        srch.update(p.read_bytes())
    return {"software_version": __version__, "engine_version": ENGINE_VERSION,
            "research_code_hash": research_code_hash(), "src": str(Path(src).resolve()),
            "src_tree_sha256": srch.hexdigest(), "python": sys.version, "platform": platform.platform(),
            "numpy": numpy.__version__, "pandas": pandas.__version__, "git_head": head,
            "pip_freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest(), "pip_freeze": freeze.splitlines()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--only", nargs="*", help="scenario keys (default: all)")
    ap.add_argument("--reps", type=int, help="override (timing/pilot only — not a campaign run)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--calibration", help="reuse this calibration.json (the after phase reuses the before one)")
    a = ap.parse_args()
    _setup(a.src)
    from scenarios import SCENARIOS
    out_dir = HERE / "results" / a.phase
    out_dir.mkdir(parents=True, exist_ok=True)
    scen = [s for s in SCENARIOS if not a.only or s.key in a.only]
    manifest = {"phase": a.phase, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "campaign_seed": CAMPAIGN_SEED, "reps": REPS, "override_reps": a.reps, "env": env_record(a.src),
                "protocol_sha256": hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest()
                if (HERE / "PROTOCOL.md").exists() else None,
                "scenarios_py_sha256": hashlib.sha256((HERE / "scenarios.py").read_bytes()).hexdigest(),
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if any(s.family == "power" for s in scen):
        if a.calibration:
            cal = json.loads(Path(a.calibration).read_text())
        else:
            cal = calibrate(a.src, [s for s in SCENARIOS], a.workers)
        (out_dir / "calibration.json").write_text(json.dumps(cal, indent=1))
        manifest["calibration"] = cal
    index = {s.key: i for i, s in enumerate(SCENARIOS)}
    tasks = []
    for sc in scen:
        if sc.family == "power":
            sc = replace(sc, q=manifest["calibration"][sc.key]["q"])
        for rep in range(a.reps or REPS[sc.family]):
            tasks.append((a.src, sc.as_dict(), index[sc.key], rep, a.phase))
    files = {sc.key: open(out_dir / f"{sc.key}.jsonl", "w") for sc in scen}
    t0 = time.time()
    done = 0
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for row in pool.imap_unordered(run_one, tasks, chunksize=1):
            files[row["scenario"]].write(json.dumps(row, default=str) + "\n")
            files[row["scenario"]].flush()
            done += 1
            if done % 200 == 0:
                print(f"{done}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    for f in files.values():
        f.close()
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["seconds"] = round(time.time() - t0, 1)
    manifest["outputs_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(out_dir.glob("*.jsonl"))}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("done", manifest["seconds"], "s")


if __name__ == "__main__":
    main()
