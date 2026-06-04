"""Run the macro simulation and write data/simulation_output.json.

The output is everything the visualization needs for the macro layer: per-region
belief-state fractions and Christian% over time, the population-weighted GLOBAL
aggregate, and the anchor points for overlay. Nothing is hardcoded downstream — the
viz reads this file plus strands.csv/events.csv/example_lives.json.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pipeline import schema as S  # noqa: E402
from sim import data as D  # noqa: E402
from sim.macro.model import MacroModel, MacroConfig, PARAM_NAMES  # noqa: E402
from sim.mesa_compat import MESA_MAJOR  # noqa: E402

ORIGIN_REGION = "Roman/Mediterranean"


def effective_region_pop(region: str, year: float, anchors) -> float:
    """Region population for GLOBAL aggregation, with the Roman/Mediterranean
    antiquity-only category faded out across 500->900 as its territory passes to
    Western/Eastern Europe & MENA (honoring the double-count rule)."""
    pop = D.region_population(region, year, anchors)
    if region == ORIGIN_REGION:
        if year <= 500:
            factor = 1.0
        elif year >= 900:
            factor = 0.0
        else:
            factor = 1.0 - (year - 500) / 400.0
        pop *= factor
    return pop


def build_global_series(model: MacroModel) -> dict:
    anchors = model.anchors
    years = model.years
    gpop_curve = D.global_population_curve(anchors)
    christians, pop_total, pct, practicing = [], [], [], []
    for i, y in enumerate(years):
        wsum = 0.0
        chr_w = 0.0
        prac_w = 0.0
        for r in model.regions:
            frac = model.history[r]["A"][i] + model.history[r]["P"][i]
            pfrac = model.history[r]["P"][i]
            ep = effective_region_pop(r, y, anchors)
            wsum += ep
            chr_w += frac * ep
            prac_w += pfrac * ep
        # GLOBAL Christian% is the population-weighted average of regional fractions
        # (always in [0,100]); absolute counts use the authoritative GLOBAL population.
        gfrac = (chr_w / wsum) if wsum else 0.0
        pfrac_g = (prac_w / wsum) if wsum else 0.0
        gpop = D._interp(list(gpop_curve.items()), y) if gpop_curve else None
        if not gpop:
            gpop = wsum
        christians.append(gfrac * gpop)
        pop_total.append(gpop)
        pct.append(100.0 * gfrac)
        practicing.append(100.0 * pfrac_g)
    return {
        "christian_pct": pct,
        "practicing_pct": practicing,
        "christians": christians,
        "population": pop_total,
    }


def anchors_for_output(anchors, regions: list[str]) -> list[dict]:
    keep = set(regions) | {S.GLOBAL}
    out = []
    for a in anchors:
        if a.region not in keep:
            continue
        out.append({
            "region": a.region,
            "year": a.year,
            "christians_pct_central": a.christians_pct_central,
            "christians_low": a.christians_low,
            "christians_central": a.christians_central,
            "christians_high": a.christians_high,
            "practicing_pct": a.practicing_pct,
            "confidence": a.confidence,
        })
    return out


def build_output(model: MacroModel, source: str = "fixtures") -> dict:
    years = model.years
    regions_out = {}
    for r in model.regions:
        h = model.history[r]
        cp = model.christian_pct_series(r)
        pp = model.practicing_pct_series(r)
        pops = [D.region_population(r, y, model.anchors) for y in years]
        christians = [cp[i] / 100.0 * pops[i] for i in range(len(years))]
        regions_out[r] = {
            "states": {k: [round(v, 6) for v in h[k]] for k in h},
            "christian_pct": [round(v, 4) for v in cp],
            "practicing_pct": [round(v, 4) for v in pp],
            "population": [round(v, 1) for v in pops],
            "christians": [round(v, 1) for v in christians],
        }
    glob = build_global_series(model)
    return {
        "meta": {
            "regions": model.regions,
            "start_year": model.config.start_year,
            "end_year": model.config.end_year,
            "step": model.config.step,
            "params": {k: model.params[k] for k in PARAM_NAMES},
            "seed": model.config.seed,
            "mesa_major": MESA_MAJOR,
            "source": source,
            "n_strands": len(model.strands),
            "n_events": len(model.events),
            "origin_region": ORIGIN_REGION,
        },
        "years": years,
        "regions": regions_out,
        "global": {
            "christian_pct": [round(v, 4) for v in glob["christian_pct"]],
            "practicing_pct": [round(v, 4) for v in glob["practicing_pct"]],
            "christians": [round(v, 1) for v in glob["christians"]],
            "population": [round(v, 1) for v in glob["population"]],
        },
        "anchors": anchors_for_output(model.anchors, model.regions),
    }


def run_and_write(config: MacroConfig | None = None, source: str = "fixtures",
                  out_path: str | None = None) -> dict:
    model = MacroModel(config)
    model.run()
    output = build_output(model, source=source)
    out_path = out_path or os.path.join(D.DEFAULT_DATA_DIR, "simulation_output.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=1)
    return output


def main() -> int:
    out = run_and_write()
    g = out["global"]
    print(f"Macro run complete: {len(out['regions'])} regions, "
          f"{len(out['years'])} timesteps ({out['years'][0]}..{out['years'][-1]}).")
    print("GLOBAL Christian% at anchor-ish years:")
    years = out["years"]
    for ay in S.ANCHOR_YEARS:
        # nearest timestep
        i = min(range(len(years)), key=lambda k: abs(years[k] - ay))
        print(f"  {ay:>5} -> {g['christian_pct'][i]:6.2f}%")
    print(f"Wrote {os.path.join(D.DEFAULT_DATA_DIR, 'simulation_output.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
