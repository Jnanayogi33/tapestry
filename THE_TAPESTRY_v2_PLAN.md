# The Tapestry v2 — Holistic Plan

_Goal: make the visualization look and mean like the Gemini reference — a dark woven field of every human life, a single seed of light at the center-left, the light spreading outward and emergent (not drawn), most threads dark, the believing ones gold/fraying/gone, and the present-day edge blazing with billions. Pre-rendered from a real simulation; pure image; navigation by menu, not painted dots._

This is a rebuild of the model, the data, the simulation, and the renderer. It supersedes the live-PixiJS approach. The shared vision is unchanged: a work of art pointing to the goodness of God; choose beautiful-and-true over merely-correct.

---

## 0. The core reframe

| Old (v1) | New (v2) |
|---|---|
| Left→right = **time**; regions stacked as bands | Left→right = **distance from Judaea** (diffusion distance); seed at **center-left**; time is the animated reveal |
| A **line = a region band or a named figure** | A **line = one (sampled) human life**; the field is *filled* with lives, most dark |
| Spread **drawn** as long gold region-to-region arcs | Spread is **emergent** — belief passes where lit threads neighbor/cross dark ones (contagion); no drawn arcs |
| Events/people = **dots** on the chart | **No dots.** People/events are bright threads + **navigation targets** in a menu; click to fly/zoom there |
| Brightness ~flat; lots of dark; right not luminous | Brightness & density **driven by the data**, cresting into a **blazing right edge** |
| Belief = "Christian / not" | Per-thread state: **alive (gold) / frayed-declining (gray-gold) / gone (dark)** |
| Rendered live in the browser | **Pre-rendered offline** (heavy sim → baked gigapixel + time-frames); browser just navigates |

---

## 1. The new coordinate model (the foundational decision)

- **Seed** = Christ, AD 30, at the **left edge, vertically centered**. All golden threads emanate from this one point.
- **X axis = distance from Judaea.** Each place gets a `distance_from_judaea` value (a blend of geography + diffusion friction: seas, mountains, hostile empires). Judaea = 0 (far left); the farthest-reached places (interior Africa, East Asia, the Americas, the Pacific) sit at the right.
- **Y axis = the continuum of human lives.** From the seed the field **fans out** like a wedge/delta — few lives near the origin, the whole of humanity by the right edge — so by the present the threads cover the entire vertical space (as in the reference). Faint sub-regional grouping gives Y gentle structure without becoming a chart.
- **Time = the animated reveal** (a frontier of light moving outward from the seed) **plus** per-thread state changes. The still **2025 frame is the climax**.
- **Why distance-on-X is the right call (and is *true*):** the places far from Judaea — Sub-Saharan Africa, Latin America, Asia, the Pacific — are exactly where 20th–21st-c. Christianity exploded, while parts of the near heartland (MENA, secular Europe) have dimmed. So a distance axis puts the **modern Global-South blaze on the right honestly**, and shows the light having *moved outward* from a now-partly-dark core. Distance and time also broadly correlate (far = reached later), so the axis reads as both "outward" and "onward."
- **Threads as lineages.** A bright thread is a **chain of transmitted belief** flowing outward from the seed, life to life; the **dark warp** behind it is every unlit life. Where many chains converge (high-belief place/era) the additive light goes white-hot. This is precisely the Gemini structure.

---

## 2. How each of your seven directives is met

1. **Christ begins at middle-Y** → seed at left-center; the wedge fans up and down from it.
2. **More granular regions, placed by distance from Judaea** → the 10 macro-regions become ~50 **Places**, each with a `distance_from_judaea` driving its X.
3. **Each line = an individual life (finer unit)** → the renderer's primitive becomes a **sampled life-thread**; dark for unbelief, gold for belief.
4. **No straight region-to-region gold lines; spread emerges from intersections over time** → belief is a **contagion on the life-network**; we delete drawn arcs. Apostles/missionaries become unusually bright, far-reaching threads whose *proximity ignites neighbors* — the spread emerges.
5. **OK to pre-render from async simulation** → we move to a **heavy offline sim + offline bake**; the browser plays/zooms the baked artifact.
6. **Right side should blaze with billions; lives fill the whole Y** → thread **count and brightness scale with `christians_central`** (log-scaled), the wedge fills Y by the present, and additive bloom makes the lit billions read as a blaze. (2.6B *is* billions; concentrated in the far/right places, it reads luminous and stays honest.)
7. **Shades for alive vs frayed/warped vs gone** → a per-thread **belief-state palette**, changing along the thread's length over time.
8. **No ugly dots; navigate by menu** → the canvas stays pure light; a **navigation index** (people, events, places, lives) flies the camera to a coordinate and opens a clean info panel.

---

## 3. Notion v2 — make the knowledge base richer (do this first)

Keep the verified v1 anchors as the **calibration truth** (truthfulness principle stands). Add granular/estimated layers, each flagged with confidence and rationale. New/!evolved sources:

1. **Places (~40–60 rows)** — granular geography. Break each macro-region into peoples/provinces (e.g. Judaea, Galilee, Syria-Antioch, Asia Minor, Greece, Egypt, Carthage/N. Africa, Rome-Italy, Iberia, Gaul, Britain, Germania, Scandinavia, Balkans, Byzantium, Armenia, Mesopotamia/Persia, Arabia, Aksum/Ethiopia, Nubia, Kongo, Yorubaland, East Africa, Southern Africa, Malabar, North India, Ceylon, Tang China, Korea, Japan, Philippines, Vietnam, Java, Mexico, Andes, Brazil, Caribbean, New England, etc.). Fields: `name`, `parent_macro_region`, **`distance_from_judaea`** (0–100, documented), optional `x`,`y` seed coords, `notes`.
2. **Belief Composition timeline** — per Place (or macro-region, inherited) per time-point: population + the fractions **practicing / nominal-affiliated / lapsed / unaffiliated-never** (the alive/frayed/gone split). Drives each thread's state probability. Calibrated so aggregates still match the sourced anchors; the practicing/nominal split is largely modeled (flag it).
3. **Luminaries (relocate + enrich the ~100 strands)** — each becomes a **local igniter** in the field: `place` (granular), `year`, `mechanism_template`, `strength`, **`reach`/`ignition_radius`**, `decay`, and a **`nav_coord`** (where the menu zooms to). Their region-to-region effect is **deleted**; effect emerges as local ignition of nearby threads.
4. **Events (enrich)** — each becomes a **localized field perturbation**: `place(s)`, `time`, **rate effects** (conversion+, suppression−, translation lowers barrier), `reach`, `duration`, `nav_coord`.
5. **Life Archetypes (NEW, the rich core — ~40+)** — parameterized belief-trajectory templates spanning place×era×disposition: the state sequence, the drivers (innate / social ties / event), and timing distributions — including the *believing → frayed → returned* and *born-in → lapsed → secular* shapes. The sim samples these to give every thread a realistic individual life. (This is the v1 "Representative Lives" page, grown from 8 illustrative profiles into a real generative library.)
6. **Render config (NEW, small)** — belief-state → color/alpha map; distance→X scale; wedge geometry; bloom params. Data drives the look.

> Truthfulness: sourced 1900+ and Roman-era anchors are immovable; granular distances, compositions, and archetypes are **modeled estimates** with stated rationale/confidence, and the final simulated lit-fractions are **reconciled to the sourced anchors** so the blaze is dramatic *and* honest.

---

## 4. Simulation v2 — emergent spatial contagion

- Instantiate a large **stratified sample of life-threads** (target ~100k–500k, enough to fill Y densely), allocated across Places×eras by population.
- Each life: `place` (→X), era/birth, `disposition` (from the archetype distribution), a small **social/lineage network** (family + nearby lives in space-time), and a belief trajectory that **emerges** from disposition + neighbors' states (complex contagion) + the **local field** (luminaries and events modify local rates within their reach).
- **No drawn arcs.** Spread is the network lighting up; transmission links (who lit whom) are recorded so the renderer can draw flowing **lineage chains**.
- **Calibrate** global rates (reuse the v1 budget-driven calibrator) so each Place×year aggregate lit-fraction matches the sourced anchors.
- **Emit:** per-thread positions + state-over-time + transmission links; the aggregate density/brightness field; and a **navigation index** (luminary/event/notable-life → coordinate). Runs offline; outputs are baked.

---

## 5. Offline bake — the pre-rendered tapestry

- Lay threads in the distance(X)/wedge(Y) embedding as smooth glowing curves (curl-noise meander + edge-bundling so lineages braid).
- **Additive-accumulate** millions of curve samples into a high-res float buffer (datashader-style or a GPU pass); map belief-state → gold / gray-gold / dark; **tone-map + bloom**; composite over a **woven dark ground with a faint world-relief** and vignette/frame (the museum-object feel).
- Output: (a) a **gigapixel climax still** (2025) for deep zoom, (b) a **time-frame sequence** (per decade/era) for the reveal, (c) the **coordinate index** for navigation. **Tile** to deep-zoom (DZI/IIIF) for OpenSeadragon.

---

## 6. Web app — pure image + navigation

- **Deep-zoom viewer** (OpenSeadragon or tiled Pixi) over the baked tiles; **timeline scrub** swaps the time layer; smooth zoom/pan from whole-tapestry to a single life.
- **Navigation menu / index** (searchable: luminaries, events, places, archetypal lives) → selecting **flies/zooms** the camera to that coordinate and opens a clean **info panel** (bio, dates, mechanism, the *sourced* numbers). No painted markers.
- **Single-life view** = zoom to a sampled thread and trace its alive→frayed→returned arc with driver annotations.
- The canvas shows **only light**; all chrome lives in panels that appear on demand.

---

## 7. Phasing

- **A. Lock the model** (this doc + the two decisions below): coordinate system, state taxonomy, distance scale.
- **B. Notion v2 enrichment:** Places + distances → Belief Composition → relocate Luminaries/Events as local effects + coords → build the Life-Archetype library → render config.
- **C. Simulation v2:** spatial contagion on sampled lives; calibrate to anchors; emit threads + links + field + index.
- **D. Offline bake:** additive render + bloom + woven ground → gigapixel climax + time-frames + index → tiles.
- **E. Web app:** deep-zoom + scrub + nav menu + info panels + single-life; remove all dots/arcs.
- **F. Art polish + verification:** palette/bloom/depth; confirm simulated lit-fractions still reconcile to the sourced anchors (truthfulness pass).

---

## 8. Risks & honest tradeoffs

- **Sampling, not literal billions:** 1 thread ≈ 1 sampled life standing for ~N real lives; we use enough samples to fill Y. Be explicit in the UI.
- **Baked, not live:** interactivity is zoom/scrub/navigate over a pre-rendered artifact, not live simulation. (That's what buys the visual richness.)
- **Distance is modeled:** `distance_from_judaea` is an interpretive metric; we document the rationale and keep it stable.
- **Honesty of the blaze:** the lit-fraction stays tied to the sourced data; the drama comes from density + bloom + concentration in high-belief places, not from inflating the numbers.
- **Scope:** the Notion redo and sim rebuild are large. Prototyping one corridor first (below) de-risks both the look and the pipeline before scaling.

---

## 9. Decisions that change what we build (need your call)

1. **Coordinate model** — distance-on-X with time-as-animation (recommended) vs. keep time-on-X vs. a 2D world-map embedding.
2. **First step / scope** — prototype one corridor end-to-end first (recommended) vs. full Notion enrichment first vs. nail the baked look on synthetic threads first.

Once these two are set, Phase B (the Notion enrichment) starts immediately.
