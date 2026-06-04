# The Tapestry — v2 PROGRESS ledger

Durable state for resuming by hand. A fresh run resumes from this file alone:
reopen Claude Code in this repo and say **"continue from PROGRESS.md"**, then pick up
at the EXACT NEXT ACTION below. Update this after every step and commit immediately
("checkpoint: <step>").

**v2 vision:** X = time (AD30→2025); Y = distance-from-Judaea (Christ at center-left,
West fans up, East-South fans down). The primitive is a sampled LIFE thread. Spread is
emergent contagion (no drawn arcs). Pre-rendered/baked gigapixel + era frames; the web
app navigates the image (no dots). Right edge BLAZES by 2025. Target look:
`reference/target_tapestry.png`.

---

## Step list & status

- [x] **v1** — complete & deployed: https://jnanayogi33.github.io/tapestry/
- [x] **1. Sync v2 + fixtures + validate** — DONE. `schema.py` extended (places/
  archetypes columns, branch/disposition/end_state/drivers/pattern_tags enums,
  composition cols on anchors, v2 cols on strands/events, layout helpers
  x_of_year/y_of_place/haversine/derive_composition). `fixtures_v2.py` (49 places w/
  objective haversine distance + branch; 36 archetypes, dark-warp highest weight).
  `make_fixtures.py` emits places.csv+archetypes.csv + extended cols.
  `validate.py` + `sync_from_notion.py` extended. Fixtures validate 0/0.
- [ ] **2. Re-embed** — x(t), y(place), region→primary-Place fallback, seed at (0,0.5).
- [ ] **3. Micro-life-thread sim** — sample lives from archetypes by weight/region/era;
  emergent contagion; strands as local igniters; calibrate lit-fraction to composition;
  real example_lives.json (provenance assertion).
- [ ] **4. Offline bake** — additive + bloom + woven ground → gigapixel climax + era
  frames + nav index + DZI tiles.
- [ ] **5. Web app** — deep-zoom + scrub + nav menu + single-life; DELETE old arcs /
  region bands / dots.
- [ ] **6. Deploy** to Pages (permissions + Vite base); verify live URL.
- [ ] **7. Visual iteration loop** — view real output, score vs reference criteria
  (0–2 each, ≥12/14, no zeros), re-bake/re-deploy. Log under `reports/look/iNN.md`.
- [ ] **8. Done** only when deployed AND visual loop converged (≥12/14, no zeros).

## EXACT NEXT ACTION
Step 2 (re-embed): create `sim/embedding.py` exposing place→(x,y) using
`schema.x_of_year`/`y_of_place`, loading `data/places.csv`, with the
region→primary-Place fallback and deterministic per-thread Y jitter. Seed (Jesus) →
(x=0, y=0.5). Add a tiny self-test (e.g. assert Judaea≈0.5, Americas near 0, East
Asia near 1). This is the coordinate foundation the micro-sim (step 3) and bake (step
4) both consume.

## Key decisions / assumptions (see BLOCKERS.md for the full log)
- Layout per v2 prompt: `x=(year-30)/1995`; `y=0.5+sign*0.5*(distance_norm/100)`,
  sign = West −1 / East-South +1 / Core 0. Helpers in `pipeline/schema.py`.
- No Notion token → fixtures. Places' `distance_km` computed by haversine from
  Jerusalem (objective); `distance_norm` = 100×km/maxkm. Branch hand-assigned.
- Archetype `drivers`/`pattern_tags`/`end_state` enums defined in `schema.py` (modeled).
- Regional belief composition is DERIVED (`schema.derive_composition`) using modeled
  `PRACTICING_RATIO`; GLOBAL composition is populated in fixtures and sums to ~100.

## Last commit
(to be updated each checkpoint)
