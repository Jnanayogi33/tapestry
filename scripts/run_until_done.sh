#!/usr/bin/env bash
# Tapestry v2 — run-until-done supervisor.
# Re-launches Claude Code headless in a loop; resumes via PROGRESS.md after every step;
# on a usage-limit / non-zero exit it sleeps until the quota resets, then continues.
# Exits only when a file named DONE appears at the repo root.
#
# Usage:   ./scripts/run_until_done.sh
# Requires the `claude` CLI on PATH. Adjust the flags below to match your install.
# Override the wait with:   SLEEP_SECONDS=21600 ./scripts/run_until_done.sh

set -u
cd "$(dirname "$0")/.."

SLEEP_SECONDS="${SLEEP_SECONDS:-18600}"   # default ~5h10m; the rolling usage window is ~5h
RESUME='Resume the Tapestry v2 build. Read THE_TAPESTRY_v2_ENGINEERING_PROMPT.md and (if present) PROGRESS.md, then continue from the exact next action. Work through the ORDER OF WORK and the VISUAL ITERATION LOOP. Commit after every step and update PROGRESS.md. Create a file named DONE at the repo root ONLY when the site is deployed AND the visual loop has converged (>=12/14, no zeros).'

iter=0
while [ ! -f DONE ]; do
  iter=$((iter+1))
  echo "[run_until_done] === iteration $iter @ $(date) ==="

  # Continue the prior conversation from the 2nd run onward (first run starts fresh).
  if [ -f .tapestry_session ]; then CONT="--continue"; else CONT=""; touch .tapestry_session; fi

  OUT="$(mktemp)"
  # Headless (-p), autonomous. If your CLI differs, change just this line.
  claude $CONT -p "$RESUME" --dangerously-skip-permissions 2>&1 | tee "$OUT"

  [ -f DONE ] && break

  if grep -qiE 'usage limit|rate limit|reset[s]? (at|in)|quota|too many requests|overloaded' "$OUT"; then
    echo "[run_until_done] usage limit hit @ $(date). Sleeping ${SLEEP_SECONDS}s for quota reset..."
    sleep "$SLEEP_SECONDS"
  else
    echo "[run_until_done] ended without DONE and without a limit message; retrying in 120s..."
    sleep 120
  fi
  rm -f "$OUT"
done

echo "[run_until_done] DONE @ $(date)."
