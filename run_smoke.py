"""SMOKE TEST GATE — minimal end-to-end path on tiny synthetic data.

Confirms PLUMBING, not quality: 1 region, 3 timesteps, ~10 strands, 5 micro agents, and
a SINGLE-ITERATION (not converged) calibration. Each stage must run and emit its file:
  - data/smoke/simulation_output.json   (macro)
  - reports/smoke/calibration_report.md (single-iteration calibration)
  - data/smoke/example_lives.json       (micro, a real dump)
Outputs go under data/smoke/ and reports/smoke/ so the full-run artifacts are untouched.

Run: python run_smoke.py   (exit 0 only if all three files emit)
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import make_fixtures  # noqa: E402
from sim import data as D  # noqa: E402
from sim.macro.model import MacroConfig, MacroModel  # noqa: E402
from sim.macro.run import build_output  # noqa: E402
from sim.macro.calibrate import calibrate, write_report  # noqa: E402
from sim.micro.run import run_and_export  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_SMOKE = os.path.join(ROOT, "data", "smoke")
REPORTS_SMOKE = os.path.join(ROOT, "reports", "smoke")


def main() -> int:
    os.makedirs(DATA_SMOKE, exist_ok=True)
    os.makedirs(REPORTS_SMOKE, exist_ok=True)
    print("=== SMOKE TEST GATE (tiny end-to-end; plumbing only) ===")

    # Ensure fixtures exist.
    if not os.path.exists(os.path.join(D.DEFAULT_DATA_DIR, "anchors.csv")):
        make_fixtures.main()

    ok = True

    # --- Stage 1: macro on a tiny slice (1 region, 3 timesteps, <=10 strands) ---
    cfg = MacroConfig(regions=["Roman/Mediterranean"], start_year=30, end_year=50,
                      step=10, max_strands=10)
    model = MacroModel(cfg)
    model.run()
    macro_out = build_output(model, source="smoke-fixtures")
    macro_path = os.path.join(DATA_SMOKE, "simulation_output.json")
    with open(macro_path, "w", encoding="utf-8") as f:
        json.dump(macro_out, f, indent=1)
    n_steps = len(macro_out["years"])
    print(f"[1/3] macro: {len(macro_out['regions'])} region, {n_steps} timesteps, "
          f"{macro_out['meta']['n_strands']} strands -> {os.path.relpath(macro_path, ROOT)}")
    assert n_steps == 3, f"expected 3 timesteps, got {n_steps}"
    assert macro_out["meta"]["n_strands"] <= 10

    # --- Stage 2: SINGLE-ITERATION calibration on the tiny slice ---
    best_params, info = calibrate(cfg, budget_s=30, smoke=True)
    report_path = os.path.join(REPORTS_SMOKE, "calibration_report.md")
    write_report(best_params, info, cfg, out_path=report_path)
    print(f"[2/3] calibration: single-iteration, {info['nfev']} evals, "
          f"cap={info['cap_hit']} -> {os.path.relpath(report_path, ROOT)}")
    assert info["smoke"] is True

    # --- Stage 3: micro with 5 agents, no extra seeds (plumbing only) ---
    micro_path = os.path.join(DATA_SMOKE, "example_lives.json")
    micro_out = run_and_export(n_agents=5, out_path=micro_path, max_extra_seeds=0,
                               region="Roman/Mediterranean")
    print(f"[3/3] micro: {micro_out['meta']['n_agents']} agents, "
          f"{len(micro_out['lives'])} lives (real dump) -> {os.path.relpath(micro_path, ROOT)}")
    assert micro_out["meta"]["provenance"].startswith("REAL")

    # --- Gate: all three files must exist and be non-empty ---
    for path in (macro_path, report_path, micro_path):
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            print(f"  [FAIL] missing/empty: {path}")
            ok = False

    print("=== SMOKE", "PASSED — plumbing confirmed; safe to scale up ===" if ok else "FAILED ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
