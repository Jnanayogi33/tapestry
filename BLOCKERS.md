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

<!-- VALIDATION:START -->

## Validation (latest run, auto-managed)
- HARD FAILS: 0 | WARNINGS: 0
- (no warnings)

<!-- VALIDATION:END -->
