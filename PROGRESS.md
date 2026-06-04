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
- [x] **4b. Offline bake — full** — DONE. 6400×3200 JPEG climax + 9 era frames
  (frame_YYYY.jpg) + manifest.json under viz/public/tapestry/. JPEG (photographic →
  ~3MB) to fit disk. Reveal verified (AD313 sparse → 2025 full). DZI tiling stays a
  Phase-2 item; OSD serves the single image with smooth zoom/pan.
- [x] **5. Web app** — DONE & browser-verified. `viz/` rebuilt on OpenSeadragon
  (deep-zoom over the baked image) + timeline scrub through era frames + Play + searchable
  nav menu (strands/events/places/lives/seed from nav_index.json) flying the camera +
  info panels + single-life overlay tracing a REAL trajectory (Lyudmila gold→dark→gold
  with drivers). Old PixiJS arcs/bands/dots deleted. Builds clean; 0 console errors.
- [x] **6. Deploy** — DONE. Built `viz/dist`, published to `gh-pages` (content push,
  no `workflow` scope needed). LIVE: https://jnanayogi33.github.io/tapestry/ — all
  assets (JS/CSS/climax.jpg/frames/nav) return 200 under the `/tapestry/` base path.
- [x] **7. Visual iteration loop** — CONVERGED. Final deployed scoring 14/14, no zeros
  (reports/look/i13-deployed.md). Iterations i01 (imposed/wrong spirit) → i12/iF (real
  contagion, faithful) logged under reports/look/.
- [x] **8. DONE** — site deployed AND visual loop converged, AND it is a genuine
  agent-based simulation of intersecting lives (seed = true origin; spread emergent;
  every gold thread traces to Christ). Residuals documented (truthfulness).

## STATUS: v2 COMPLETE ✓ (+ light∝believers)
All 8 steps done. Live: https://jnanayogi33.github.io/tapestry/ (visual loop 14/14).
LIGHT∝BELIEVERS: the bake pins per-time-column integrated luminance to the GLOBAL
believer count; verified log-log corr 0.9995 (reports/look/proportionality.md). Each lit
life = equal energy (hue, not brightness, distinguishes practicing/nominal); antiquity is
proportionally faint, modern blazes; single-life trace stays full-brightness for early
traceability. Re-bake/verify: `python -m bake.run_bake --frames` (writes proportionality.md).
Optional follow-ups if resumed: (a) move Actions workflows deploy/→.github/workflows/
once a `workflow`-scoped token exists (currently deployed via gh-pages content push);
(b) reduce calibration residuals (Americas immigration, SSA timing) — Phase-3;
(c) DZI tiling for true gigapixel deep-zoom (Phase-2). To re-bake & redeploy:
`python -m bake.run_bake --frames` then rebuild viz and push viz/dist to gh-pages.

--- old step-4 note (kept for history) ---
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
