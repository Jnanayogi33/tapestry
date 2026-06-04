"""Typed loaders for the data snapshots the sim consumes.

Reads the CSVs written by make_fixtures.py or sync_from_notion.py, parses
multi-selects (JSON arrays) and coerces numerics, and exposes small structured
records plus helpers (anchor lookup, per-region population schedules) used by both
the macro and micro models. Missing region×year anchor cells are ABSENT (not zero).
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

from pipeline import schema as S

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "data")


def _f(v):
    try:
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _i(v):
    f = _f(v)
    return None if f is None else int(round(f))


def _read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---- records ----------------------------------------------------------------------
@dataclass
class Anchor:
    label: str
    region: str
    year: int
    christians_low: float | None
    christians_central: float | None
    christians_high: float | None
    total_population: float | None
    christians_pct_central: float | None
    practicing_pct: float | None
    confidence: str


@dataclass
class Event:
    name: str
    year_text: str
    year_sort: float
    regions: list[str]
    description: str
    effect: str
    mechanism: str


@dataclass
class Strand:
    name: str
    birth_year: int | None
    death_year: int | None
    primary_region: list[str]
    role: str
    mechanism_template: str
    regions_affected: list[str]
    effect_window_start: int | None
    effect_window_end: int | None
    strength: int
    depth_tier: str
    confidence: str

    def expanded_regions(self) -> list[str]:
        """regions_affected with GLOBAL expanded to all 10 regions."""
        return S.expand_regions_affected(self.regions_affected)


@dataclass
class Life:
    id: str
    name: str
    era: str
    region: str
    start_disposition: str
    trajectory: str
    drivers: str
    summary: str


# ---- loaders ----------------------------------------------------------------------
def load_regions(data_dir: str = DEFAULT_DATA_DIR) -> list[str]:
    rows = _read(os.path.join(data_dir, "regions.csv"))
    names = [r["Name"] for r in rows if r.get("Name")]
    return names or list(S.REGIONS)


def load_anchors(data_dir: str = DEFAULT_DATA_DIR) -> list[Anchor]:
    out = []
    for r in _read(os.path.join(data_dir, "anchors.csv")):
        y = _i(r.get("year"))
        if y is None:
            continue
        out.append(Anchor(
            label=r.get("label", ""),
            region=r.get("region", ""),
            year=y,
            christians_low=_f(r.get("christians_low")),
            christians_central=_f(r.get("christians_central")),
            christians_high=_f(r.get("christians_high")),
            total_population=_f(r.get("total_population")),
            christians_pct_central=_f(r.get("christians_pct_central")),
            practicing_pct=_f(r.get("practicing_pct")),
            confidence=r.get("confidence", "Medium") or "Medium",
        ))
    return out


def load_events(data_dir: str = DEFAULT_DATA_DIR) -> list[Event]:
    out = []
    for r in _read(os.path.join(data_dir, "events.csv")):
        ys = _f(r.get("year_sort"))
        if ys is None:
            continue
        out.append(Event(
            name=r.get("Event Name", ""),
            year_text=r.get("year", ""),
            year_sort=ys,
            regions=S.load_multiselect(r.get("regions")),
            description=r.get("description", ""),
            effect=r.get("effect", "Neutral") or "Neutral",
            mechanism=r.get("mechanism", "") or "",
        ))
    return sorted(out, key=lambda e: e.year_sort)


def load_strands(data_dir: str = DEFAULT_DATA_DIR) -> list[Strand]:
    out = []
    for r in _read(os.path.join(data_dir, "strands.csv")):
        mt = r.get("mechanism_template", "")
        if mt not in S.STRAND_MECHANISM_ENUM:
            # The sim must reject any non-canonical template; skip but it will be
            # caught loudly by validate.py.
            continue
        out.append(Strand(
            name=r.get("name", ""),
            birth_year=_i(r.get("birth_year")),
            death_year=_i(r.get("death_year")),
            primary_region=S.load_multiselect(r.get("primary_region")),
            role=r.get("role", ""),
            mechanism_template=mt,
            regions_affected=S.load_multiselect(r.get("regions_affected")),
            effect_window_start=_i(r.get("effect_window_start")),
            effect_window_end=_i(r.get("effect_window_end")),
            strength=_i(r.get("strength")) or 1,
            depth_tier=r.get("depth_tier", "Tier 3") or "Tier 3",
            confidence=r.get("confidence", "Medium") or "Medium",
        ))
    return out


def load_lives(data_dir: str = DEFAULT_DATA_DIR) -> list[Life]:
    out = []
    for r in _read(os.path.join(data_dir, "lives.csv")):
        out.append(Life(
            id=r.get("id", ""),
            name=r.get("name", ""),
            era=r.get("era", ""),
            region=r.get("region", ""),
            start_disposition=r.get("start_disposition", ""),
            trajectory=r.get("trajectory", ""),
            drivers=r.get("drivers", ""),
            summary=r.get("summary", ""),
        ))
    return out


# ---- derived helpers --------------------------------------------------------------
CONFIDENCE_WEIGHT = {"High": 1.0, "Medium": 0.6, "Low": 0.3, "Speculative": 0.12}

# Fallback modern population shares (sum ~1.0) used only to spread the GLOBAL
# population curve onto regions that lack their own total_population anchors.
FALLBACK_POP_SHARE = {
    "Roman/Mediterranean": 0.0,  # antiquity-only; handled specially below
    "Western Europe": 0.06,
    "Eastern Europe & Russia": 0.05,
    "Middle East & North Africa": 0.06,
    "Sub-Saharan Africa": 0.15,
    "South Asia": 0.24,
    "East Asia": 0.20,
    "Southeast Asia": 0.08,
    "Latin America": 0.08,
    "North America": 0.05,
}


def anchor_index(anchors: list[Anchor]) -> dict[tuple[str, int], Anchor]:
    """(region, year) -> Anchor. region+year are the machine keys."""
    return {(a.region, a.year): a for a in anchors}


def global_population_curve(anchors: list[Anchor]) -> dict[int, float]:
    return {a.year: a.total_population for a in anchors
            if a.region == S.GLOBAL and a.total_population is not None}


def _interp(points: list[tuple[float, float]], x: float) -> float | None:
    """Piecewise-linear interpolation/flat-extrapolation over sorted (x,y) points."""
    if not points:
        return None
    pts = sorted(points)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def region_population(region: str, year: float, anchors: list[Anchor]) -> float:
    """Population of a region at a (possibly non-anchor) year.

    Within a region's own total_population anchor range we interpolate the real
    points. OUTSIDE that range (e.g. modern regions back in antiquity) we do NOT hold
    the nearest value flat — that would put hundreds of millions in East/South Asia at
    AD 100. Instead we scale the nearest known point by the GLOBAL population ratio, so
    proportions stay sane. Regions with no own anchors fall back to a modern share of
    the GLOBAL curve. Always returns a positive number (safe as a denominator).
    """
    gcurve = global_population_curve(anchors)
    g_at = (lambda yr: _interp(list(gcurve.items()), yr)) if gcurve else (lambda yr: None)
    g_here = g_at(year)

    own = sorted((a.year, a.total_population) for a in anchors
                 if a.region == region and a.total_population is not None)
    if own:
        first_y, first_p = own[0]
        last_y, last_p = own[-1]
        if year < first_y:
            ratio = (g_here / g_at(first_y)) if (g_here and g_at(first_y)) else 1.0
            return max(1.0, first_p * ratio)
        if year > last_y:
            ratio = (g_here / g_at(last_y)) if (g_here and g_at(last_y)) else 1.0
            return max(1.0, last_p * ratio)
        v = _interp(own, year)
        return max(1.0, v) if v else 1.0

    if g_here is None:
        return 1.0
    share = FALLBACK_POP_SHARE.get(region, 0.05) or 0.05
    return max(1.0, g_here * share)
