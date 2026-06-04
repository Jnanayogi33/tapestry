# The Tapestry

> A vast field of dark threads — every human life — into which a single golden thread
> enters at AD 30 and, over two thousand years, kindles light from one to billions,
> dimming where it is resisted and rekindling after.

The Tapestry is a self-calibrating historical simulation of the spread and decline of
Christianity from **AD 30 to today**, rendered as a zoomable, luminous web. It has a
**macro** layer (10 world regions, cohort belief-state dynamics) and a **micro** layer
(individual lives moving through belief over a lifetime), and a **visualization** that
turns both into something a person can see and move through.

**Live visualization:** _set after first GitHub Pages deploy — see step 10._

---

## What's here

| Path | What it is |
|------|------------|
| `config/` | `notion_ids.json` — the Knowledge Base database/page IDs (read by ID, never by name). |
| `data/` | Generated snapshots the sim reads: `regions/anchors/events/strands.csv`, `lives.csv`, plus `simulation_output.json` and `example_lives.json`. |
| `pipeline/` | `make_fixtures.py` (synthetic data matching the real schema), `sync_from_notion.py` (real pull, gated on `NOTION_TOKEN`), `validate.py` (hard/soft checks), `schema.py` (canonical enums & regions). |
| `sim/macro/` | Cohort model in Mesa: 10 regions, multi-state belief, inter-region contagion, named-strand mechanisms; `calibrate.py` auto-fits 8 parameters. |
| `sim/micro/` | Individual-agent model: 1k–5k agents, social network, complex contagion; emits **real** agent life-histories. |
| `viz/` | PixiJS/WebGL single-page zoomable app (Vite). Gold threads on dark ground. |
| `reports/` | `calibration_report.md` and other derived reports. |
| `BLOCKERS.md` | Every assumption / warning / blocker, with the action taken. |

## The data model (Knowledge Base)

Inputs live in a Notion workspace, *The Tapestry — Knowledge Base*, across **four
databases** + **one narrative page**:

- **Regions** (10) — canonical region definitions.
- **Historical Anchors** (54 = 14 GLOBAL + 40 regional) — Christian counts/percent by
  `region` × `year` at 14 anchor years (30, 100, 300, 313, 500, 1000, 1054, 1500,
  1517, 1800, 1900, 1970, 2000, 2025). Percents are **percentage points** (34.5 =
  34.5%); counts are **persons**.
- **Events** (21) — historical inflections with `year_sort`, affected `regions`,
  `effect` sign, and a 6-value `mechanism`.
- **Named Strands** (100) — ~100 individuals/collectives, each with a
  `mechanism_template` (one of 8), an effect window, affected regions, and `strength`.
- **Representative Lives** (page) — 8 illustrative life arcs (seed material for micro).

The 10 canonical regions:
`Roman/Mediterranean`, `Western Europe`, `Eastern Europe & Russia`,
`Middle East & North Africa`, `Sub-Saharan Africa`, `South Asia`, `East Asia`,
`Southeast Asia`, `Latin America`, `North America` (plus `GLOBAL`).

### Data realities the code is built around
1. **Percents are percentage points**, counts are persons.
2. **Regional anchor coverage is sparse by design** — only 40 of 140 region×year
   cells are filled; missing cells are *absent*, never zero, and never hard-fail.
3. **Double-count rule:** before ~640 AD, Levant/Egypt/N.-Africa Christians count
   under *Roman/Mediterranean*, not *Middle East & North Africa* (whose independent
   series starts at year 1000).
4. *Europe* in the source is reported combined; the West/East split is apportioned
   (confidence Low) — treat as soft.

## Sync contract

`pipeline/sync_from_notion.py` reads `NOTION_TOKEN` from the environment and IDs from
`config/notion_ids.json` (**never by name**). It pulls the four databases into
`data/{regions,anchors,events,strands}.csv` and best-effort-parses the Representative
Lives page into `data/lives.csv` (`id, name, era, region, start_disposition,
trajectory, drivers, summary`).

Two failure cases are distinguished:
- **(a) missing creds** — `notion_ids.json` absent *or* `NOTION_TOKEN` unset → log to
  `BLOCKERS.md` and fall back to fixtures (expected early on).
- **(b) zero rows despite creds** — token + IDs present but a database returns zero
  rows → **loud** `BLOCKERS.md` entry naming the empty database, keep last-good data,
  continue. (Almost always: the DB wasn't shared with the integration.)

Notion is authoritative for inputs; the CSV snapshots are what the sim reads.
Multi-selects are serialized as JSON-array strings in CSV and parsed with `json.loads`,
so Notion pulls and fixtures are byte-for-byte interchangeable.

## Quick start

```bash
# 1. Python env + deps (advisory pins; falls back to latest compatible)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python pipeline/smoke_imports.py          # prints resolved versions, detects Mesa major

# 2. Generate fixtures + validate
python pipeline/make_fixtures.py
python pipeline/validate.py

# 3. Smoke test (tiny end-to-end: 1 region, 3 steps, 5 agents, 10 strands)
python run_smoke.py

# 4. Full macro run + calibration
python -m sim.macro.run
python -m sim.macro.calibrate

# 5. Micro run (emits data/example_lives.json from a real run)
python -m sim.micro.run

# 6. Visualization
cd viz && npm install && npm run dev      # or: npm run build
```

To use real Notion data: `export NOTION_TOKEN=...`, share the root page with the
integration, then `python pipeline/sync_from_notion.py && python pipeline/validate.py`.

## Validation

`pipeline/validate.py` (wired into GitHub Actions on every push) **hard-fails** on:
broken `low ≤ central ≤ high`; a missing GLOBAL row for any anchor year; any required
field null (except `practicing_pct`, and `birth_year`/`death_year` on strands); any
`mechanism_template` outside the 8; any region/effect/mechanism/confidence outside its
enum. It **warns** (never fails) on regional sums not reconciling to GLOBAL — and only
checks reconciliation for years with ≥8/10 region coverage (in practice 1900 & 2025).

## Status

See `BLOCKERS.md` for the running log of assumptions and warnings. Phase-2 items
(gigapixel tiling, ABC-SMC calibration, micro↔macro coupling, filling deferred anchor
cells) are intentionally deferred.
