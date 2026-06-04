"""Self-calibration of the 8 macro parameters — no human tuning.

Budget-driven, per the spec:
  * Fixed random seed throughout.
  * Time ONE full run first; from that and a wall-clock budget (default 60 min) compute
    how many evaluations fit and set Nelder-Mead's maxfev.
  * Average 3 seeded runs per evaluation IF the budget allows >= ~50 evaluations; if
    3/eval leaves < ~30, drop to 1/eval; if still too few, fix the least-sensitive
    parameters at their midpoints to shrink the search until >= ~30 evaluations fit.
    (Our macro is deterministic, so seed-averaging is a no-op — recorded in the report.)
  * Nelder-Mead with the computed maxfev AND the wall-clock budget as a hard stop; on
    hitting either, write best-so-far params and STOP.
  * Objective: confidence-weighted error between simulated and central anchor Christian%
    per region per anchor year (Speculative low weight, High high). Speculative rows are
    scored against the low/central/high BAND (zero penalty if inside). A sum-to-GLOBAL
    penalty is applied only for years with broad regional coverage (>= 8/10 regions).
    Scored only where that region×year anchor row exists.

Writes reports/calibration_report.md and data/simulation_output.json.

Run: python -m sim.macro.calibrate [--budget SECONDS] [--smoke]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402
from scipy.optimize import minimize  # noqa: E402

from pipeline import schema as S  # noqa: E402
from sim import data as D  # noqa: E402
from sim.macro.model import MacroModel, MacroConfig, PARAM_SPEC, PARAM_NAMES, DEFAULT_PARAMS  # noqa: E402
from sim.macro.run import build_global_series, build_output  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS = [1729, 2718, 3141]  # used only if the model were stochastic

# Least-sensitive params fixed first if the search must shrink (per spec fallback).
LEAST_SENSITIVE_ORDER = ["fertility_adv", "martyrdom_amplification",
                         "nominal_to_practicing_ratio", "complex_contagion_threshold"]


class BudgetExceeded(Exception):
    pass


def _global_pct_at(years, gpct, year):
    return D._interp(list(zip(years, gpct)), year)


def evaluate(params: dict, base_config: MacroConfig):
    """Run the model once with `params`; return (model, years, global_pct)."""
    cfg = MacroConfig(
        regions=base_config.regions, start_year=base_config.start_year,
        end_year=base_config.end_year, step=base_config.step,
        params=params, seed=base_config.seed, data_dir=base_config.data_dir,
        max_strands=base_config.max_strands,
    )
    m = MacroModel(cfg)
    m.run()
    g = build_global_series(m)
    return m, m.years, g["christian_pct"]


def _anchor_band_pct(a: D.Anchor):
    """Return (low_pct, central_pct, high_pct) using counts/total_population."""
    pop = a.total_population
    c = a.christians_pct_central
    lo = (100.0 * a.christians_low / pop) if (a.christians_low is not None and pop) else None
    hi = (100.0 * a.christians_high / pop) if (a.christians_high is not None and pop) else None
    return lo, c, hi


def objective_from_run(model, years, gpct, anchors, broad_years) -> float:
    total = 0.0
    # Per-region per-anchor-year confidence-weighted error.
    for a in anchors:
        if a.christians_pct_central is None:
            continue
        if a.region == S.GLOBAL:
            sim = _global_pct_at(years, gpct, a.year)
        elif a.region in model.region_set:
            sim = model.simulated_pct_at(a.region, a.year)
        else:
            continue
        if sim is None:
            continue
        w = D.CONFIDENCE_WEIGHT.get(a.confidence, 0.5)
        lo, c, hi = _anchor_band_pct(a)
        if a.confidence == "Speculative" and lo is not None and hi is not None:
            # Band scoring: zero penalty if inside [low, high].
            if lo <= sim <= hi:
                dev = 0.0
            else:
                dev = min(abs(sim - lo), abs(sim - hi))
        else:
            dev = sim - c
        total += w * (dev / 100.0) ** 2

    # Sum-to-GLOBAL penalty, ONLY for broad-coverage years (>= 8/10 regions).
    aidx = D.anchor_index(anchors)
    for y in broad_years:
        present = [r for r in model.regions if (r, y) in aidx]
        if len(present) < 8:
            continue
        g_anchor = aidx.get((S.GLOBAL, y))
        if not g_anchor or g_anchor.christians_central is None:
            continue
        sim_sum = 0.0
        for r in present:
            sim_pct = model.simulated_pct_at(r, y)
            pop = D.region_population(r, y, anchors)
            if sim_pct is not None:
                sim_sum += sim_pct / 100.0 * pop
        rel = (sim_sum - g_anchor.christians_central) / g_anchor.christians_central
        total += 0.5 * rel ** 2
    return total


def calibrate(base_config: MacroConfig, budget_s: float = 3600.0, smoke: bool = False):
    anchors = D.load_anchors(base_config.data_dir)
    broad_years = S.years_with_broad_coverage(8)
    free_names = list(PARAM_NAMES)
    fixed = {}

    # 1) Time a single full run.
    t0 = time.time()
    m, years, gpct = evaluate(dict(DEFAULT_PARAMS), base_config)
    t_run = max(1e-3, time.time() - t0)
    base_obj = objective_from_run(m, years, gpct, anchors, broad_years)

    # 2) Budget-driven settings.
    if smoke:
        runs_per_eval = 1
        maxfev = len(free_names) + 2          # ONE iteration only
        note = "smoke: single-iteration calibration (plumbing only, NOT converged)"
    else:
        # The macro model is DETERMINISTic, so averaging seeded runs is a pure no-op;
        # per the spec's fallback we use 1 run/eval, which triples effective evaluations.
        runs_per_eval = 1
        evals = int(budget_s / (t_run * runs_per_eval))
        # If even 1/eval can't afford >= 30 evals, fix least-sensitive params at midpoints.
        while evals < 30 and len(free_names) > 3:
            drop = next((p for p in LEAST_SENSITIVE_ORDER if p in free_names), None)
            if drop is None:
                break
            free_names.remove(drop)
            fixed[drop] = DEFAULT_PARAMS[drop]
        maxfev = max(len(free_names) + 2, min(2000, evals))
        note = (f"runs/eval=1 (model deterministic -> seed-averaging is a no-op, so 1/eval "
                f"is used to maximize evaluations); fixed={list(fixed)}")

    bounds = [PARAM_SPEC[p] for p in free_names]

    # Optimize in normalized [0,1] space for Nelder-Mead conditioning.
    def denorm(xn):
        params = dict(DEFAULT_PARAMS)
        params.update(fixed)
        for name, v in zip(free_names, xn):
            lo, hi, _ = PARAM_SPEC[name]
            params[name] = lo + min(1.0, max(0.0, v)) * (hi - lo)
        return params

    state = {"best_obj": float("inf"), "best_params": dict(DEFAULT_PARAMS), "nfev": 0,
             "hit_time": False, "start": time.time()}

    def obj(xn):
        if time.time() - state["start"] > budget_s:
            state["hit_time"] = True
            raise BudgetExceeded()
        params = denorm(xn)
        vals = []
        for s in range(runs_per_eval):
            cfg = MacroConfig(regions=base_config.regions, start_year=base_config.start_year,
                              end_year=base_config.end_year, step=base_config.step,
                              params=params, seed=SEEDS[s % len(SEEDS)] if runs_per_eval > 1 else base_config.seed,
                              data_dir=base_config.data_dir, max_strands=base_config.max_strands)
            mm = MacroModel(cfg)
            mm.run()
            gg = build_global_series(mm)
            vals.append(objective_from_run(mm, mm.years, gg["christian_pct"], anchors, broad_years))
        val = float(np.mean(vals))
        state["nfev"] += 1
        if val < state["best_obj"]:
            state["best_obj"] = val
            state["best_params"] = params
        return val

    # Multi-restart Nelder-Mead: the objective landscape is multimodal (bistable
    # regions create local minima), so a single simplex is unreliable. We run several
    # restarts from spread starting points and keep the global best-ever evaluated point
    # (state tracks it across all restarts). The wall-clock budget is the hard stop.
    mid0 = np.array([(PARAM_SPEC[p][2] - PARAM_SPEC[p][0]) / (PARAM_SPEC[p][1] - PARAM_SPEC[p][0])
                     for p in free_names])
    rng = np.random.default_rng(base_config.seed)
    # Fewer, DEEPER restarts: each needs enough evals to actually descend in 8-D.
    n_restarts = 1 if smoke else max(1, min(6, maxfev // 250))
    starts = [mid0] + [rng.random(len(free_names)) for _ in range(max(0, n_restarts - 1))]
    per_restart = max(120, maxfev // max(1, len(starts)))

    cap_hit = "maxfev/convergence"
    for x0 in starts:
        options = {"maxfev": per_restart, "xatol": 1e-3, "fatol": 1e-6, "disp": False}
        if smoke:
            options["maxiter"] = 1
        try:
            res = minimize(obj, np.asarray(x0, dtype=float), method="Nelder-Mead", options=options)
            if res.fun < state["best_obj"]:
                state["best_obj"] = res.fun
                state["best_params"] = denorm(res.x)
        except BudgetExceeded:
            cap_hit = "wall-clock budget"
            break
    info_restarts = len(starts)
    best_params = state["best_params"]

    info = {
        "t_run": t_run, "runs_per_eval": runs_per_eval, "maxfev": maxfev,
        "nfev": state["nfev"], "budget_s": budget_s, "cap_hit": cap_hit,
        "free_names": free_names, "fixed": fixed, "note": note,
        "base_obj": base_obj, "best_obj": state["best_obj"],
        "smoke": smoke, "broad_years": broad_years, "n_restarts": info_restarts,
    }
    return best_params, info


def write_report(best_params, info, base_config, out_path: str | None = None) -> str:
    anchors = D.load_anchors(base_config.data_dir)
    m, years, gpct = evaluate(best_params, base_config)
    lines = ["# Macro calibration report", ""]
    lines.append(f"- Mode: {'SMOKE (single iteration, NOT converged)' if info['smoke'] else 'full'}")
    lines.append(f"- Measured per-run wall time: **{info['t_run']*1000:.0f} ms**")
    lines.append(f"- Wall-clock budget: {info['budget_s']:.0f} s")
    lines.append(f"- runs/eval: {info['runs_per_eval']}  |  maxfev: {info['maxfev']}  |  "
                 f"evaluations actually run: {info['nfev']}")
    lines.append(f"- Stop reason (cap hit): **{info['cap_hit']}**")
    lines.append(f"- Free params: {', '.join(info['free_names'])}")
    if info["fixed"]:
        lines.append(f"- Fixed-at-midpoint params (least sensitive): {info['fixed']}")
    lines.append(f"- Notes: {info['note']}")
    lines.append(f"- Objective: start (midpoint) = {info['base_obj']:.5f} -> best = {info['best_obj']:.5f}")
    lines.append("")
    lines.append("## Calibrated parameters")
    lines.append("")
    lines.append("| parameter | value | bounds |")
    lines.append("|---|---:|---|")
    for p in PARAM_NAMES:
        lo, hi, _ = PARAM_SPEC[p]
        lines.append(f"| {p} | {best_params[p]:.4f} | [{lo}, {hi}] |")
    lines.append("")

    # Simulated vs anchor curve per region, with residuals.
    lines.append("## Simulated vs anchor Christian% (residuals)")
    lines.append("")
    g = build_global_series(m)
    aidx = D.anchor_index(anchors)
    abs_devs = []
    for region in [S.GLOBAL] + list(base_config.regions):
        rows = [a for a in anchors if a.region == region and a.christians_pct_central is not None]
        if not rows:
            continue
        lines.append(f"### {region}")
        lines.append("")
        lines.append("| year | sim % | anchor % | residual | confidence |")
        lines.append("|---:|---:|---:|---:|---|")
        for a in sorted(rows, key=lambda r: r.year):
            if region == S.GLOBAL:
                sim = _global_pct_at(years, g["christian_pct"], a.year)
            else:
                sim = m.simulated_pct_at(region, a.year)
            resid = (sim - a.christians_pct_central) if sim is not None else None
            if resid is not None:
                abs_devs.append(abs(resid))
            sim_s = f"{sim:.2f}" if sim is not None else "—"
            res_s = f"{resid:+.2f}" if resid is not None else "—"
            lines.append(f"| {a.year} | {sim_s} | {a.christians_pct_central:.2f} | {res_s} | {a.confidence} |")
        lines.append("")
    if abs_devs:
        lines.append(f"**Mean absolute residual across scored anchors: {np.mean(abs_devs):.2f} "
                     f"percentage points** ({len(abs_devs)} anchors).")
        lines.append("")
    lines.append("_A symmetric 8-global-parameter model cannot perfectly separate every "
                 "region (e.g. settler-colonial vs mission-field Christianization, or "
                 "indigenous house-church growth). Residuals above are reported honestly; "
                 "Phase 2 adds finer structure and ABC-SMC calibration._")
    report = "\n".join(lines)
    out_path = out_path or os.path.join(REPO_ROOT, "reports", "calibration_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=float(os.environ.get("TAPESTRY_CALIB_BUDGET", 3600)))
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--data-dir", default=D.DEFAULT_DATA_DIR)
    ap.add_argument("--source", default="fixtures")
    args = ap.parse_args()

    base_config = MacroConfig(data_dir=args.data_dir)
    best_params, info = calibrate(base_config, budget_s=args.budget, smoke=args.smoke)
    report = write_report(best_params, info, base_config)

    # Write the calibrated simulation_output.json.
    final_cfg = MacroConfig(data_dir=args.data_dir, params=best_params)
    m = MacroModel(final_cfg)
    m.run()
    import json
    out = build_output(m, source=args.source)
    out["meta"]["calibrated"] = True
    out["meta"]["calibration"] = {k: info[k] for k in ("t_run", "runs_per_eval", "maxfev",
                                                        "nfev", "cap_hit", "best_obj")}
    with open(os.path.join(D.DEFAULT_DATA_DIR, "simulation_output.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(report[:1500])
    print("\n[calibrate] wrote reports/calibration_report.md and data/simulation_output.json")
    print(f"[calibrate] best objective {info['best_obj']:.5f} after {info['nfev']} evals "
          f"({info['cap_hit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
