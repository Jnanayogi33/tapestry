"""Calibrate the agent contagion's 8 global rates to the sourced anchors.

The network and lives are built ONCE; only the global rates vary, and each evaluation
re-runs the (fast, vectorised) contagion. Objective: confidence-weighted squared error
between the emergent Christian fraction and the anchor christians_pct_central, per
region per anchor year (where a row exists) plus the 14 GLOBAL rows. Nelder-Mead with a
wall-clock budget and a computed maxfev; fixed seed throughout. Best params -> JSON.

Run: python -m sim.threads.calibrate [--budget-min 8] [--n 70000]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pipeline import schema as S  # noqa: E402
from sim import data as D  # noqa: E402
from sim.threads.agents import AgentField, AgentConfig, PARAM_SPEC, PARAM_NAMES, DEFAULT_PARAMS  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONF_W = {"High": 1.0, "Medium": 0.6, "Low": 0.3, "Speculative": 0.12}


def _interp(xs, ys, x):
    return float(np.interp(x, xs, ys))


class Objective:
    def __init__(self, field: AgentField):
        self.af = field
        self.years = field.years
        # anchor targets: (region, year, pct, weight)
        self.targets = []
        for a in D.load_anchors(field.cfg.data_dir):
            if a.christians_pct_central is None:
                continue
            if a.region in S.REGIONS or a.region == S.GLOBAL:
                self.targets.append((a.region, a.year, a.christians_pct_central,
                                     CONF_W.get(a.confidence, 0.5)))
        self.lo = np.array([PARAM_SPEC[k][0] for k in PARAM_NAMES])
        self.hi = np.array([PARAM_SPEC[k][1] for k in PARAM_NAMES])
        self.n_eval = 0

    def params_from_unit(self, u):
        u = np.clip(u, 0, 1)
        return {k: self.lo[i] + u[i] * (self.hi[i] - self.lo[i]) for i, k in enumerate(PARAM_NAMES)}

    def emergent(self, params):
        res = self.af.run_contagion(params)
        lf = self.af.lit_fraction(res)
        glob_lit = res["agg_lit"].sum(axis=0)
        glob_alive = np.maximum(res["agg_alive"].sum(axis=0), 1.0)
        glob = glob_lit / glob_alive
        return lf, glob

    def score(self, u):
        self.n_eval += 1
        params = self.params_from_unit(u)
        lf, glob = self.emergent(params)
        err = 0.0
        wsum = 0.0
        for region, year, pct, w in self.targets:
            if region == S.GLOBAL:
                sim = _interp(self.years, glob, year) * 100.0
            else:
                sim = _interp(self.years, lf[region], year) * 100.0
            err += w * (sim - pct) ** 2
            wsum += w
        return err / max(wsum, 1e-9)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-min", type=float, default=8.0)
    ap.add_argument("--n", type=int, default=70000)
    ap.add_argument("--seed", type=int, default=1729)
    args = ap.parse_args()

    print(f"[calib] building field (n={args.n}) ...")
    t0 = time.time()
    af = AgentField(AgentConfig(n_lives=args.n, seed=args.seed, quiet=False))
    obj = Objective(af)
    build_s = time.time() - t0

    # time one evaluation, compute maxfev from the wall-clock budget
    t1 = time.time()
    base_u = np.array([(DEFAULT_PARAMS[k] - obj.lo[i]) / (obj.hi[i] - obj.lo[i])
                       for i, k in enumerate(PARAM_NAMES)])
    base_score = obj.score(base_u)
    per_eval = time.time() - t1
    budget_s = args.budget_min * 60.0
    maxfev = int(max(40, min(600, (budget_s - build_s) / max(per_eval, 1e-3))))
    print(f"[calib] per-eval {per_eval:.2f}s, base score {base_score:.1f}, maxfev {maxfev}")

    deadline = time.time() + budget_s
    best = {"u": base_u, "score": base_score}

    def wrapped(u):
        if time.time() > deadline:
            return best["score"] + 1e6   # force NM to wind down past the deadline
        s = obj.score(u)
        if s < best["score"]:
            best["score"] = s; best["u"] = np.array(u)
        return s

    # multi-start Nelder-Mead from the midpoint + a few perturbations
    starts = [base_u]
    rng = np.random.default_rng(args.seed)
    for _ in range(2):
        starts.append(np.clip(base_u + rng.normal(0, 0.2, len(base_u)), 0, 1))
    fev_each = max(20, maxfev // len(starts))
    for s0 in starts:
        if time.time() > deadline:
            break
        minimize(wrapped, s0, method="Nelder-Mead",
                 options={"maxfev": fev_each, "xatol": 1e-3, "fatol": 1e-2})

    best_params = obj.params_from_unit(best["u"])
    lf, glob = obj.emergent(best_params)

    # write params + report
    out = {"params": best_params, "score": best["score"], "n_lives": args.n,
           "seed": args.seed, "evals": obj.n_eval, "maxfev": maxfev,
           "per_eval_s": per_eval}
    json.dump(out, open(os.path.join(D.DEFAULT_DATA_DIR, "thread_params.json"), "w"), indent=1)

    lines = ["# Thread-contagion calibration report", "",
             f"- lives: {args.n} | seed: {args.seed} | evals: {obj.n_eval} | maxfev: {maxfev}",
             f"- per-eval: {per_eval:.2f}s | budget: {args.budget_min} min",
             f"- base score: {base_score:.1f} -> best score: {best['score']:.1f}",
             f"- params: `{json.dumps(best_params)}`", "",
             "## Emergent vs anchor Christian % (per region per anchor year)", ""]
    mae = [];
    for region, year, pct, w in obj.targets:
        sim = (_interp(af.years, glob, year) if region == S.GLOBAL
               else _interp(af.years, lf[region], year)) * 100.0
        mae.append(abs(sim - pct))
        lines.append(f"- {region} {year}: sim {sim:5.1f}% vs anchor {pct:5.1f}% (w={w})")
    lines.insert(6, f"- mean |residual|: {np.mean(mae):.1f} percentage points")
    os.makedirs(os.path.join(REPO_ROOT, "reports"), exist_ok=True)
    open(os.path.join(REPO_ROOT, "reports", "calibration_report_threads.md"), "w").write("\n".join(lines))

    print(f"[calib] done: score {base_score:.1f} -> {best['score']:.1f}, "
          f"MAE {np.mean(mae):.1f}pp, {obj.n_eval} evals in {time.time()-t0:.0f}s")
    print(f"[calib] params -> data/thread_params.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
