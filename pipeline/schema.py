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
    "total_population", "christians_pct_central", "practicing_pct",
    "source", "source_url", "confidence", "notes",
]

EVENTS_COLUMNS = [
    "Event Name", "year", "year_sort", "regions", "description",
    "effect", "mechanism", "source", "source_url",
]

STRANDS_COLUMNS = [
    "name", "birth_year", "death_year", "primary_region", "role",
    "mechanism_template", "regions_affected",
    "effect_window_start", "effect_window_end", "strength",
    "depth_tier", "confidence", "sources",
]

LIVES_COLUMNS = [
    "id", "name", "era", "region",
    "start_disposition", "trajectory", "drivers", "summary",
]

# Multi-select columns by file (serialized as JSON-array strings in CSV).
MULTISELECT_COLUMNS = {
    "events": ["regions"],
    "strands": ["primary_region", "regions_affected"],
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
