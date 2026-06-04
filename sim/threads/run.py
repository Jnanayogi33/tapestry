"""Orchestrate the life-thread layer's data artifacts:

  * data/example_lives.json  — REAL dump from the v1 micro sim (provenance asserted
    there), AUGMENTED with v2 coordinate PATHS (x=time, y=place) + per-point shade so
    the web app can zoom to a single life and trace its gold->gray->gold arc. States
    are NOT fabricated — only coordinates (deterministic from states + embedding) are
    added.
  * data/nav_index.json — strand / event / place / archetype / notable-life -> coord,
    so the navigation menu can fly the camera (no painted dots on the canvas).

The heavy thread FOREST (lineages + links + dark warp) is built by the offline bake
(sim/threads/model.ThreadSim), not serialized here — it would be hundreds of MB.

Run: python -m sim.threads.run
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pipeline import schema as S  # noqa: E402
from sim import data as D  # noqa: E402
from sim.embedding import Embedding  # noqa: E402

DATA_DIR = D.DEFAULT_DATA_DIR

STATE_SHADE = {
    "Practicing": "gold",
    "Affiliated": "gray-gold", "Nominal": "gray-gold", "Lapsed": "gray-gold",
    "Unexposed": "dark", "Unaffiliated": "dark",
    "Martyred": "gold",
}


def shade_of(state: str) -> str:
    return STATE_SHADE.get(state, "gray-gold")


def regenerate_example_lives() -> None:
    """Rerun the v1 micro sim so example_lives.json is a fresh, real dump."""
    try:
        from sim.micro import run as micro_run
        micro_run.main()
    except Exception as exc:  # noqa: BLE001
        print(f"[threads.run] micro sim re-run skipped ({exc}); using existing example_lives.json")


def augment_example_lives(emb: Embedding) -> dict:
    path = os.path.join(DATA_DIR, "example_lives.json")
    doc = json.load(open(path, encoding="utf-8"))
    lives = doc.get("lives", [])
    for life in lives:
        region = life.get("region", "")
        place = S.REGION_PRIMARY_PLACE.get(region, "Rome")
        key = f"life::{life.get('id','x')}"
        traj = life.get("trajectory", [])
        pts = []
        for t in traj:
            yr = t.get("year")
            if yr is None:
                continue
            x = emb.x(yr)
            y = emb.y(place=place, region=region, jitter_key=key)
            pts.append({
                "year": yr, "x": round(x, 5), "y": round(y, 5),
                "state": t.get("state"), "shade": shade_of(t.get("state", "")),
                "driver": t.get("driver"),
            })
        life["path"] = pts
        life["place"] = place
        if pts:
            life["nav"] = {"x": pts[len(pts) // 2]["x"], "y": pts[0]["y"], "zoom": 8}
    doc["coordinate_model"] = {"x": "time (AD30->2025)", "y": "distance-from-Judaea",
                               "augmented_by": "sim.threads.run (coords only; states are the real micro dump)"}
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1)
    return doc


def _era_onset_x(era_note: str) -> float:
    import re
    s = (era_note or "").lower().replace("+", "").replace("–", "-")
    m = re.search(r"(\d{3,4})", s)
    if m:
        return S.x_of_year(int(m.group(1)))
    cmatch = re.search(r"(\d{1,2})(st|nd|rd|th)\s*c", s)
    if cmatch:
        return S.x_of_year((int(cmatch.group(1)) - 1) * 100 + 50)
    return 0.5


def build_nav_index(emb: Embedding) -> dict:
    strands = D.load_strands(DATA_DIR)
    events = D.load_events(DATA_DIR)
    places = D.load_places(DATA_DIR)
    archetypes = D.load_archetypes(DATA_DIR)

    nav = {"strands": [], "events": [], "places": [], "archetypes": []}

    for st in strands:
        ws = st.effect_window_start if st.effect_window_start is not None else st.birth_year
        if ws is None:
            ws = S.TIMELINE_START
        region0 = (st.primary_region or st.regions_affected or ["Roman/Mediterranean"])[0]
        p = emb.resolve_place(st.place or None, region0)
        x = S.x_of_year(max(S.TIMELINE_START, ws))
        y = p.base_y if p else 0.5
        nav["strands"].append({
            "name": st.name, "birth_year": st.birth_year, "death_year": st.death_year,
            "role": st.role, "mechanism_template": st.mechanism_template,
            "regions_affected": st.regions_affected, "primary_region": st.primary_region,
            "place": p.name if p else "", "depth_tier": st.depth_tier,
            "strength": st.strength, "confidence": st.confidence,
            "x": round(x, 5), "y": round(y, 5), "zoom": 5 if st.depth_tier == "Tier 1" else 9,
        })

    for ev in events:
        exp = S.expand_regions_affected(ev.regions)
        ys = [emb.base_y(region=r) for r in exp] or [0.5]
        y = sum(ys) / len(ys)
        nav["events"].append({
            "name": ev.name, "year": ev.year_text, "year_sort": ev.year_sort,
            "regions": ev.regions, "description": ev.description,
            "effect": ev.effect, "mechanism": ev.mechanism,
            "x": round(S.x_of_year(ev.year_sort), 5), "y": round(y, 5), "zoom": 6,
        })

    for pl in places:
        p = emb.places.get(pl.name)
        if not p:
            continue
        nav["places"].append({
            "name": pl.name, "parent_macro_region": pl.parent_macro_region,
            "branch": pl.branch, "distance_norm": pl.distance_norm,
            "era_note": pl.era_note, "notes": pl.notes,
            "x": round(_era_onset_x(pl.era_note), 5), "y": round(p.base_y, 5), "zoom": 7,
        })

    for ar in archetypes:
        region = ar.region if ar.region in S.REGIONS else "Roman/Mediterranean"
        p = emb.resolve_place(region=region)
        nav["archetypes"].append({
            "name": ar.name, "era": ar.era, "region": ar.region,
            "end_state": ar.end_state, "weight": ar.weight,
            "drivers": ar.drivers, "pattern_tags": ar.pattern_tags, "summary": ar.summary,
            "x": round(_era_onset_x(ar.era), 5), "y": round(p.base_y if p else 0.5, 5), "zoom": 6,
        })

    nav["seed"] = {"name": "Christ — Pentecost", "x": 0.0, "y": 0.5, "zoom": 4,
                   "description": "AD 30, Jerusalem. The single thread enters here."}
    return nav


def main() -> int:
    emb = Embedding(DATA_DIR)
    if not emb.places:
        print("[threads.run] no places — run make_fixtures first")
        return 1

    regenerate_example_lives()
    doc = augment_example_lives(emb)
    n_lives = len(doc.get("lives", []))
    n_arc = sum(1 for l in doc.get("lives", []) if l.get("is_target_arc"))

    nav = build_nav_index(emb)
    json.dump(nav, open(os.path.join(DATA_DIR, "nav_index.json"), "w", encoding="utf-8"), indent=1)

    meta = {
        "coordinate_model": {"x": "time", "y": "distance-from-Judaea", "seed_xy": [0.0, 0.5]},
        "example_lives": {"n": n_lives, "target_arc_present": bool(n_arc)},
        "nav_counts": {k: len(v) for k, v in nav.items() if isinstance(v, list)},
    }
    json.dump(meta, open(os.path.join(DATA_DIR, "threads_meta.json"), "w", encoding="utf-8"), indent=1)

    print(f"[threads.run] example_lives: {n_lives} lives (target arc present: {bool(n_arc)})")
    print(f"[threads.run] nav_index: { {k: len(v) for k,v in nav.items() if isinstance(v,list)} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
