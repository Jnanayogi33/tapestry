"""Emergent life-thread simulation — the SOURCE of the v2 picture.

The picture is built from a forest of GOLD belief-transmission LINEAGES rooted at the
single seed (Christ, AD 30, at x=0, y=0.5) and at the named strands (apostles/
missionaries = unusually bright, far-reaching igniters). Belief is not drawn as
region-to-region arcs; it SPREADS by local ignition: when a region needs more lit
lives (its calibrated Christian fraction rises), new lineages are ignited from a
nearby active lineage or an active strand — and we record the transmission link
(who lit whom). The chains flow rightward in time and fan outward in Y by distance
from Judaea, blazing where many converge (the modern Global South).

Beneath the gold lies the DARK WARP: a dense sample of unlit lives that fills the
field top-to-bottom (every human life), most of them dark.

Aggregate lit-fraction per region×decade is taken from the v1-calibrated macro run
(sim/threads/targets.Targets), so the blaze stays reconciled to the sourced anchors.
The random seed is fixed; the whole sim is reproducible.
"""
from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field

from pipeline import schema as S
from sim import data as D
from sim.embedding import Embedding
from sim.threads.targets import Targets

# Inter-region adjacency for cross-region ignition (mirrors the macro contact graph).
ADJACENCY = {
    "Roman/Mediterranean": ["Western Europe", "Eastern Europe & Russia", "Middle East & North Africa"],
    "Western Europe": ["Roman/Mediterranean", "Eastern Europe & Russia", "North America", "Latin America", "Sub-Saharan Africa"],
    "Eastern Europe & Russia": ["Roman/Mediterranean", "Western Europe", "Middle East & North Africa", "East Asia"],
    "Middle East & North Africa": ["Roman/Mediterranean", "Eastern Europe & Russia", "Sub-Saharan Africa", "South Asia"],
    "Sub-Saharan Africa": ["Middle East & North Africa", "Western Europe"],
    "South Asia": ["Middle East & North Africa", "Southeast Asia", "East Asia"],
    "East Asia": ["Eastern Europe & Russia", "South Asia", "Southeast Asia"],
    "Southeast Asia": ["South Asia", "East Asia"],
    "Latin America": ["Western Europe", "North America"],
    "North America": ["Western Europe", "Latin America"],
}
TIER_W = {"Tier 1": 1.0, "Tier 2": 0.6, "Tier 3": 0.35}


@dataclass
class Lineage:
    id: int
    region: str
    place: str
    base_y: float
    birth_i: int
    parent_id: int | None
    root_strand: str | None
    drift: float
    phase1: float
    phase2: float
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)
    shades: list = field(default_factory=list)
    alive: bool = True
    end_i: int | None = None

    def y_at(self, i: int) -> float:
        k = i - self.birth_i
        m = (0.013 * math.sin(0.55 * i + self.phase1)
             + 0.008 * math.sin(0.23 * i + self.phase2)
             + self.drift * k)
        return min(0.997, max(0.003, self.base_y + m))


@dataclass
class Link:
    px: float
    py: float
    cx: float
    cy: float
    kind: str          # "apostolic" (from a strand) or "contagion"
    strength: float


class ThreadSim:
    def __init__(self, data_dir: str = D.DEFAULT_DATA_DIR, seed: int = 1729,
                 budget_lit: int = 240_000, budget_dark: int = 60_000,
                 max_active_per_region: int = 1400, quiet: bool = True):
        self.data_dir = data_dir
        self.rng = random.Random(seed)
        self.budget_lit = budget_lit
        self.budget_dark = budget_dark
        self.max_active = max_active_per_region
        self.quiet = quiet

        self.emb = Embedding(data_dir)
        self.tg = Targets(data_dir)
        self.years = self.tg.years
        self.n = len(self.years)
        self.strands = D.load_strands(data_dir)

        self.lineages: list[Lineage] = []
        self.links: list[Link] = []
        self.dark: list[dict] = []
        self._next_id = 0
        self._active: dict[str, list[Lineage]] = {r: [] for r in S.REGIONS}
        self._build_strand_schedule()
        self._build_thread_counts()

    # -- precompute ----------------------------------------------------------------
    def _build_strand_schedule(self) -> None:
        """Per decade index -> list of (strand, x, y, strength) active and their regions."""
        self.strand_at: list[list[dict]] = [[] for _ in range(self.n)]
        for st in self.strands:
            ws = st.effect_window_start if st.effect_window_start is not None else st.birth_year
            we = st.effect_window_end if st.effect_window_end is not None else (st.death_year or ws)
            if ws is None:
                continue
            place = st.place if (st.place and st.place in self.emb.places) else None
            region0 = (st.primary_region or st.regions_affected or ["Roman/Mediterranean"])[0]
            p = self.emb.resolve_place(place, region0)
            sx = S.x_of_year(ws)
            sy = p.base_y if p else 0.5
            regions = [r for r in st.expanded_regions()] or ([region0] if region0 in S.REGIONS else [])
            strength = TIER_W.get(st.depth_tier, 0.3) * (st.strength / 5.0)
            for i, y in enumerate(self.years):
                if ws <= y <= we or (ws <= y + 9 and we >= y):  # overlaps the decade
                    self.strand_at[i].append({
                        "strand": st, "x": sx, "y": sy, "regions": regions,
                        "strength": strength, "name": st.name,
                    })

    def _build_thread_counts(self) -> None:
        """A(region, decade) = active lit lineage target, ∝ log(1+christians), summed
        to the budget; floored so early Christian regions still show a few threads."""
        raw = {}
        total = 0.0
        for r in S.REGIONS:
            for i in range(self.n):
                v = math.log10(1.0 + self.tg.christians(r, i)) if self.tg.christian_frac(r, i) > 0.004 else 0.0
                raw[(r, i)] = v
                total += v
        self.A: dict[tuple, int] = {}
        scale = (self.budget_lit / total) if total > 0 else 0.0
        for (r, i), v in raw.items():
            a = int(round(scale * v))
            if v > 0:
                a = max(a, 1)
            self.A[(r, i)] = min(a, self.max_active)

    # -- ignition ------------------------------------------------------------------
    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id - 1

    def _pick_place(self, region: str, near_y: float | None = None) -> str:
        places = self.emb.by_region.get(region) or []
        if not places:
            pl = self.emb.resolve_place(region=region)
            return pl.name if pl else "Rome"
        if near_y is not None and self.rng.random() < 0.6:
            places = sorted(places, key=lambda p: abs(p.base_y - near_y))[:max(2, len(places) // 2)]
        return self.rng.choice(places).name

    def _ignite(self, region: str, i: int, count: int) -> None:
        active_strands = [s for s in self.strand_at[i] if region in s["regions"]]
        for _ in range(count):
            parent_id = None
            root_strand = None
            px = py = None
            kind = "contagion"
            # Prefer a named strand igniter (the bright, far-reaching root).
            if active_strands and self.rng.random() < 0.7:
                s = max(active_strands, key=lambda z: z["strength"] * self.rng.random())
                px, py, root_strand, kind = s["x"], s["y"], s["name"], "apostolic"
            else:
                # contagion from a nearby active lineage (same region, else adjacent).
                pool = list(self._active[region])
                if not pool:
                    for adj in ADJACENCY.get(region, []):
                        pool.extend(self._active.get(adj, []))
                if pool:
                    par = self.rng.choice(pool if len(pool) < 40 else self.rng.sample(pool, 40))
                    parent_id = par.id
                    px, py = par.xs[-1], par.ys[-1]
                elif active_strands:
                    s = active_strands[0]
                    px, py, root_strand, kind = s["x"], s["y"], s["name"], "apostolic"
                else:
                    # No source yet — region not reachable; skip (emergence from seed).
                    continue
            place = self._pick_place(region, near_y=py)
            lid = self._new_id()
            base_y = self.emb.y(place=place, jitter_key=f"L{lid}")
            lin = Lineage(
                id=lid, region=region, place=place, base_y=base_y, birth_i=i,
                parent_id=parent_id, root_strand=root_strand,
                drift=(self.rng.random() - 0.5) * 0.004,
                phase1=self.rng.random() * 6.283, phase2=self.rng.random() * 6.283,
            )
            cx = S.x_of_year(self.years[i])
            cy = lin.y_at(i)
            lin.xs.append(cx); lin.ys.append(cy); lin.shades.append("gold")
            self.lineages.append(lin)
            self._active[region].append(lin)
            if px is not None and (abs(px - cx) > 1e-4 or abs(py - cy) > 1e-4):
                self.links.append(Link(px, py, cx, cy, kind,
                                       1.0 if kind == "apostolic" else 0.4))

    def _seed(self) -> None:
        lid = self._new_id()
        sx, sy = self.emb.seed_xy()
        lin = Lineage(id=lid, region="Roman/Mediterranean", place="Judaea", base_y=sy,
                      birth_i=0, parent_id=None, root_strand="Jesus of Nazareth",
                      drift=0.0, phase1=0.0, phase2=0.0)
        lin.xs.append(sx); lin.ys.append(sy); lin.shades.append("gold")
        self.lineages.append(lin)
        self._active["Roman/Mediterranean"].append(lin)

    # -- run -----------------------------------------------------------------------
    def run(self) -> dict:
        self._seed()
        for i in range(self.n):
            year = self.years[i]
            for r in S.REGIONS:
                gold = self.tg.gold_frac(r, i)
                # 1) extend existing actives.
                for lin in self._active[r]:
                    if lin.birth_i == i and lin.xs:
                        # just ignited this step; set shade by gold target
                        lin.shades[-1] = "gold" if self.rng.random() < gold else "gray-gold"
                        continue
                    x = S.x_of_year(year)
                    y = lin.y_at(i)
                    lin.xs.append(x); lin.ys.append(y)
                    lin.shades.append("gold" if self.rng.random() < gold else "gray-gold")
                # 2) adjust count to target.
                target = self.A.get((r, i), 0)
                cur = len(self._active[r])
                if cur < target:
                    self._ignite(r, i, target - cur)
                elif cur > target:
                    self._fray(r, cur - target, i)
        # finalize end_i
        for lin in self.lineages:
            if lin.end_i is None:
                lin.end_i = self.n - 1
        self._build_dark_warp()
        if not self.quiet:
            print(f"[threads] {len(self.lineages)} lineages, {len(self.links)} links, "
                  f"{len(self.dark)} dark, {sum(len(l.xs) for l in self.lineages)} lit points")
        return self.forest()

    def _fray(self, region: str, count: int, i: int) -> None:
        """Retire the `count` lineages most under decline (older/under suppression)."""
        actives = self._active[region]
        if not actives:
            return
        # fray the oldest first (they have run their course); their thread ends here.
        actives.sort(key=lambda l: l.birth_i)
        for lin in actives[:count]:
            if lin.shades:
                lin.shades[-1] = "gray-gold"  # dim before going dark
            lin.alive = False
            lin.end_i = i
        self._active[region] = actives[count:]

    # -- dark warp -----------------------------------------------------------------
    def _build_dark_warp(self) -> None:
        anchors = D.load_anchors(self.data_dir)
        weights = []
        for r in S.REGIONS:
            for i in range(self.n):
                w = math.log10(1.0 + self.tg.non_christian(r, i))
                weights.append(((r, i), max(0.0, w)))
        tot = sum(w for _, w in weights) or 1.0
        for (r, i), w in weights:
            k = int(round(self.budget_dark * w / tot))
            year = self.years[i]
            for j in range(k):
                place = self._pick_place(r)
                key = f"D{r}{i}{j}"
                y0 = self.emb.y(place=place, jitter_key=key, jitter_scale=0.07)
                span = 1.5 + 3.0 * self.rng.random()
                x0 = S.x_of_year(year)
                x1 = S.x_of_year(year + span * 10)
                ph = self.rng.random() * 6.283
                self.dark.append({"x0": x0, "x1": x1, "y": y0, "phase": ph,
                                  "amp": 0.006 + 0.01 * self.rng.random()})

    # -- export --------------------------------------------------------------------
    def forest(self) -> dict:
        return {
            "seed_xy": list(self.emb.seed_xy()),
            "years": self.years,
            "lineages": self.lineages,
            "links": self.links,
            "dark": self.dark,
            "meta": {
                "n_lineages": len(self.lineages), "n_links": len(self.links),
                "n_dark": len(self.dark),
                "lit_points": sum(len(l.xs) for l in self.lineages),
            },
        }
