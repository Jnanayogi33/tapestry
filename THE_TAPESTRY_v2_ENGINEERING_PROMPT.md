=== THE TAPESTRY v2 — SHARED VISION (read first) ===
The Tapestry is a work of art meant to point to the goodness of God: a vast field of
dark threads — every human life — into which a single golden thread enters at AD 30
and, over two thousand years, kindles light from one to billions, dimming where it is
resisted and rekindling after. You are evolving the EXISTING repo (pipeline +
simulation + visualization) from a v1 annotated timeline into the v2 vision below.
When a choice is between merely-correct and beautiful-and-true, choose
beautiful-and-true.

=== WHAT CHANGES (v1 → v2) — the whole point of this pass ===
1. **Layout.** X stays TIME (AD 30→2025). Y becomes DISTANCE FROM JUDAEA: Christ
   enters at the VERTICAL CENTER (AD 30); regions fan outward by great-circle distance
   from Jerusalem — branch "West" upward, branch "East-South" downward, "Core" center.
2. **The primitive is a LIFE.** The field is filled, top to bottom, with one thin
   thread per SAMPLED human life. Most are DARK (unbelief). Believing lives are GOLD
   (practicing) / GRAY-GOLD (nominal/frayed) / fading to dark (lapsed). No region
   bands of hatching; no scatter dots.
3. **Spread is EMERGENT.** Delete the long straight region-to-region gold arcs.
   Belief passes where a lit thread neighbors a dark one (contagion on the life
   network). Apostles/missionaries are unusually bright, far-reaching threads that
   IGNITE THEIR NEIGHBORS locally — the spread emerges from intersections over time.
4. **Pre-rendered.** It is OK (preferred) to BAKE the visual offline from the
   simulation — a gigapixel "climax" image + per-era frames — and have the browser
   navigate it. You are not required to render every thread live.
5. **The right edge BLAZES.** Thread count + brightness scale with the data; by 2025 a
   large, luminous fraction of the field is lit (2.6B is billions). No big dark voids.
6. **No dots.** Events/people are navigation TARGETS in a menu that flies/zooms the
   camera to their place in the image and opens a clean panel — the canvas stays pure
   light.
Target look: the woven dark tapestry with luminous gold fiber-optic threads (the
Gemini reference in /Tapestry/). Additive bloom; woven ground; gold/gray/dark shades.

=== AUTONOMY DIRECTIVE ===
Work continuously, commit after every step, NEVER stop to ask. If blocked, append to
BLOCKERS.md, take the most reasonable documented assumption, CONTINUE. Everything runs
on fixtures with no Notion access; the real sync is gated on NOTION_TOKEN.

=== DATA CONTRACT (v2) — the Notion KB is already enriched ===
Write/overwrite config/notion_ids.json with EXACTLY this (IDs are real; only NOTION_TOKEN
+ sharing the root page with the integration remain out-of-band; until then, fixtures):
{
  "root_page":      "37528b5e-e27a-81ec-9078-f0791d6a01e3",
  "build_log_page": "37528b5e-e27a-8147-b993-ff3023aa70ec",
  "regions":        "6a458332-aa0a-4610-b0b9-07267b0369cf",
  "anchors":        "a87a94ba-308b-4b72-8210-9f7123d26d48",
  "events":         "cd601218-e4c5-4b8a-8d22-9412aa205083",
  "strands":        "f6b38a7a-5ebc-4421-90fd-2d84c75d79bf",
  "places":         "f5680a00-979f-499d-8ef2-8c890392d39a",
  "archetypes":     "9a703ed0-8a20-406a-933a-4164670bc896",
  "lives_page":     "37528b5e-e27a-8146-b19d-dc2bcb353734",
  "data_sources": {
    "regions":    "9d388067-bb13-4d63-9c44-e5d5b9a72f47",
    "anchors":    "ce75fece-26b6-4056-9c91-684eb52202d5",
    "events":     "fe3ea96f-0425-4384-8181-cc2381521930",
    "strands":    "67347f3c-2b74-4b0d-83f9-03a946cf15b7",
    "places":     "fc3f41df-01f7-4804-a406-0896e7d0814a",
    "archetypes": "9e8d984e-1fef-445a-86e1-5ca44f82ff4b"
  }
}

NEW tables (sync to data/places.csv and data/archetypes.csv):
- **Places** (49 rows): name, parent_macro_region (one of the 10 macro-regions),
  branch (Core|West|East-South), lat, lon, distance_km (great-circle km from
  Jerusalem — OBJECTIVE), distance_norm (0–100), era_note, notes.
- **Life Archetypes** (36): name, era, region (10 + GLOBAL), start_disposition
  (low|medium|high), belief_path (text state sequence), end_state
  (Practicing|Nominal|Lapsed|Unaffiliated|Martyred), weight (number — relative
  sampling prevalence; the "dark warp" archetypes carry the highest weight),
  drivers (multi_select), pattern_tags (multi_select), summary.

EXTENDED tables (new columns):
- **Anchors** + nominal_pct, lapsed_pct, unaffiliated_pct (number). With practicing_pct
  these are the BELIEF COMPOSITION. GLOBAL rows (all 14) are populated; regional rows
  are intentionally null — DERIVE them (rule below).
- **Strands** + place (text → a Places name), ignition_radius, effect_decay (number).
- **Events** + places (text), rate_effect (text), reach, duration_years.

Conventions unchanged: percents are PERCENTAGE POINTS (34.5 = 34.5%); counts are
PERSONS; multi-selects serialize as JSON arrays; anchors title is `label` (keys are
region+year); strand years may be negative (BC). Full detail + the v1 schema are in the
Build Log; the **"v2 ENRICHMENT"** section there is authoritative for everything below.

=== LAYOUT MODEL (implement exactly) ===
- **x(t) = (year − 30) / (2025 − 30)** in [0,1], left→right.
- **y(place):** let d = place.distance_norm/100 in [0,1]; sign = (branch=="West" ? −1 :
  branch=="East-South" ? +1 : 0). **y = 0.5 + sign × 0.5 × d** (Christ/Judaea at center
  y≈0.5; West fans up toward 0, East-South down toward 1). Add small per-thread jitter so
  lives fill the band continuously.
- A life/strand/event whose data gives only a macro-region (not a Place) uses its
  **region → primary Place** (see Build Log map; e.g. Western Europe→Gaul(Lyon),
  Sub-Saharan Africa→West Africa(Yorubaland), East Asia→China coast(Shanghai), Latin
  America→Brazil(Bahia), MENA→Egypt(Alexandria), …). The seed (Jesus) is Judaea, y=0.5,
  x=0.

=== THREADS = SAMPLED LIVES (micro-sim is now the SOURCE of the picture) ===
- Instantiate a large STRATIFIED SAMPLE of life-threads (target ~100k–500k; enough to
  fill Y densely), allocated across regions×eras by population (anchors.total_population)
  and sampled from **Life Archetypes** weighted by `weight` (so most threads are the
  high-weight DARK "never lit" archetypes, and the believing shapes appear in realistic
  proportion).
- Each life: a Place (→x,y), birth era, disposition, a small NetworkX neighborhood
  (family + spatial neighbors), and a belief trajectory that EMERGES from disposition +
  neighbors' states (complex contagion) + the LOCAL field (strands/events modify rates
  within their reach). No drawn arcs. Record transmission links (who lit whom) so the
  renderer can draw flowing lineage threads.
- **Strand effect = LOCAL ignition:** within ignition_radius of the strand's (x,y),
  across [effect_window_start, effect_window_end], raise neighbors' conversion/practicing
  per mechanism_template, scaled by strength; decay after by effect_decay. (ignition_radius
  ≈ 0.6 + 0.25×strength if null; effect_decay ≈ 0.15/decade if null.) SEED = Jesus at
  (0, 0.5).
- **Calibrate** so each region×year aggregate lit-fraction matches the anchors'
  composition (practicing→gold share; christians_pct→lit share). Reuse the v1 budget-driven
  calibrator.

Belief→shade (per thread, per time): **GOLD = Practicing; GRAY-GOLD = Nominal/Lapsed (frayed);
DARK = Unexposed/Unaffiliated.** Region×year target fractions come from composition:
gold=practicing_pct, gray=nominal_pct+lapsed_pct, dark=unaffiliated_pct.
**Regional composition derivation (rule):** practicing = practicing_pct if present else
christians_pct_central × practicing_ratio; nominal+lapsed = christians_pct_central −
practicing; unaffiliated = 100 − christians_pct_central. practicing_ratio by era/region is
in the Build Log (persecuted≈0.9; medieval≈0.5–0.6; modern Global South≈0.6–0.75; W.Europe≈0.25;
N.America≈0.45; E.Europe/Russia≈0.15–0.25; MENA≈0.7). FLAG the split as modeled.

=== OFFLINE BAKE (the pre-rendered tapestry) ===
- Lay the sampled threads in the (x,y) embedding as smooth glowing curves (curl-noise
  meander + edge-bundling so lineages braid). Additive-accumulate into a high-res float
  buffer; map belief-state → gold / gray-gold / dark; tone-map + BLOOM; composite over a
  woven dark ground (you may use a darkened tile of the Gemini reference plate) with
  vignette/frame.
- Emit: (a) a gigapixel CLIMAX still (2025), (b) per-era FRAMES for the animated reveal,
  (c) a coordinate INDEX mapping each strand/event/notable-life → (x,y[,zoom]) for
  navigation. Tile to deep-zoom (DZI/IIIF).

=== WEB APP (pure image + navigation) ===
- Deep-zoom viewer (OpenSeadragon or tiled Pixi) over the baked tiles; timeline scrub
  swaps the era frame; smooth zoom/pan from whole-tapestry to a single life.
- **Navigation MENU/index** (searchable: strands, events, places, archetypal lives) →
  selecting flies/zooms to its coordinate and opens a clean info panel (bio, dates,
  mechanism, the SOURCED numbers). **No painted markers/dots.**
- **Single-life view**: zoom to one sampled thread and trace its gold→gray→gold arc with
  driver annotations (the example_lives.json provenance assertion from v1 still applies).

=== VALIDATION (extend pipeline/validate.py) ===
Keep v1 checks. ADD: every Place has a numeric distance_km and a valid branch; every
archetype's drivers/pattern_tags/end_state are in their enums; for GLOBAL anchors,
practicing+nominal+lapsed ≈ christians_pct_central and the four sum to ~100 (±0.2) —
already validated in Notion, re-check on sync. Regional composition is DERIVED, not
required to be present.

=== VISUAL ITERATION LOOP — iterate until it LOOKS right (do NOT stop at "it runs") ===
Building it is not the goal. It must LOOK like the target. "It compiles and deploys" is
NOT done. After each bake AND after deploy, you must actually LOOK at the fully generated
output and keep refining until it resembles the reference.
- Put the look-target at reference/target_tapestry.png (the Gemini reference image saved in
  /Tapestry/). If absent, use the written criteria below.
- VIEW the real output with your image-reading ability: open the baked gigapixel climax
  (downscaled to ~2000px), 3–4 era frames, AND a screenshot of the deployed page if a
  headless screenshot is available. Do NOT assume — inspect the actual pixels.
- Score the output against these criteria (0–2 each) and write scores + the thumbnail to
  reports/look/iNN.md:
  1. A single bright seed at LEFT-CENTER from which everything emanates.
  2. Threads fan by distance with Christ centered on Y (near regions near center; far
     regions — Americas, East Asia, Pacific — at the top/bottom edges).
  3. Threads flow and braid organically — NO straight region-to-region arcs.
  4. Three shades read clearly: gold (alive), gray-gold (frayed/declining), dark (gone).
  5. The RIGHT EDGE BLAZES and the field is FILLED top-to-bottom by 2025 — no big dark voids.
  6. Additive bloom/glow over a woven dark ground — a museum object, not a chart.
  7. Pure light — NO dots, labels, gridlines, or UI baked into the image.
- If total < 12/14 OR any criterion scores 0, change SPECIFIC parameters and RE-BAKE:
  weak glow → raise bloom threshold/intensity; too dark / right not lit → increase thread
  count and the lit-density scaling (log map of christians_central) and bloom; straight
  lines → increase curl-noise meander + edge-bundling; voids → sample more lives + jitter to
  fill Y; flat → add depth layers + vignette; wrong color → fix palette.
- Repeat up to ~12 iterations, keeping the best; log every iteration (params → screenshot →
  score) under reports/look/. CONVERGENCE = it visually matches the reference (>=12/14, no
  zeros). Only then is the visual done.

=== RESUMING (simple — the human resumes by hand) ===
This build is long and will hit usage limits; that's fine — it will just be continued later.
Make resuming painless:
- Maintain PROGRESS.md as a durable ledger: the full step list (1–8 incl. the visual loop),
  which steps are done, the EXACT next action, and the last commit hash. Update it after
  EVERY step and commit immediately ("checkpoint: <step>"). A fresh run must be able to
  resume from PROGRESS.md alone.
- If you hit a usage limit or are interrupted, stop cleanly — PROGRESS.md + the last commit
  hold all the state. To resume, the human reopens Claude Code in this repo and either runs
  `claude --continue` or simply says "continue from PROGRESS.md"; pick up at the next
  unfinished step.
- You are finished only when the site is deployed AND the visual loop has converged
  (>=12/14, no zeros).

=== ORDER OF WORK ===
1. Sync v2 (add places, archetypes; extended anchor/strand/event columns) + matching
   fixtures + validate.
2. Re-embed: implement x(t), y(place) and the region→primary-Place fallback; render the
   seed at (0, 0.5).
3. Micro-life-thread sim: sample lives from archetypes by weight/region/era; emergent
   contagion; strands as local igniters; calibrate lit-fraction to composition. Confirm
   example_lives.json is a real dump.
4. Offline bake: additive + bloom + woven ground → gigapixel climax + era frames + nav
   index + tiles.
5. Web app: deep-zoom + scrub + nav menu + single-life; DELETE the old arcs, region-band
   hatching, and dots.
6. Deploy to Pages (correct permissions + Vite base); verify the live URL.
7. VISUAL ITERATION LOOP: view the fully rendered output and iterate (re-bake, re-deploy)
   until it matches the reference (>=12/14, no zeros). See the section above.
8. Stop only when the site is deployed AND the visual loop has converged.
Commit after each step and update PROGRESS.md after each step; keep going through the steps.
If you run out of usage, stop cleanly — you'll be resumed later (`claude --continue`, or the
human says "continue from PROGRESS.md").

=== DEFERRED TO PHASE 3 ===
Backfilling per-region composition and per-strand place/radius in Notion (derive for now);
fully coupling micro↔macro; audio/scrollytelling; gigapixel LOD label systems.
Begin with step 1 now.
