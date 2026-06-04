# BLOCKERS & DOCUMENTED ASSUMPTIONS

This log records every point where the build was blocked, made a documented
assumption, or hit a warning. Per the autonomy directive, the build never stops:
each entry below records the most reasonable assumption taken and the work continued.

Format: `[STEP] [LEVEL] (date) — message`. LEVEL ∈ {INFO, ASSUMPTION, WARNING, BLOCKER}.

---

## Step 1 — Skeleton
- [1] INFO (2026-06-03) — Repo initialized. `Is a git repository` was false at start;
  ran `git init`. Working dir contains `ENGINEERING_PROMPT.md` (the build spec).
- [1] INFO (2026-06-03) — `config/notion_ids.json` written verbatim from the spec.
  Real Notion sync is gated on `NOTION_TOKEN`; until set, all stages use fixtures.

## Step 2 — Dependencies
- [2] ASSUMPTION (2026-06-03) — The advisory pins (mesa 2.3.4, networkx 3.2.1,
  scipy 1.11.4, numpy 1.26.4, pandas 2.1.4, notion-client 2.2.1) have no wheels for
  Python 3.13.1 (this machine). `scipy==1.11.4` tried to build from source and failed
  (`meson`/`cython`: "Compiler cython cannot compile programs"). Per the directive we
  did NOT retry the failing pin; we fell back to the latest compatible releases.
- [2] INFO (2026-06-03) — Resolved & import-smoke-tested OK: numpy 2.4.6, pandas
  3.0.3, scipy 1.17.1, networkx 3.6.1, mesa 3.5.1, notion-client 3.1.0.
- [2] INFO (2026-06-03) — **Mesa MAJOR version detected at runtime = 3.** All model
  code is written against the 3.x API (`model.agents`/`AgentSet`, no `mesa.time`) with
  a compatibility shim (`sim/mesa_compat.py`) that also supports 2.x schedulers.
- [2] INFO (2026-06-03) — `requirements.txt` now uses version floors (not exact pins)
  so CI / other Python versions resolve to whatever wheels exist there.

## Steps 5-6 — Macro model & calibration
- [5] INFO (2026-06-03) — Macro dynamics use a bistable complex-contagion CAPACITY
  model: conversion relaxes toward a per-region, per-time capacity K(drive) (Hill
  function) where drive = internal prevalence (self-sustain, gated by external support)
  + additive Christian-neighbor contact + strand push. This reproduces the historical
  pattern — the faith locks in where it becomes the mutually-reinforcing social fabric
  (Europe/Americas) and stays a minority where isolated — with NO per-region constants.
  A durable "rival incumbency" term (from SUPPRESSION strands + persecution events)
  captures Islam de-Christianizing MENA and Soviet atheism dipping Eastern Europe.
- [6] ASSUMPTION/LIMITATION (2026-06-03) — A symmetric 8-GLOBAL-parameter model cannot
  separate two cases the input data labels identically: settler-colonial
  Christianization (Latin America, North America — Christian populations transplanted,
  reach ~90%) vs mission-field contact among entrenched non-Christian incumbencies
  (East/South/Southeast Asia — Hinduism/Buddhism/Confucianism/Islam, stay <10%). The
  calibrated model therefore OVERESTIMATES modern East/South Asia Christian share
  (~30-55% vs anchored ~4-8%). Documented, not hidden — residuals are in
  reports/calibration_report.md. Phase-2 fix: per-region incumbency priors and
  ABC-SMC calibration (both already on the deferred list).
- [6] INFO (2026-06-03) — Calibration: 1 run/eval (model is deterministic, so the
  spec's "average 3 seeded runs" is a no-op), multi-restart Nelder-Mead, wall-clock +
  maxfev hard stops. A single full macro run is ~25-30 ms, so the default 60-min budget
  affords far more than the ~50-eval threshold; we cap maxfev at 2000. Objective fell
  ~13.6 -> ~1.25; mean absolute anchor residual ≈ 11-12 percentage points.


## Step 10 — Deploy
- [10] BLOCKER→WORKAROUND (2026-06-03) — The available `gh` token (account
  Jnanayogi33) has scopes `gist, read:org, repo` but NOT `workflow`. GitHub therefore
  rejects any push that creates/updates files under `.github/workflows/`
  ("refusing to allow an OAuth App to create or update workflow ... without workflow
  scope"). I cannot re-auth interactively to add the scope. Workaround taken:
  (1) the correct Actions workflows are preserved in the repo under `deploy/` (build +
  Pages deploy with permissions contents:read/pages:write/id-token:write and
  configure-pages/upload-pages-artifact/deploy-pages) — move them to `.github/workflows/`
  once a `workflow`-scoped token is available; (2) for an actual LIVE URL now, the built
  static bundle is deployed directly to the `gh-pages` branch (a content push, no
  workflow scope needed) and Pages is served from that branch. The Vite base is
  `/tapestry/` to match the Pages subpath. Live URL recorded in README.

## Step 9 — Notion sync
- [9] INFO (2026-06-03) — NOTION_TOKEN unset; falling back to synthetic fixtures (expected until the integration token is set and the root page is shared). Existing data/*.csv (fixtures or last-good) are kept as-is.

<!-- VALIDATION:START -->

## Validation (latest run, auto-managed)
- HARD FAILS: 0 | WARNINGS: 0
- (no warnings)

<!-- VALIDATION:END -->

- [9] INFO (2026-06-03) — NOTION_TOKEN unset; falling back to synthetic fixtures (expected until the integration token is set and the root page is shared). Existing data/*.csv (fixtures or last-good) are kept as-is.
