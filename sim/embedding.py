"""The v2 coordinate embedding: x = time, y = distance-from-Judaea.

Christ enters at Jerusalem, AD 30, at the vertical CENTER (x=0, y=0.5). Regions fan
outward by great-circle distance from Jerusalem: the Latin West fans UP (toward y=0),
the Orthodox East and the Global South fan DOWN (toward y=1). A life/strand/event that
gives only a macro-region (not a Place) uses that region's PRIMARY place. Small
deterministic per-thread jitter fills each place's band continuously.

This module is the single source of truth for placement; the micro-sim and the offline
bake both import it so the picture and the data agree.
"""
from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import dataclass

from pipeline import schema as S

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "data")

SEED_PLACE = "Judaea"
ORIGIN_REGION = "Roman/Mediterranean"


@dataclass
class Place:
    name: str
    parent_macro_region: str
    branch: str
    lat: float
    lon: float
    distance_km: float
    distance_norm: float

    @property
    def base_y(self) -> float:
        return S.y_of_place(self.branch, self.distance_norm)


class Embedding:
    """Loads places.csv and maps (place|region, year) -> (x, y)."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.places: dict[str, Place] = {}
        self._load(data_dir)
        # Index: region -> list of its places (for stratified sampling in the sim).
        self.by_region: dict[str, list[Place]] = {}
        for p in self.places.values():
            self.by_region.setdefault(p.parent_macro_region, []).append(p)

    def _load(self, data_dir: str) -> None:
        path = os.path.join(data_dir, "places.csv")
        if not os.path.exists(path):
            return
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    self.places[r["name"]] = Place(
                        name=r["name"],
                        parent_macro_region=r.get("parent_macro_region", ""),
                        branch=r.get("branch", "Core"),
                        lat=float(r.get("lat") or 0.0),
                        lon=float(r.get("lon") or 0.0),
                        distance_km=float(r.get("distance_km") or 0.0),
                        distance_norm=float(r.get("distance_norm") or 0.0),
                    )
                except (ValueError, KeyError):
                    continue

    # -- resolution ----------------------------------------------------------------
    def resolve_place(self, place: str | None = None, region: str | None = None) -> Place | None:
        """Resolve to a Place: explicit place if known; else the region's primary
        place; else the origin region's primary place; else None."""
        if place and place in self.places:
            return self.places[place]
        if region:
            for reg in (S.expand_regions_affected([region]) or [region]):
                pl = S.REGION_PRIMARY_PLACE.get(reg)
                if pl and pl in self.places:
                    return self.places[pl]
            # region might itself be a canonical region with a primary place
            pl = S.REGION_PRIMARY_PLACE.get(region)
            if pl and pl in self.places:
                return self.places[pl]
        # Fallback to the origin region's primary place.
        pl = S.REGION_PRIMARY_PLACE.get(ORIGIN_REGION)
        return self.places.get(pl) if pl else None

    # -- coordinates ---------------------------------------------------------------
    def x(self, year: float) -> float:
        return S.x_of_year(year)

    def base_y(self, place: str | None = None, region: str | None = None) -> float:
        p = self.resolve_place(place, region)
        return p.base_y if p else 0.5

    def y(self, place: str | None = None, region: str | None = None,
          jitter_key: str | None = None, jitter_scale: float = 0.045) -> float:
        """Y with deterministic per-thread jitter so lives fill the band continuously.

        Jitter is scaled toward the edges where places are sparser (so the top/bottom
        fill), and clamped to [0,1]. Core stays tight near 0.5.
        """
        p = self.resolve_place(place, region)
        if p is None:
            return 0.5
        y0 = p.base_y
        if jitter_key is not None:
            # Wider band away from center so the far edges fill densely.
            spread = jitter_scale * (0.5 + abs(y0 - 0.5) * 1.4)
            y0 = y0 + jitter_unit(jitter_key) * spread
        return min(0.999, max(0.001, y0))

    def xy(self, year: float, place: str | None = None, region: str | None = None,
           jitter_key: str | None = None) -> tuple[float, float]:
        return self.x(year), self.y(place, region, jitter_key)

    def seed_xy(self) -> tuple[float, float]:
        """Christ: Judaea, AD 30 -> (0, 0.5)."""
        return self.x(S.TIMELINE_START), self.base_y(SEED_PLACE)


def jitter_unit(key: str) -> float:
    """Deterministic pseudo-random value in [-1, 1] from a string key (stable across
    runs; no global RNG, so the embedding is reproducible)."""
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF       # [0,1]
    return 2.0 * n - 1.0


# -- self-test ----------------------------------------------------------------------
def _selftest() -> int:
    emb = Embedding()
    if not emb.places:
        print("[embedding] no places loaded — run make_fixtures first")
        return 1
    sx, sy = emb.seed_xy()
    print(f"seed (Judaea, AD30) -> x={sx:.3f} y={sy:.3f}")
    assert abs(sx) < 1e-9, "seed x should be 0"
    assert abs(sy - 0.5) < 0.02, f"seed y should be ~0.5, got {sy}"
    # West (Americas) fans UP toward 0; East-South (East Asia) fans DOWN toward 1.
    samples = ["Andes (Lima)", "New England", "Rome", "Judaea", "Kiev",
               "Alexandria", "Shanghai (China coast)", "Manila (Philippines)"]
    for name in samples:
        p = emb.places.get(name)
        if p:
            print(f"  {name:26} branch={p.branch:11} dnorm={p.distance_norm:6.2f} base_y={p.base_y:.3f}")
    # Region fallback.
    for reg in S.REGIONS:
        p = emb.resolve_place(region=reg)
        assert p is not None, f"no place resolved for region {reg}"
    # West places should have y < 0.5; East-South y > 0.5.
    west = [p for p in emb.places.values() if p.branch == "West" and p.distance_norm > 30]
    es = [p for p in emb.places.values() if p.branch == "East-South" and p.distance_norm > 30]
    assert all(p.base_y < 0.5 for p in west), "West should fan up (<0.5)"
    assert all(p.base_y > 0.5 for p in es), "East-South should fan down (>0.5)"
    print("[embedding] self-test OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, REPO_ROOT)
    raise SystemExit(_selftest())
