"""Supplementary experiments declared in PROTOCOL.md §9, deviation 4 (written AFTER the "before" results were
read, BEFORE any "after" result existed). Imports the sealed runner and scenarios; changes neither.

4c — blind correlated nulls  N10b / N11b: the exact N10 / N11 data, signals and outcomes (same scenario index,
     same seeds), but the feature rows are permuted at random across signals before learning. Outcome
     dependence is kept, predictability is destroyed: E[filtered R] = 0 exactly.
4d — H1 sensitivity: Politis–White block length × 0.5 and × 2 (then bounded to [1, min(3√n, n/3)]) on
     N5, N9, N11 (and N11b), 300 replicates, cluster method only. Published, never used to choose.

    cd quant
    .venv/bin/python research_campaign/run_supplement.py --part blind --src research_campaign/frozen/v0.4.0/src --tag v0.4.0
    .venv/bin/python research_campaign/run_supplement.py --part blind --src research_campaign/frozen/v0.4.1/src --tag v0.4.1
    .venv/bin/python research_campaign/run_supplement.py --part sensitivity --src research_campaign/frozen/v0.4.1/src --tag v0.4.1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PERMUTATION_SALT = 4_0003  # fixed in deviation 4: permutation rng = default_rng([eval_seed, PERMUTATION_SALT])
BLIND = {"N10b_corr_2h_blind": "N10_corr_2h", "N11b_corr_1d_blind": "N11_corr_1d"}
BLIND_REPS = 800
SENS_KEYS = ["N5_burst60", "N9_stochvol_burst30", "N11_corr_1d", "N11b_corr_1d_blind"]
SENS_SCALES = [0.5, 2.0]
SENS_REPS = 300
SCALED_LOG: list = []  # (Politis–White block, scaled block) of the current task — recorded in each row


def _scale_blocks(scale: float) -> None:
    from ai_trader_optimizer.research import inference as I
    # worker processes are reused across tasks: wrap the ORIGINAL function exactly once per call (deviation 5 —
    # the first version re-wrapped the wrapper on every task, compounding the scale)
    orig = I.__dict__.setdefault("_original_politis_white_block", I.politis_white_block)

    def scaled(x):
        n = len(x)
        b_max = max(1, int(math.ceil(min(3 * math.sqrt(n), n / 3)))) if n >= 8 else 1
        b = int(min(max(1, round(orig(x) * scale)), b_max))
        SCALED_LOG.append((int(orig(x)), b))
        return b
    I.politis_white_block = scaled


def run_one(task: tuple) -> dict:
    src, key, base_key, rep, blind, scale = task
    import run_campaign as RC
    RC._setup(src)
    import numpy as np
    from scenarios import BY_KEY, SCENARIOS, lattice_bars, make_dataset, make_signals
    from ai_trader_optimizer.research import features as F
    from ai_trader_optimizer.research import labels as L
    from ai_trader_optimizer.research import study as S
    from ai_trader_optimizer.research import inference as _I
    if "_original_politis_white_block" in _I.__dict__:
        _I.politis_white_block = _I._original_politis_white_block
    if scale != 1.0:
        _scale_blocks(scale)
    sc = BY_KEY[base_key]
    sc_index = [s.key for s in SCENARIOS].index(base_key)
    data_seed, eval_seed = RC.seeds_for(sc_index, rep)  # identical to the main campaign's replicate
    t0 = time.time()
    out = {"scenario": key, "base_scenario": base_key, "rep": rep, "data_seed": data_seed, "eval_seed": eval_seed,
           "blind": blind, "block_scale": scale}
    try:
        rng = np.random.default_rng(data_seed)
        frame, m_t = lattice_bars(sc, rng)
        from scenarios import frame_sha256
        out["frame_sha256"] = frame_sha256(frame)
        ds = make_dataset(sc, frame, f"rep{rep}")
        out["dataset_id"] = ds.meta.dataset_id
        sig = make_signals(sc, frame, m_t, rng)
        from scenarios import baseline_spec
        spec, cfg, settings, alpha = baseline_spec(), RC._zero_cost_config(), S.StudySettings(), RC._first_alpha(S)
        labels = L.label_signals(ds, spec, cfg, sig, settings.horizon_bars)
        X = F.signal_features(ds.bars.reset_index(drop=True), labels, 0.0, 0.0, 0.0, float(cfg.contract.contract_size))
        ok = X.notna().all(axis=1).to_numpy()
        labels, X = labels[ok].reset_index(drop=True), X[ok].reset_index(drop=True)
        out.update(n_labelled=int(len(labels)), sum_r=float(labels["r"].sum()), sum_r2=float((labels["r"] ** 2).sum()))
        if blind:  # destroy predictability, keep the outcomes (and their temporal dependence) untouched
            perm = np.random.default_rng([eval_seed, PERMUTATION_SALT]).permutation(len(X))
            X = X.iloc[perm].reset_index(drop=True)
        if len(labels) == 0:
            out["verdict"] = "INSUFFICIENT"
        elif hasattr(S, "evaluate_labelled"):
            out.update(RC._summary(S.evaluate_labelled(labels, X, settings, seed=eval_seed, alpha=alpha)))
        else:
            out.update(RC._summary(S.evaluate_signals(
                labels["entry_time"].astype("int64").to_numpy(), labels["exit_time"].astype("int64").to_numpy(),
                X.to_numpy(float), labels["r"].to_numpy(float), settings, seed=eval_seed, alpha=alpha)))
        out["alpha"] = alpha
        if SCALED_LOG:
            out["pw_block_unscaled"], out["pw_block_scaled"] = SCALED_LOG[-1]
        SCALED_LOG.clear()
    except Exception as exc:  # recorded, never dropped
        out.update(verdict="ERROR", error=f"{type(exc).__name__}: {exc}")
    out["seconds"] = round(time.time() - t0, 3)
    return out


def main() -> None:
    import sys
    sys.path.insert(0, str(HERE))
    import run_campaign as RC
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["blind", "sensitivity"], required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    RC._setup(a.src)
    tasks = []
    if a.part == "blind":
        for key, base in BLIND.items():
            tasks += [(a.src, key, base, rep, True, 1.0) for rep in range(BLIND_REPS)]
    else:
        for scale in SENS_SCALES:
            for key in SENS_KEYS:
                base, blind = BLIND.get(key, key), key in BLIND
                tasks += [(a.src, f"{key}__x{scale}", base, rep, blind, scale) for rep in range(SENS_REPS)]
    out_dir = HERE / "results" / f"supp_{a.part}_{a.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"part": a.part, "tag": a.tag, "src": a.src, "env": RC.env_record(a.src),
                "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "permutation_salt": PERMUTATION_SALT, "blind_reps": BLIND_REPS, "sens_reps": SENS_REPS,
                "sens_scales": SENS_SCALES, "sens_keys": SENS_KEYS,
                "protocol_sha256": hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest(),
                "supplement_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "runner_sha256": hashlib.sha256((HERE / "run_campaign.py").read_bytes()).hexdigest(),
                "scenarios_py_sha256": hashlib.sha256((HERE / "scenarios.py").read_bytes()).hexdigest()}
    keys = sorted({t[1] for t in tasks})
    files = {k: open(out_dir / f"{k}.jsonl", "w") for k in keys}
    t0, done = time.time(), 0
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
