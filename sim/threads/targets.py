"""Per-region, per-decade lit-fraction TARGETS for the life-thread sim.

The aggregate truth is the v1-calibrated macro run (data/simulation_output.json): for
each region and decade it gives the Christian fraction (lit share), the practicing
fraction (gold share), the absolute Christian count (drives thread COUNT and the blaze),
and the population. The thread sim distributes individual life-threads to MATCH these —
so the lit-fraction stays reconciled to the sourced anchors while the spread emerges.

If simulation_output.json is absent, we fall back to interpolating anchors directly
(christians_pct_central -> lit; schema.derive_composition -> gold share).
"""
from __future__ import annotations

import json
import os

from pipeline import schema as S
from sim import data as D

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _interp(xs, ys, x):
    if not xs:
        return 0.0
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] != xs[i] else 0.0
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


class Targets:
    def __init__(self, data_dir: str = D.DEFAULT_DATA_DIR, decade_step: int = 10):
        self.data_dir = data_dir
        self.regions = list(S.REGIONS)
        self.years = list(range(S.TIMELINE_START, S.TIMELINE_END + 1, decade_step))
        if self.years[-1] != S.TIMELINE_END:
            self.years.append(S.TIMELINE_END)
        self._christian_frac: dict[str, list[float]] = {}
        self._gold_frac: dict[str, list[float]] = {}
        self._christians: dict[str, list[float]] = {}
        self._population: dict[str, list[float]] = {}
        self._load()

    def _load(self) -> None:
        sim_path = os.path.join(self.data_dir, "simulation_output.json")
        if os.path.exists(sim_path):
            self._load_from_macro(sim_path)
        else:
            self._load_from_anchors()

    def _load_from_macro(self, path: str) -> None:
        sim = json.load(open(path, encoding="utf-8"))
        syears = sim["years"]
        for r in self.regions:
            reg = sim["regions"].get(r)
            if not reg:
                self._zero(r)
                continue
            cp = reg["christian_pct"]
            pp = reg["practicing_pct"]
            chr_ = reg.get("christians", [0] * len(syears))
            pop = reg.get("population", [1] * len(syears))
            self._christian_frac[r] = [max(0.0, _interp(syears, cp, y) / 100.0) for y in self.years]
            self._christians[r] = [max(0.0, _interp(syears, chr_, y)) for y in self.years]
            self._population[r] = [max(1.0, _interp(syears, pop, y)) for y in self.years]
            gold = []
            for i, y in enumerate(self.years):
                c = self._christian_frac[r][i]
                pr = max(0.0, _interp(syears, pp, y) / 100.0)
                gold.append(min(1.0, pr / c) if c > 1e-9 else 0.0)
            self._gold_frac[r] = gold

    def _load_from_anchors(self) -> None:
        anchors = D.load_anchors(self.data_dir)
        idx = {}
        for a in anchors:
            if a.region in self.regions and a.christians_pct_central is not None:
                idx.setdefault(a.region, []).append((a.year, a))
        for r in self.regions:
            pts = sorted(idx.get(r, []))
            if not pts:
                self._zero(r)
                continue
            xs = [p[0] for p in pts]
            cf = [p[1].christians_pct_central / 100.0 for p in pts]
            self._christian_frac[r] = [max(0.0, _interp(xs, cf, y)) for y in self.years]
            self._population[r] = [D.region_population(r, y, anchors) for y in self.years]
            self._christians[r] = [self._christian_frac[r][i] * self._population[r][i]
                                   for i in range(len(self.years))]
            gold = []
            for i, y in enumerate(self.years):
                comp = S.derive_composition(r, int(y), self._christian_frac[r][i] * 100.0, None)
                c = self._christian_frac[r][i]
                gp = (comp["practicing"] or 0.0) / 100.0
                gold.append(min(1.0, gp / c) if c > 1e-9 else 0.0)
            self._gold_frac[r] = gold

    def _zero(self, r: str) -> None:
        n = len(self.years)
        self._christian_frac[r] = [0.0] * n
        self._gold_frac[r] = [0.0] * n
        self._christians[r] = [0.0] * n
        self._population[r] = [1.0] * n

    # -- accessors ------------------------------------------------------------------
    def christian_frac(self, r: str, i: int) -> float:
        return self._christian_frac[r][i]

    def gold_frac(self, r: str, i: int) -> float:
        return self._gold_frac[r][i]

    def christians(self, r: str, i: int) -> float:
        return self._christians[r][i]

    def population(self, r: str, i: int) -> float:
        return self._population[r][i]

    def non_christian(self, r: str, i: int) -> float:
        return max(0.0, self._population[r][i] - self._christians[r][i])
