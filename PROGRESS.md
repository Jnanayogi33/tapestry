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
- [x] **2. Re-embed** — DONE. `sim/embedding.py`: loads places.csv, `xy(year,place|region)`,
  region→primary-Place fallback, deterministic per-thread jitter, seed→(0,0.5).
  Self-test passes (`python -m sim.embedding`): Americas→top edge, E.Asia/Pacific→bottom,
  Core centered.
- [x] **3. Micro-life-thread sim** — DONE. `sim/threads/`: `targets.py` (per-region/decade
  lit + gold + count from the v1-calibrated macro run, reconciled to anchors),
  `model.py` (ThreadSim: emergent lineage contagion rooted at the seed + named-strand
  igniters; transmission links = who-lit-whom; dark warp fills Y; thread count ∝
  log(christians) → blaze; fixed seed), `run.py` (regenerates real example_lives.json
  via v1 micro sim + augments with x/y PATHS & shades; writes nav_index.json for
  strands/events/places/archetypes/seed). Lyudmila gold→dark→gold arc verified real.
- [~] **4. Offline bake** — `bake/render.py` (additive splat + Catmull-Rom chains +
  bloom + woven ground + vignette) and `bake/run_bake.py` (consumes the REAL
  `AgentField.export_forest` with calibrated params). Climax look CONVERGED at fast res
  (~13/14, reports/look/i12.md). TODO: full-res climax + era frames + DZI tiles.
- [ ] **4b. Offline bake — full** — additive + bloom + woven ground → gigapixel climax + era
  frames + nav index + DZI tiles.
- [ ] **5. Web app** — deep-zoom + scrub + nav menu + single-life; DELETE old arcs /
  region bands / dots.
- [ ] **6. Deploy** to Pages (permissions + Vite base); verify live URL.
- [ ] **7. Visual iteration loop** — view real output, score vs reference criteria
  (0–2 each, ≥12/14, no zeros), re-bake/re-deploy. Log under `reports/look/iNN.md`.
- [ ] **8. Done** only when deployed AND visual loop converged (≥12/14, no zeros).

## EXACT NEXT ACTION
Step 4 (offline bake): create `bake/` — `bake/render.py` builds the gigapixel CLIMAX
still + per-era frames from `sim.threads.model.ThreadSim`. Additive-accumulate glowing
curves (lineage polylines + curved transmission filaments + faint dark warp) into a
float buffer (numpy); map shade→gold/gray-gold/dark palette; tone-map + BLOOM
(scipy gaussian); composite over a woven dark ground + vignette/frame. Era frames =
reveal up to year T (mask x>x(T)). Emit `viz/public/tapestry/climax.png` (downscaled
inspect copy to reports/look/), era frames, and DZI tiles (`bake/dzi.py`). Then INSPECT
the pixels (Read the PNG) before moving on. Budgets: start ~240k lit pts / 60k dark;
res ~7000x3500 climax. Keep `data/nav_index.json` coords aligned to the image.

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
