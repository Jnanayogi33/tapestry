=== THE TAPESTRY — SHARED VISION (read first; the same words open the knowledge-base
prompt, so we hold one picture of what we are making) ===
The Tapestry is, finally, a work of art meant to point to the goodness of God: a
vast field of dark threads — every human life — into which a single golden thread
enters at AD 30 and, over two thousand years, kindles light from one to billions,
dimming where it is resisted and rekindling after. You are building one part of
that whole. Your part: you are turning that history into something a person can see
and move through. When a choice is between merely-correct and beautiful-and-true,
choose beautiful-and-true. Hold the whole in view as you work on your part.
You are building the PIPELINE, SIMULATION, and VISUALIZATION for The Tapestry: a
self-calibrating historical simulation of the spread and decline of Christianity
from AD 30 to today, with a macro (geographic) layer AND a micro (individual-life)
layer, plus the zoomable artistic web visualization above. Code and derived data
live in THIS GitHub repo. The ASSUMPTIONS (historical numbers, events, ~100 named
individuals, representative lives) live in a Notion workspace "The Tapestry —
Knowledge Base," which is ALREADY POPULATED (see the concrete IDs and schema below).

=== AUTONOMY DIRECTIVE ===
Work continuously, commit after every step with clear messages. NEVER stop to ask
me questions. If blocked, append to BLOCKERS.md, implement the most reasonable
documented assumption, and CONTINUE. You can run this ENTIRE prompt end-to-end with
NO Notion access — every stage falls back to synthetic fixtures that match the real
schema exactly. The real Notion sync is step 9 and is gated on a NOTION_TOKEN env
var; if that token isn't set, log it and keep using fixtures. Do not wait or idle.

=== KNOWLEDGE BASE — CONCRETE IDS & SCHEMA (already built; use these verbatim) ===
The Notion KB is fully populated. Write config/notion_ids.json with EXACTLY this
content (IDs are real; the only thing the human must still do out-of-band is set the
NOTION_TOKEN env var and share the root page with the integration — until then,
fixtures). Note there are FOUR databases plus ONE narrative page ("Representative
Lives"); "lives" is a PAGE, not a database.

config/notion_ids.json:
{
  "root_page":      "37528b5e-e27a-81ec-9078-f0791d6a01e3",
  "build_log_page": "37528b5e-e27a-8147-b993-ff3023aa70ec",
  "regions":        "6a458332-aa0a-4610-b0b9-07267b0369cf",
  "anchors":        "a87a94ba-308b-4b72-8210-9f7123d26d48",
  "events":         "cd601218-e4c5-4b8a-8d22-9412aa205083",
  "strands":        "f6b38a7a-5ebc-4421-90fd-2d84c75d79bf",
  "lives_page":     "37528b5e-e27a-8146-b19d-dc2bcb353734",
  "data_sources": {
    "regions": "9d388067-bb13-4d63-9c44-e5d5b9a72f47",
    "anchors": "ce75fece-26b6-4056-9c91-684eb52202d5",
    "events":  "fe3ea96f-0425-4384-8181-cc2381521930",
    "strands": "67347f3c-2b74-4b0d-83f9-03a946cf15b7"
  }
}
With notion-client 2.2.1, query databases.query(database_id=<top-level id>). If the
API complains a database has multiple/!single data sources, fall back to the
matching collection id in "data_sources". Read IDs from this file, NEVER by name.

EXACT SCHEMAS (property names are case-sensitive; match them in sync AND fixtures):

REGIONS (10 rows) — title "Name":
  Name (title) | Modern Definition (text) | Boundary Notes (text)

HISTORICAL ANCHORS (54 rows = 14 GLOBAL + 40 regional) — title "label":
  label (title; human label like "GLOBAL — 1900", NOT a machine key)
  region (select; one of the 10 canonical regions OR "GLOBAL")
  year (number)                       <-- region + year are the machine keys
  christians_low (number)             persons (absolute), not millions
  christians_central (number)
  christians_high (number)
  total_population (number)           persons
  christians_pct_central (number)     PERCENTAGE POINTS, e.g. 34.5 means 34.5% — do
                                      NOT multiply by 100 and do NOT treat as 0..1
  practicing_pct (number, NULLABLE)   mostly null; populated only where data exists
  source (text) | source_url (url) | confidence (select) | notes (text)

EVENTS (21 rows) — title "Event Name":
  Event Name (title)
  year (text; may be a range like "634–750 (7th–8th c.)") — display only
  year_sort (number)                  <-- use THIS for timeline positioning/sorting
  regions (multi_select; 10 regions and/or "GLOBAL")
  description (text)
  effect (select; one of: Strong+ , Mild+ , Neutral , Mild- , Strong-)
  mechanism (select; one of: conversion, persecution, schism, secularization,
             translation, revival)   <-- EVENT mechanism vocabulary (6), distinct
                                          from the STRAND mechanism_template (8)
  source (text) | source_url (url)

NAMED STRANDS (100 rows = Tier 1: 25, Tier 2: 40, Tier 3: 35) — title "name":
  name (title)
  birth_year (number, NULLABLE; NEGATIVE = BC, e.g. Jesus birth_year = -4)
  death_year (number, NULLABLE)       a few strands have null years (collectives;
                                      "Alopen"; "The Twelve Apostles of Mexico")
  primary_region (multi_select)
  role (text)
  mechanism_template (select; EXACTLY one of the 8 — the sim must reject any other:)
      SEED, APOSTOLIC_PROPAGATION, INSTITUTIONAL, THEOLOGICAL, TRANSLATION,
      MARTYRDOM, REVIVAL, SUPPRESSION
  regions_affected (multi_select; 10 regions and/or "GLOBAL" = applies to all)
  effect_window_start (number)        <-- the years the strand bends the curve
  effect_window_end (number)
  strength (number, 1–5)              <-- scale each mechanism's magnitude by this
  depth_tier (select; "Tier 1" | "Tier 2" | "Tier 3")
  confidence (select) | sources (text)

CANONICAL REGION STRINGS (exact spelling/punctuation — used for all joins; fixtures
and code MUST match byte-for-byte):
  "Roman/Mediterranean", "Western Europe", "Eastern Europe & Russia",
  "Middle East & North Africa", "Sub-Saharan Africa", "South Asia", "East Asia",
  "Southeast Asia", "Latin America", "North America"   (+ "GLOBAL" in anchors.region,
  events.regions, strands.primary_region / regions_affected)
ENUMS: confidence = High | Medium | Low | Speculative.
Anchor years (the 14): 30, 100, 300, 313, 500, 1000, 1054, 1500, 1517, 1800, 1900,
  1970, 2000, 2025.
MULTI-SELECT SERIALIZATION: store every multi_select cell in CSV as a JSON array
string, e.g. ["Roman/Mediterranean","Western Europe"]; parse with json.loads. The
Notion sync returns these as lists already — serialize them the same way the
fixtures do so the two are interchangeable.

=== DATA REALITIES YOU MUST DESIGN AROUND (so nothing hard-fails) ===
1. PERCENTS are percentage points (34.5 = 34.5%), not fractions. COUNTS are persons.
2. GLOBAL rows exist for all 14 anchor years. REGIONAL rows are intentionally
   SPARSE: only 40 of the 140 possible region×year cells are filled. Present
   regional coverage:
     Roman/Mediterranean: 30, 100, 300, 313, 500
     Middle East & North Africa: 1000, 1500, 1900, 1970, 2000, 2025
     North America / Latin America / Sub-Saharan Africa: 1900, 1970, 2000, 2025
     Western Europe: 1000, 1500, 1900, 1970, 2000, 2025
     Eastern Europe & Russia: 1000, 1900, 1970, 2000, 2025
     East Asia / South Asia / Southeast Asia: 1900, 2025
   The remaining cells are deferred to Phase 2 BY DESIGN. Code must treat missing
   region×year cells as absent, not as zero, and must NOT halt because of them.
3. DOUBLE-COUNT RULE: before ~640 AD, the Levant/Egypt/N.-Africa Christians are
   counted under "Roman/Mediterranean", NOT under "Middle East & North Africa".
   MENA's independent series deliberately STARTS at year 1000. So for years 30–500
   the Roman/Mediterranean row ≈ most of the GLOBAL total on purpose; do not expect
   a full regional partition in antiquity, and do not double-count MENA early.
4. "Europe" in the source dataset (CSGC) is reported combined; the Western Europe and
   Eastern Europe & Russia rows are an apportioned split (confidence = Low). Treat
   them as soft.
5. APOSTOLIC_PROPAGATION per-journey detail (e.g. Paul: 1st ~46–48 Anatolia; 2nd
   ~49–52 Greece; Rome ~60) lives in each Tier-1 strand's SUBPAGE PROSE, NOT in CSV
   columns. The structured contract the sim consumes is: effect_window_start/end +
   regions_affected (a list) + strength. Apply APOSTOLIC_PROPAGATION by ramping the
   conversion-rate step-up across each region in regions_affected over the strand's
   effect window (scaled by strength) — do NOT look for per-journey columns; they
   don't exist in the CSV.
6. "GLOBAL" in a strand's regions_affected means "apply to all 10 regions"
   (Seymour, Graham, John Paul II, Ignatius, Zinzendorf, Mother Teresa, Jesus).
7. SEED occurs exactly once (Jesus, effect window starts 30). Anchor SEED there.

=== DEPENDENCY SETUP (advisory pins, environment-driven; do first) ===
requirements.txt. TRY FIRST (advisory, not mandatory): mesa==2.3.4,
networkx==3.2.1, scipy==1.11.4, numpy==1.26.4, pandas==2.1.4, notion-client==2.2.1.
Install into a venv. If ANY install fails, FALL BACK to latest compatible versions,
install those, record the resolved versions in BLOCKERS.md and requirements.txt. Do
NOT hard-fail or retry the same failing pin. Then DETECT the installed Mesa MAJOR
version at runtime and write all model code against whichever API is present (2.x:
mesa.time schedulers + model.schedule; 3.x: AgentSet / model.agents). Never assume a
Mesa version in prose — read it from the environment. Do NOT use NDlib; implement
belief-state transitions as rate equations in Mesa. Run an import smoke test
printing each version; on failure, fix the pin, log, continue.

=== REPO STRUCTURE ===
  /config (notion_ids.json), /data, /pipeline, /sim/macro, /sim/micro, /viz,
  /reports, README.md, BLOCKERS.md

=== SMOKE TEST GATE (before any long-running work) ===
Minimal end-to-end path on tiny synthetic data: 1 region, 3 timesteps, 5 micro
agents, 10 strands. Confirms PLUMBING, not quality: each stage runs and emits its
file — simulation_output.json, example_lives.json, and a calibration report from a
SINGLE-ITERATION calibration run (NOT converged). Only after all files emit do you
scale to full 10 regions / 14 anchor years / ~100 strands.

=== SYNC CONTRACT ===
config/notion_ids.json (content given above) holds the four DATABASE ids under keys
regions, anchors, events, strands, the Representative-Lives PAGE id under lives_page,
and collection ids under data_sources. pipeline/sync_from_notion.py reads NOTION_TOKEN
from env and IDs from this file (NOT by name), pulling:
  - the four databases into data/{regions,anchors,events,strands}.csv, and
  - the Representative Lives PAGE into data/lives.csv by best-effort parsing its 8
    profile blocks into columns {id, name, era, region, start_disposition,
    trajectory, drivers, summary}. lives is ILLUSTRATIVE seed material, not an
    authoritative input — if the page parse yields < 6 rows or errors, log it and
    fall back to the lives fixture; never hard-fail on lives.
DISTINGUISH TWO FAILURE CASES for the four databases:
  (a) if config/notion_ids.json is missing OR NOTION_TOKEN is unset, log to
      BLOCKERS.md and FALL BACK to fixtures (expected early on);
  (b) if the token and IDs ARE present but the API returns ZERO rows for any
      database, do NOT silently fall back — that almost always means the database
      wasn't shared with the integration. Treat it as a LOUD BLOCKERS.md entry
      naming the empty database, keep the last-good data in place, and continue.
Notion is authoritative for inputs; these snapshots are what the sim reads. Map
Notion property names to the CSV columns above exactly; coerce multi_selects to JSON
arrays; leave practicing_pct / birth_year / death_year empty when null.

=== SYNTHETIC FIXTURES ===
pipeline/make_fixtures.py generates plausible data/*.csv matching the EXACT schema
above — including: all 14 GLOBAL rows in anchors.csv with the same sparse regional
coverage pattern (so downstream code meets real-world sparseness early); percentage-
point percents; persons-scale counts; valid mechanism_template / effect / mechanism
/ confidence enums; JSON-array multi-selects; at least one BC (negative) birth_year;
at least one strand with regions_affected = ["GLOBAL"]; and a lives.csv with >= 6
profiles, one of which encodes an affiliated→unbelieving→strongly-practicing arc.
Every stage must build and test against fixtures before real Notion data exists.

=== VALIDATION ===
pipeline/validate.py checks (wire into GitHub Actions on every push):
  HARD FAILS (exit non-zero):
   - any anchor row with NOT (christians_low <= christians_central <= christians_high)
   - a MISSING GLOBAL row for any of the 14 anchor years (fail loudly, name the year)
   - any required field null except practicing_pct (and except birth_year/death_year,
     which are explicitly nullable on strands)
   - any strand mechanism_template not in {SEED, APOSTOLIC_PROPAGATION, INSTITUTIONAL,
     THEOLOGICAL, TRANSLATION, MARTYRDOM, REVIVAL, SUPPRESSION}
   - any region / effect / mechanism / confidence value outside its canonical enum
  WARNINGS (log to BLOCKERS.md, DO NOT fail — the data is intentionally sparse/soft):
   - regional reconciliation: for an anchor year, sum regional christians_central and
     compare to that year's GLOBAL central. ONLY run this for years with broad
     coverage (>= 8 of 10 regions present: in practice 1900 and 2025) and require
     within ~15%. For 1970 and 2000 (Asian regional cells deferred) and for every
     pre-1900 year (coverage is partial BY DESIGN, and pre-640 is concentrated in
     Roman/Mediterranean to avoid double-counting), emit a WARNING only — never a
     hard fail. Document this rule in the validator's output.
Validation must be safe to run on both fixtures and real Notion snapshots.

=== MACRO SIMULATION (sim/macro) ===
Cohort model in Mesa. 10 regions, each with meta-agent cohorts whose population
weights update over decadal timesteps from the denominators (total_population) in
anchors.csv (remember: percents are percentage points; counts are persons). Belief
is multi-state per cohort: Unexposed -> Affiliated -> Practicing, with back-
transitions -> Lapsed -> Unaffiliated, as rate equations. Spread within and between
regions via time-varying inter-region contact edges seeded from events.csv (use
year_sort for timing, regions for endpoints, effect for sign/magnitude). Apply named
individuals from strands.csv by mechanism_template, scaling each by `strength` and
spreading the effect over [effect_window_start, effect_window_end] across the
regions in regions_affected ("GLOBAL" = all regions):
  SEED instantiates the origin (Jesus, AD 30);
  APOSTOLIC_PROPAGATION applies conversion-rate step-increases per region in
    regions_affected, ramped across the effect window (per-journey detail is in the
    Notion subpage prose, not the CSV — use window + regions_affected + strength);
  INSTITUTIONAL boosts affiliated share top-down;
  THEOLOGICAL raises practicing-conversion without adding affiliates;
  TRANSLATION durably lowers the conversion barrier;
  MARTYRDOM gives a short sharp local amplification near death_year in primary_region;
  REVIVAL surges Affiliated->Practicing;
  SUPPRESSION forces Practicing/Affiliated toward Unaffiliated, scaled by severity.
Expose 8 global parameters: base_conversion_rate, complex_contagion_threshold,
secularization_term, persecution_severity, inter_region_decay, fertility_adv,
martyrdom_amplification, nominal_to_practicing_ratio. Fixed random seed.

=== SELF-CALIBRATION (no human tuning, budget-driven) ===
sim/macro/calibrate.py auto-fits the 8 parameters; let the BUDGET drive the
settings:
  - Fixed random seed throughout.
  - FIRST time a single full run. From that and an overall wall-clock budget
    (default 60 min), compute how many evaluations fit and set scipy's maxfev.
    Average 3 seeded runs per evaluation IF the budget allows >= ~50 evaluations;
    if 3-per-eval leaves fewer than ~30, drop to 1 run per eval; if still too few,
    fix the least-sensitive parameters at midpoints to shrink the search until >=
    ~30 evaluations fit. Record chosen settings and measured per-run time.
  - Nelder-Mead with computed maxfev AND the wall-clock budget as a hard stop; on
    hitting either, write best-so-far params and STOP.
  - Objective: confidence-weighted error between simulated and central anchor
    Christian% per region per anchor year (Speculative low weight, High high), plus
    a penalty keeping regional adherents summing to GLOBAL rows — BUT only apply
    that sum-penalty for years/regions that actually have rows (regional coverage is
    sparse by design; never penalize a deliberately-absent cell). For Speculative
    early centuries score against the low/central/high BAND (zero penalty if inside).
    Score per region per anchor year only where that region×year anchor row exists.
  - On the tiny smoke-test fixture run calibration ONE iteration only.
Write reports/calibration_report.md (settings, per-run time, params, simulated-vs-
anchor curve per region, residuals, whether a cap was hit) and
data/simulation_output.json.

=== MICRO SIMULATION (sim/micro — the heart of the project) ===
Separate individual-agent model. Scope: 1,000-5,000 agents in ONE or TWO regions.
Each agent: innate religiosity_disposition (stable, from a distribution);
belief_state moving Unexposed -> Affiliated -> Lapsed -> Practicing and back; a small
NetworkX social network of family/friends/rivals. Transitions depend on BOTH
disposition AND neighbors' states (complex contagion). Seed from the calibrated
macro set plus patterns in lives.csv (disposition mix and target arcs; lives.csv is
illustrative, so tolerate a missing/partial file).
CRITICAL OUTPUT — REAL, not hand-written: export data/example_lives.json as a
genuine dump of agent state histories FROM AN ACTUAL MICRO RUN. Do NOT synthesize or
hardcode. Assert each exported trajectory was produced by the simulation (verify
against the run's state log). Ensure at least one trajectory shows affiliated ->
unbelieving -> strongly-practicing with the late return driven by believing social
ties (the Notion "Representative Lives" page profiles this as the "Lyudmila" arc —
match its shape). If none emerges, increase agents or run more seeds UP TO A BOUND
(at most 20 additional seeds OR 15 minutes). If it still doesn't emerge, do NOT
fabricate and do NOT loop further: export the closest trajectory found, flag clearly
in the JSON and report that the target arc didn't emerge naturally, and continue.

=== VISUALIZATION (viz — also a work of art) ===
Single-page zoomable app. WebGL (PixiJS) for thread rendering — NOT a filled
streamgraph. Dark ground; luminous GOLD THREADS beginning at a single point (Christ,
AD 30) ramifying outward across time (left -> right), brightening as belief spreads,
dimming/fraying where it declines or is suppressed; additive blending for glow. The
10 regions are faint backdrop envelopes; the THREADS are the art. Reads as light
spreading from one to billions.
Requirements:
  - ANIMATED time reveal: play control sweeps left->right; Pentecost ignites first
    threads; APOSTOLIC_PROPAGATION strands shoot filaments across regions at journey
    years (use effect_window_start and regions_affected); SUPPRESSION events darken
    regions which can rekindle.
  - Smooth zoom/pan from full tapestry to a single decade.
  - Named strands as labeled threads; at full zoom only pivotal ones (Jesus, Paul,
    Constantine, Luther) labeled, more appear on zoom; gate labels by depth_tier
    (Tier 1 first, then Tier 2, then Tier 3) and strength. Click -> name, dates,
    mechanism_template, role, regions_affected from strands.csv.
  - MICRO VIEW (first-class): open an example_lives.json trajectory and watch one
    life move through belief states over time, annotated with what drove each change.
  - Events as subtle timeline markers positioned by year_sort; hover -> description.
  - Read ALL content from data/simulation_output.json + example_lives.json +
    strands.csv + events.csv. Nothing hardcoded. Remember percents are percentage
    points and the anchor title column is "label" (machine keys are region + year).
Build with Vite. Set base to "/<this-repo-name>/" so GitHub Pages assets resolve.
Static bundle.

=== DEPLOY ===
GitHub Actions workflow builds viz/ and deploys to GitHub Pages on push to main.
MUST set permissions: contents: read, pages: write, id-token: write, and use
actions/configure-pages, actions/upload-pages-artifact, actions/deploy-pages. After
deploy, fetch the live URL and confirm a non-empty HTML body with the app's root
element; if blank/404, likely the Vite base path — fix, log, redeploy. Live URL in
README.

=== ORDER OF WORK ===
1. Repo skeleton + README (incl. sync contract) + BLOCKERS.md + config/notion_ids.json
   (write it with the exact content given above).
2. Dependency setup + import smoke test (advisory pins, detect Mesa version).
3. make_fixtures.py + validate.py (validate the fixtures; fixtures must reproduce the
   real sparse regional-coverage pattern and percentage-point percents).
4. SMOKE TEST GATE: tiny end-to-end run emitting all files (single-iteration calib).
5. Scale macro sim to full data; confirm a full run.
6. calibrate.py: time one run, set budget-driven settings, calibrate on full data.
7. Micro sim; confirm example_lives.json is a real dump, provenance assertion
   passes, arc handled within bound.
8. Visualization: threads + animation + zoom + named strands + micro view.
9. Swap fixtures for real Notion sync (once NOTION_TOKEN exists and the root page is
   shared with the integration; config/notion_ids.json is already written in step 1).
   Run validate.py on real data. Handle the two failure cases per the sync contract
   (missing creds -> quiet fixture fallback; zero rows despite creds -> loud blocker
   naming the database). If validation produces only WARNINGS (e.g. regional sums
   don't reconcile for 1970/2000 or pre-1900 — expected, by design), do NOT halt:
   keep last-good data for the build, write specifics to BLOCKERS.md, proceed to
   build/deploy with whatever validates. Recalibrate on whichever dataset is in use.
10. Deploy to Pages with correct permissions + base path; verify the live URL.
Commit after each step. Keep working through the list; do not stop between steps.

=== DEFERRED TO PHASE 2 ===
Gigapixel DZI/OpenSeadragon tiling; pyABC/ABC-SMC calibration; fully coupling
micro<->macro; micro agents in all 10 regions; confidence-fog rendering; full
level-of-detail label systems; audio/scrollytelling; filling the deferred anchor
region×year cells (Asia 1970/2000, finer pre-1900 splits) and deepening the 35
Tier-3 strand stubs.
Begin with step 1 now.
