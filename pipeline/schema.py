"""Canonical constants and (de)serialization helpers for The Tapestry.

Every byte here must match the Knowledge Base schema exactly — region spellings,
enum vocabularies, anchor years, and the multi-select serialization — because
fixtures and real Notion pulls have to be interchangeable. Code reads IDs and data by
these constants, never by ad-hoc strings.
"""
from __future__ import annotations

import json
from typing import Iterable

# --- The 10 canonical regions (exact spelling/punctuation; used for all joins) ----
REGIONS: list[str] = [
    "Roman/Mediterranean",
    "Western Europe",
    "Eastern Europe & Russia",
    "Middle East & North Africa",
    "Sub-Saharan Africa",
    "South Asia",
    "East Asia",
    "Southeast Asia",
    "Latin America",
    "North America",
]
GLOBAL = "GLOBAL"
REGIONS_AND_GLOBAL: list[str] = [*REGIONS, GLOBAL]

# --- The 14 anchor years -----------------------------------------------------------
ANCHOR_YEARS: list[int] = [
    30, 100, 300, 313, 500, 1000, 1054, 1500, 1517, 1800, 1900, 1970, 2000, 2025,
]

# --- Enums -------------------------------------------------------------------------
CONFIDENCE_ENUM = ["High", "Medium", "Low", "Speculative"]
EFFECT_ENUM = ["Strong+", "Mild+", "Neutral", "Mild-", "Strong-"]
# EVENT mechanism vocabulary (6) — distinct from the STRAND mechanism_template (8).
EVENT_MECHANISM_ENUM = [
    "conversion", "persecution", "schism", "secularization", "translation", "revival",
]
# STRAND mechanism_template (8) — the sim must reject any other value.
STRAND_MECHANISM_ENUM = [
    "SEED",
    "APOSTOLIC_PROPAGATION",
    "INSTITUTIONAL",
    "THEOLOGICAL",
    "TRANSLATION",
    "MARTYRDOM",
    "REVIVAL",
    "SUPPRESSION",
]
DEPTH_TIERS = ["Tier 1", "Tier 2", "Tier 3"]

# --- v2 enums ----------------------------------------------------------------------
# Branch governs the Y fan: West fans UP (toward y=0), East-South fans DOWN (toward
# y=1), Core stays centered (y≈0.5).
BRANCH_ENUM = ["Core", "West", "East-South"]
DISPOSITION_ENUM = ["low", "medium", "high"]
END_STATE_ENUM = ["Practicing", "Nominal", "Lapsed", "Unaffiliated", "Martyred"]
# Multi-select vocabularies for Life Archetypes (modeled; documented in BLOCKERS.md).
DRIVERS_ENUM = [
    "family", "social ties", "personal crisis", "conversion experience",
    "persecution", "martyrdom witness", "missionary contact", "scripture/translation",
    "revival", "institution/state", "secular culture", "intellectual doubt",
    "prosperity", "displacement/migration", "mysticism",
]
PATTERN_TAGS_ENUM = [
    "dark warp", "steady faith", "convert", "nominal inheritance",
    "frayed/declining", "lapsed", "returned", "martyr", "persecuted-faithful",
    "secularized", "revival-swept", "diaspora", "underground",
]
# Belief shades the renderer paints (per thread, per time).
BELIEF_SHADES = ["gold", "gray-gold", "dark"]  # Practicing | Nominal/Lapsed | Unexposed/Unaffiliated

# --- Sparse regional anchor coverage (40 of 140 region×year cells, by design) ------
# Missing cells are ABSENT (not zero) and must never hard-fail downstream.
REGIONAL_COVERAGE: dict[str, list[int]] = {
    "Roman/Mediterranean": [30, 100, 300, 313, 500],
    "Middle East & North Africa": [1000, 1500, 1900, 1970, 2000, 2025],
    "North America": [1900, 1970, 2000, 2025],
    "Latin America": [1900, 1970, 2000, 2025],
    "Sub-Saharan Africa": [1900, 1970, 2000, 2025],
    "Western Europe": [1000, 1500, 1900, 1970, 2000, 2025],
    "Eastern Europe & Russia": [1000, 1900, 1970, 2000, 2025],
    "East Asia": [1900, 2025],
    "South Asia": [1900, 2025],
    "Southeast Asia": [1900, 2025],
}

# Years with broad coverage (>= 8 of 10 regions) — the ONLY years for which the
# regional->GLOBAL reconciliation check is a (soft) WARNING rather than skipped.
def years_with_broad_coverage(min_regions: int = 8) -> list[int]:
    counts: dict[int, int] = {}
    for years in REGIONAL_COVERAGE.values():
        for y in years:
            counts[y] = counts.get(y, 0) + 1
    return sorted(y for y, c in counts.items() if c >= min_regions)


# --- CSV column contracts (order matters for stable diffs) -------------------------
REGIONS_COLUMNS = ["Name", "Modern Definition", "Boundary Notes"]

ANCHORS_COLUMNS = [
    "label", "region", "year",
    "christians_low", "christians_central", "christians_high",
    "total_population", "christians_pct_central",
    # v2 belief-composition columns (percentage points). GLOBAL rows populated;
    # regional rows intentionally null -> DERIVED (see derive_composition).
    "practicing_pct", "nominal_pct", "lapsed_pct", "unaffiliated_pct",
    "source", "source_url", "confidence", "notes",
]

EVENTS_COLUMNS = [
    "Event Name", "year", "year_sort", "regions", "description",
    "effect", "mechanism",
    # v2: localized field perturbation
    "places", "rate_effect", "reach", "duration_years",
    "source", "source_url",
]

STRANDS_COLUMNS = [
    "name", "birth_year", "death_year", "primary_region", "role",
    "mechanism_template", "regions_affected",
    "effect_window_start", "effect_window_end", "strength",
    # v2: local igniter geometry
    "place", "ignition_radius", "effect_decay",
    "depth_tier", "confidence", "sources",
]

LIVES_COLUMNS = [
    "id", "name", "era", "region",
    "start_disposition", "trajectory", "drivers", "summary",
]

# v2 NEW tables ---------------------------------------------------------------------
PLACES_COLUMNS = [
    "name", "parent_macro_region", "branch", "lat", "lon",
    "distance_km", "distance_norm", "era_note", "notes",
]

ARCHETYPES_COLUMNS = [
    "name", "era", "region", "start_disposition", "belief_path", "end_state",
    "weight", "drivers", "pattern_tags", "summary",
]

# Multi-select columns by file (serialized as JSON-array strings in CSV).
MULTISELECT_COLUMNS = {
    "events": ["regions"],
    "strands": ["primary_region", "regions_affected"],
    "archetypes": ["drivers", "pattern_tags"],
}


# --- Multi-select (de)serialization ------------------------------------------------
def dump_multiselect(values: Iterable[str] | str | None) -> str:
    """Serialize a multi-select cell to a JSON-array string for CSV storage.

    Accepts a list/tuple (from a Notion pull) or an already-serialized string
    (idempotent) or None -> "[]".
    """
    if values is None:
        return "[]"
    if isinstance(values, str):
        s = values.strip()
        if s.startswith("["):
            # Already a JSON array string; normalize.
            try:
                return json.dumps([str(v) for v in json.loads(s)])
            except json.JSONDecodeError:
                return json.dumps([s]) if s else "[]"
        return json.dumps([s]) if s else "[]"
    return json.dumps([str(v) for v in values])


def load_multiselect(cell: str | float | None) -> list[str]:
    """Parse a multi-select CSV cell (JSON-array string) back into a list."""
    if cell is None:
        return []
    if isinstance(cell, (list, tuple)):
        return [str(v) for v in cell]
    s = str(cell).strip()
    if not s or s.lower() == "nan":
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
        return [str(parsed)]
    except json.JSONDecodeError:
        # Fall back to a bare value or comma-separated string.
        return [p.strip() for p in s.split(",") if p.strip()]


def expand_regions_affected(values: Iterable[str]) -> list[str]:
    """Expand a regions_affected / regions list: "GLOBAL" -> all 10 regions."""
    out: list[str] = []
    for v in values:
        if v == GLOBAL:
            out.extend(REGIONS)
        elif v in REGIONS:
            out.append(v)
    # De-dupe, preserve canonical order.
    seen = set()
    return [r for r in REGIONS if (r in out and not (r in seen or seen.add(r)))]


# ===================================================================================
# v2 LAYOUT MODEL — x(t)=time, y(place)=distance-from-Judaea fanning from center
# ===================================================================================
import math

# Christ enters at Jerusalem, AD 30, at the vertical center.
JERUSALEM_LAT = 31.7683
JERUSALEM_LON = 35.2137
TIMELINE_START = 30
TIMELINE_END = 2025

# Each macro-region's PRIMARY place (used when a life/strand/event gives only a
# region, not a Place). Names MUST exist in places.csv. The seed (Jesus) is Judaea.
REGION_PRIMARY_PLACE = {
    "Roman/Mediterranean": "Rome",
    "Western Europe": "Gaul (Lyon)",
    "Eastern Europe & Russia": "Kiev",
    "Middle East & North Africa": "Alexandria",
    "Sub-Saharan Africa": "Yorubaland (West Africa)",
    "South Asia": "Malabar Coast",
    "East Asia": "Shanghai (China coast)",
    "Southeast Asia": "Manila (Philippines)",
    "Latin America": "Bahia (Brazil)",
    "North America": "New England",
}

# practicing_ratio (practicing as a share of all Christians) for DERIVING regional
# composition where Notion leaves it null. Values from the v2 prompt; modeled — FLAG.
PRACTICING_RATIO = {
    "Roman/Mediterranean": 0.9,        # persecuted/early -> mostly committed
    "Western Europe": 0.25,            # heavily nominal/secular
    "Eastern Europe & Russia": 0.20,   # 0.15-0.25
    "Middle East & North Africa": 0.7,
    "Sub-Saharan Africa": 0.7,         # modern Global South 0.6-0.75
    "South Asia": 0.7,
    "East Asia": 0.7,
    "Southeast Asia": 0.7,
    "Latin America": 0.6,              # Global South, somewhat nominal Catholic
    "North America": 0.45,
    "GLOBAL": 0.45,
}
PRACTICING_RATIO_MEDIEVAL = 0.55       # pre-1500 anywhere: ~0.5-0.6


def haversine_km(lat1, lon1, lat2=JERUSALEM_LAT, lon2=JERUSALEM_LON) -> float:
    """Great-circle distance (km) from (lat1,lon1) to Jerusalem by default."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def x_of_year(year: float) -> float:
    """x(t) = (year - 30) / (2025 - 30), clamped to [0, 1]."""
    x = (year - TIMELINE_START) / (TIMELINE_END - TIMELINE_START)
    return max(0.0, min(1.0, x))


def branch_sign(branch: str) -> int:
    return -1 if branch == "West" else (1 if branch == "East-South" else 0)


def y_of_place(branch: str, distance_norm: float) -> float:
    """y = 0.5 + sign * 0.5 * d, where d = distance_norm/100 in [0,1].

    Christ/Judaea (Core, d≈0) at center y≈0.5; West fans up toward 0; East-South fans
    down toward 1. Per-thread jitter is added by the caller, not here.
    """
    d = max(0.0, min(1.0, (distance_norm or 0.0) / 100.0))
    return 0.5 + branch_sign(branch) * 0.5 * d


def derive_composition(region: str, year: int, christians_pct_central: float | None,
                       practicing_pct: float | None) -> dict:
    """Derive (practicing, nominal, lapsed, unaffiliated) percentage points for a
    region×year from christians_pct_central using the modeled practicing_ratio.

    Rule (v2 prompt): practicing = practicing_pct if present else
    christians_pct_central × practicing_ratio; (nominal+lapsed) = christians_pct_central
    − practicing; unaffiliated = 100 − christians_pct_central. The nominal/lapsed split
    is modeled (2/3 nominal, 1/3 lapsed by default). Returns a dict; 'modeled' flags it.
    """
    cpc = christians_pct_central
    if cpc is None:
        return {"practicing": None, "nominal": None, "lapsed": None,
                "unaffiliated": None, "modeled": True}
    ratio = PRACTICING_RATIO_MEDIEVAL if year < 1500 else PRACTICING_RATIO.get(region, 0.45)
    practicing = practicing_pct if practicing_pct is not None else cpc * ratio
    practicing = max(0.0, min(cpc, practicing))
    rest = max(0.0, cpc - practicing)          # nominal + lapsed
    nominal = rest * (2.0 / 3.0)
    lapsed = rest - nominal
    unaffiliated = max(0.0, 100.0 - cpc)
    return {"practicing": practicing, "nominal": nominal, "lapsed": lapsed,
            "unaffiliated": unaffiliated, "modeled": practicing_pct is None}
