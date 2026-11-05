"""Pre-registered analysis of the campaign (PROTOCOL.md §2). Standard library + numpy only.

    .venv/bin/python research_campaign/analyze.py            # every phase found in results/
Writes results/summary_<phase>.json, results/REPORT_<phase>.md and, when both exist, results/COMPARISON.md.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REFERENCE = 0.05
K_NULL_TESTS = 15
LEVEL = 0.05 / K_NULL_TESTS
POWER_ACCEPT = 0.80  # P3 must reach this after a correction
# PROTOCOL.md §9 deviation 4b: N10/N11 are not nulls for the FILTERED mean (real conditional edge, measured).
MISSPECIFIED_NULLS = ("N10_corr_2h", "N11_corr_1d")
K_SUPP_BLIND = 2  # deviation 4c: own Bonferroni over N10b / N11b


def _log_pmf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p)
            + (n - k) * math.log1p(-p))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Bin(n, p)."""
    if k <= 0:
        return 1.0
    return min(1.0, sum(math.exp(_log_pmf(i, n, p)) for i in range(k, n + 1)))


def binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    return min(1.0, sum(math.exp(_log_pmf(i, n, p)) for i in range(0, k + 1)))


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Exact equal-tailed interval by inversion of the binomial distribution (bisection)."""
    if n == 0:
        return (0.0, 1.0)
    a = (1 - conf) / 2

    def solve(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    low = 0.0 if k == 0 else solve(lambda p: binom_cdf(k - 1, n, p), 1 - a)
    high = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p), a)
    return low, high


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _pooled(rows: list[dict]) -> dict:
    """True mean R of the scenario: replicate means are independent -> mean ± 1.96 SE across replicates."""
    import numpy as np
    rows = [r for r in rows if r.get("n_labelled") and "sum_r" in r]  # E1 (run_edge_study) has no sum_r
    means = [r["sum_r"] / r["n_labelled"] for r in rows]
    if len(means) < 2:
        return {"replicate_mean_r": None, "ci95": None, "n_rep": len(means)}
    m = float(np.mean(means))
    se = float(np.std(means, ddof=1) / math.sqrt(len(means)))
    tot = sum(r["n_labelled"] for r in rows if r.get("n_labelled"))
    return {"replicate_mean_r": m, "ci95": [m - 1.96 * se, m + 1.96 * se], "n_rep": len(means),
            "pooled_mean_r": sum(r["sum_r"] for r in rows if r.get("n_labelled")) / tot,
            "mean_signals_per_rep": tot / len(means)}


def _filtered_effect(rows: list[dict]) -> dict | None:
    """Replicate mean of the OUT-OF-SAMPLE filtered mean R (what EDGE judges) ± 1.96 SE across replicates."""
    import numpy as np
    x = [r["filtered_mean_r"] for r in rows if r.get("filtered_mean_r") is not None]
    if len(x) < 2:
        return None
    m, se = float(np.mean(x)), float(np.std(x, ddof=1) / math.sqrt(len(x)))
    return {"mean": m, "ci95": [m - 1.96 * se, m + 1.96 * se], "n_rep": len(x)}


def _rate(k: int, n: int, level: float | None = None) -> dict:
    lo, hi = clopper_pearson(k, n)
    p = binom_sf(k, n, REFERENCE)
    lv = LEVEL if level is None else level
    return {"k": k, "n": n, "rate": k / n if n else None, "ci95": [lo, hi], "p_vs_5pct": p,
            "significant_excess": bool(n and p < lv),
            "judgement": ("DÉPASSEMENT SIGNIFICATIF de 5 %" if n and p < lv else "compatible avec ≤ 5 %")}


def summarise(phase: str) -> dict:
    from scenarios import BY_KEY
    d = HERE / "results" / phase
    out = {"phase": phase, "manifest": json.loads((d / "manifest.json").read_text()) if (d / "manifest.json").exists()
           else None, "scenarios": {}}
    if out["manifest"]:
        out["manifest"].get("env", {}).pop("pip_freeze", None)
    for f in sorted(d.glob("*.jsonl")):
        key = f.stem
        sc = BY_KEY.get(key)
        rows = _rows(f)
        errors = [r for r in rows if r.get("verdict") == "ERROR"]
        valid = [r for r in rows if r.get("verdict") != "ERROR"]
        rec = {"family": sc.family if sc else None, "description": sc.description if sc else None,
               "n_rows": len(rows), "errors": len(errors),
               "error_examples": sorted({e.get("error", "")[:160] for e in errors})[:3]}
        if sc and sc.family == "search":
            rec["fwer_shared"] = _rate(sum(bool(r["any_edge_shared"]) for r in valid), len(valid))
            rec["fwer_uncorrected"] = _rate(sum(bool(r["any_edge_fresh"]) for r in valid), len(valid))
            nv = len(valid[0]["shared"]) if valid else 0
            rec["per_variant_edge_rate_shared"] = [sum(r["shared"][i]["verdict"] == "EDGE" for r in valid) / len(valid)
                                                   for i in range(nv)] if valid else []
            rec["alpha_by_rank"] = [valid[0]["shared"][i]["alpha"] for i in range(nv)] if valid else []
        else:
            verdicts: dict[str, int] = {}
            for r in valid:
                verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
            rec["verdicts"] = verdicts
            rec["edge"] = _rate(verdicts.get("EDGE", 0), len(valid))
            if sc and sc.family != "codex":
                rec["true_effect"] = _pooled(valid)
            rec["filtered_effect"] = _filtered_effect(valid)
            units = [r["n_units_oos"] for r in valid if r.get("n_units_oos")]
            rec["median_n_oos"] = sorted(r["n_oos"] for r in valid if r.get("n_oos") is not None)[len(valid) // 2] \
                if valid else None
            rec["median_units_oos"] = sorted(units)[len(units) // 2] if units else None
        out["scenarios"][key] = rec
    nulls = [k for k, v in out["scenarios"].items() if v["family"] in ("codex", "null", "e2e_null", "search")]
    out["defect_established"] = any(
        (v.get("edge") or v.get("fwer_shared") or {}).get("significant_excess") for k, v in out["scenarios"].items()
        if k in nulls)
    p3 = out["scenarios"].get("P3_edge_020", {}).get("edge", {}).get("rate")
    out["power_p3"] = p3
    out["acceptance"] = (not out["defect_established"]) and p3 is not None and p3 >= POWER_ACCEPT
    valid_nulls = [k for k in nulls if k not in MISSPECIFIED_NULLS]
    out["defect_valid_nulls"] = any(
        (out["scenarios"][k].get("edge") or out["scenarios"][k].get("fwer_shared") or {}).get("significant_excess")
        for k in valid_nulls)
    out["acceptance_valid_nulls"] = (not out["defect_valid_nulls"]) and p3 is not None and p3 >= POWER_ACCEPT
    return out


def _pct(x):
    return "—" if x is None else f"{100 * x:.1f} %".replace(".", ",")


def report(s: dict) -> str:
    L = [f"# Campagne — phase « {s['phase']} »", ""]
    env = (s.get("manifest") or {}).get("env", {})
    if env:
        L += [f"Code évalué : `{env.get('src')}` · version {env.get('software_version')} · "
              f"`research_code_hash = {env.get('research_code_hash')}` · arbre source SHA-256 "
              f"`{env.get('src_tree_sha256', '')[:16]}…` · numpy {env.get('numpy')} · pandas {env.get('pandas')}", ""]
    L += [f"Référence 5 % ; dépassement significatif si p < 0,05/{K_NULL_TESTS} = {LEVEL:.5f} (binomial exact "
          "unilatéral) ; intervalles de Clopper–Pearson à 95 %.", "",
          "| Scénario | Famille | N | EDGE | Taux | IC 95 % | p (H0 ≤ 5 %) | Jugement | Effet vrai (R/signal, IC 95 %) | Autres verdicts | Erreurs |",
          "|---|---|---:|---:|---:|---|---:|---|---|---|---:|"]
    for k, v in s["scenarios"].items():
        if "edge" in v:
            e, te = v["edge"], v.get("true_effect") or {}
            eff = "—" if not te.get("ci95") else f"{te['replicate_mean_r']:+.4f} [{te['ci95'][0]:+.4f} ; {te['ci95'][1]:+.4f}]"
            other = ", ".join(f"{a}:{b}" for a, b in sorted(v["verdicts"].items()) if a != "EDGE")
            jug = e["judgement"] if v["family"] != "power" else "(puissance)"
            L.append(f"| {k} | {v['family']} | {e['n']} | {e['k']} | {_pct(e['rate'])} | [{_pct(e['ci95'][0])} ; "
                     f"{_pct(e['ci95'][1])}] | {e['p_vs_5pct']:.2g} | {jug} | {eff} | {other} | {v['errors']} |")
        else:
            for lab in ("fwer_shared", "fwer_uncorrected"):
                e = v[lab]
                L.append(f"| {k} · {'règle α de l’application' if lab == 'fwer_shared' else 'sans correction'} | "
                         f"essais multiples | {e['n']} | {e['k']} | {_pct(e['rate'])} | [{_pct(e['ci95'][0])} ; "
                         f"{_pct(e['ci95'][1])}] | {e['p_vs_5pct']:.2g} | "
                         f"{e['judgement'] if lab == 'fwer_shared' else '(référence)'} | — | — | {v['errors']} |")
    L += ["", f"**Défaut établi (au moins un dépassement significatif) : {'OUI' if s['defect_established'] else 'NON'}.** "
          f"Puissance P3 (≈ +0,20 R) : {_pct(s['power_p3'])}.",
          f"Lecture écart 4b (13 nuls valides, sans {', '.join(MISSPECIFIED_NULLS)}) : dépassement "
          f"{'OUI' if s['defect_valid_nulls'] else 'NON'}.", "",
          "Effet filtré hors échantillon (ce que juge `EDGE`), moyenne des réplications [IC 95 %] :", ""]
    for k, v in s["scenarios"].items():
        fe = v.get("filtered_effect")
        if fe:
            L.append(f"- {k} : {fe['mean']:+.4f} R [{fe['ci95'][0]:+.4f} ; {fe['ci95'][1]:+.4f}] (n = {fe['n_rep']})")
    return "\n".join(L) + "\n"


def comparison(a: dict, b: dict) -> str:
    L = ["# Comparaison avant / après (mêmes scénarios, mêmes graines)", "",
         "| Scénario | Famille | Avant : taux EDGE [IC 95 %] | Après : taux EDGE [IC 95 %] | Avant : jugement | Après : jugement |",
         "|---|---|---|---|---|---|"]
    for k in a["scenarios"]:
        va, vb = a["scenarios"][k], b["scenarios"].get(k)
        if not vb:
            continue
        for lab in (("edge",) if "edge" in va else ("fwer_shared", "fwer_uncorrected")):
            ea, eb = va[lab], vb[lab]
            name = k if lab == "edge" else f"{k} · {lab}"
            fam = va["family"]
            ja = ea["judgement"] if fam != "power" else "(puissance)"
            jb = eb["judgement"] if fam != "power" else "(puissance)"
            L.append(f"| {name} | {fam} | {_pct(ea['rate'])} [{_pct(ea['ci95'][0])} ; {_pct(ea['ci95'][1])}] | "
                     f"{_pct(eb['rate'])} [{_pct(eb['ci95'][0])} ; {_pct(eb['ci95'][1])}] | {ja} | {jb} |")
    L += ["", f"Défaut établi — avant : {'OUI' if a['defect_established'] else 'NON'} ; après : "
          f"{'OUI' if b['defect_established'] else 'NON'}. Puissance P3 — avant : {_pct(a['power_p3'])} ; après : "
          f"{_pct(b['power_p3'])}. Critère d'acceptation de la correction (§2) : "
          f"{'REMPLI' if b['acceptance'] else 'NON REMPLI'} (tel qu'écrit, K = 15) ; "
          f"{'REMPLI' if b['acceptance_valid_nulls'] else 'NON REMPLI'} (lecture écart 4b, 13 nuls valides, décidée "
          "après les résultats « avant »)."]
    return "\n".join(L) + "\n"


def supplement(res: Path) -> str | None:
    """Deviation 4c (blind correlated nulls, both codes) and 4d (block-length sensitivity, v0.4.1)."""
    dirs = sorted(d for d in res.iterdir() if d.is_dir() and d.name.startswith("supp_") and (d / "manifest.json").exists())
    if not dirs:
        return None
    L = ["# Expériences complémentaires (écart 4 — non pré-enregistrées à l'origine)", "",
         f"Nuls aveugles : dépassement significatif si p < 0,05/{K_SUPP_BLIND} = {0.05 / K_SUPP_BLIND:.3f}. "
         "Sensibilité : descriptive, ne sert pas à choisir.", "",
         "| Partie | Code | Scénario | N | EDGE | Taux [IC 95 %] | p (H0 ≤ 5 %) | Jugement | Effet filtré [IC 95 %] | Erreurs |",
         "|---|---|---|---:|---:|---|---:|---|---|---:|"]
    out = {}
    for d in dirs:
        man = json.loads((d / "manifest.json").read_text())
        for f in sorted(d.glob("*.jsonl")):
            rows = _rows(f)
            valid = [r for r in rows if r.get("verdict") != "ERROR"]
            e = _rate(sum(r["verdict"] == "EDGE" for r in valid), len(valid),
                      level=0.05 / K_SUPP_BLIND if man["part"] == "blind" else 0.05)
            fe = _filtered_effect(valid)
            jug = e["judgement"] if man["part"] == "blind" else "(descriptif)"
            out[f"{d.name}/{f.stem}"] = {"edge": e, "filtered_effect": fe, "errors": len(rows) - len(valid)}
            eff = "—" if not fe else f"{fe['mean']:+.4f} [{fe['ci95'][0]:+.4f} ; {fe['ci95'][1]:+.4f}]"
            L.append(f"| {man['part']} | {man['tag']} | {f.stem} | {e['n']} | {e['k']} | {_pct(e['rate'])} "
                     f"[{_pct(e['ci95'][0])} ; {_pct(e['ci95'][1])}] | {e['p_vs_5pct']:.2g} | {jug} | {eff} | "
                     f"{len(rows) - len(valid)} |")
    (res / "summary_supplement.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    text = "\n".join(L) + "\n"
    (res / "REPORT_supplement.md").write_text(text)
    return text


def main() -> None:
    res = HERE / "results"
    phases = [p.name for p in sorted(res.iterdir()) if p.is_dir() and (p / "manifest.json").exists()
              and not p.name.startswith(("timing", "supp_", "INVALID"))]
    summaries = {}
    for ph in phases:
        s = summarise(ph)
        summaries[ph] = s
        (res / f"summary_{ph}.json").write_text(json.dumps(s, indent=1, ensure_ascii=False, default=str))
        (res / f"REPORT_{ph}.md").write_text(report(s))
        print(report(s))
    if "before" in summaries and "after" in summaries:
        c = comparison(summaries["before"], summaries["after"])
        (res / "COMPARISON.md").write_text(c)
        print(c)
    sup = supplement(res)
    if sup:
        print(sup)


if __name__ == "__main__":
    main()
