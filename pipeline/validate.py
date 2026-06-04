"""Validate the data snapshots (fixtures OR real Notion pulls).

Wired into GitHub Actions on every push. Exit code is non-zero ONLY on HARD FAILS;
WARNINGS are logged (to BLOCKERS.md and reports/validation_report.md) but never fail
the build, because the data is intentionally sparse/soft in places.

HARD FAILS:
  * any anchor row where NOT (christians_low <= christians_central <= christians_high)
  * a MISSING GLOBAL row for any of the 14 anchor years (named loudly)
  * any required field null (except practicing_pct; and birth_year/death_year on strands)
  * any strand mechanism_template outside the 8
  * any region / effect / mechanism / confidence outside its canonical enum

WARNINGS (never fail):
  * regional reconciliation: sum regional christians_central vs GLOBAL central. Only
    actually compared for years with >= 8/10 region coverage (in practice 1900 & 2025),
    tolerance ~15%. For 1970/2000 and every pre-1900 year, coverage is partial BY
    DESIGN (and pre-640 concentrates in Roman/Mediterranean to avoid double-counting),
    so we only note that the check was skipped.

Run: python pipeline/validate.py [--data-dir data]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import schema as S  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RECONCILE_TOLERANCE = 0.15  # ~15%
REGIONS_SET = set(S.REGIONS_AND_GLOBAL)

# Required (non-null) fields per file. Explicitly-nullable / free-text-optional fields
# are excluded so real Notion data with blank notes/urls doesn't hard-fail.
REQUIRED = {
    "regions": ["Name"],
    "anchors": [
        "label", "region", "year",
        "christians_low", "christians_central", "christians_high",
        "total_population", "christians_pct_central", "confidence",
    ],
    "events": ["Event Name", "year_sort", "regions", "effect", "mechanism"],
    "strands": [
        "name", "primary_region", "role", "mechanism_template", "regions_affected",
        "effect_window_start", "effect_window_end", "strength", "depth_tier",
        "confidence",
    ],
}


class Report:
    def __init__(self) -> None:
        self.hard: list[str] = []
        self.warn: list[str] = []
        self.info: list[str] = []

    def fail(self, msg: str) -> None:
        self.hard.append(msg)

    def warning(self, msg: str) -> None:
        self.warn.append(msg)

    def note(self, msg: str) -> None:
        self.info.append(msg)


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_null(v) -> bool:
    return v is None or str(v).strip() == "" or str(v).strip().lower() == "nan"


def as_float(v):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError):
        return None


# ---- individual checks ------------------------------------------------------------
def check_required(rows: list[dict], name: str, rep: Report) -> None:
    for field in REQUIRED.get(name, []):
        for i, row in enumerate(rows):
            if field not in row or is_null(row.get(field)):
                rep.fail(f"[{name}] row {i+1}: required field '{field}' is null/missing")


def check_anchors(rows: list[dict], rep: Report) -> None:
    # low <= central <= high
    for i, row in enumerate(rows):
        lo, ce, hi = as_float(row.get("christians_low")), as_float(row.get("christians_central")), as_float(row.get("christians_high"))
        if None in (lo, ce, hi):
            continue  # nulls already caught by required-field check
        if not (lo <= ce <= hi):
            rep.fail(f"[anchors] row {i+1} ({row.get('label')}): violates low<=central<=high "
                     f"({lo} <= {ce} <= {hi})")
    # region enum
    for i, row in enumerate(rows):
        reg = row.get("region", "")
        if not is_null(reg) and reg not in REGIONS_SET:
            rep.fail(f"[anchors] row {i+1}: region '{reg}' not in canonical regions/GLOBAL")
    # confidence enum
    for i, row in enumerate(rows):
        conf = row.get("confidence", "")
        if not is_null(conf) and conf not in S.CONFIDENCE_ENUM:
            rep.fail(f"[anchors] row {i+1}: confidence '{conf}' not in {S.CONFIDENCE_ENUM}")
    # christians_pct_central must look like percentage points (0..100), warn otherwise
    for i, row in enumerate(rows):
        pct = as_float(row.get("christians_pct_central"))
        if pct is not None and (pct < 0 or pct > 100):
            rep.warning(f"[anchors] row {i+1} ({row.get('label')}): christians_pct_central "
                        f"={pct} outside 0..100 — percent should be percentage points")
    # MISSING GLOBAL row for any anchor year
    global_years = {int(as_float(r["year"])) for r in rows
                    if r.get("region") == S.GLOBAL and as_float(r.get("year")) is not None}
    for y in S.ANCHOR_YEARS:
        if y not in global_years:
            rep.fail(f"[anchors] MISSING GLOBAL row for anchor year {y}")


def check_events(rows: list[dict], rep: Report) -> None:
    for i, row in enumerate(rows):
        eff = row.get("effect", "")
        if not is_null(eff) and eff not in S.EFFECT_ENUM:
            rep.fail(f"[events] row {i+1}: effect '{eff}' not in {S.EFFECT_ENUM}")
        mech = row.get("mechanism", "")
        if not is_null(mech) and mech not in S.EVENT_MECHANISM_ENUM:
            rep.fail(f"[events] row {i+1}: mechanism '{mech}' not in {S.EVENT_MECHANISM_ENUM}")
        for r in S.load_multiselect(row.get("regions")):
            if r not in REGIONS_SET:
                rep.fail(f"[events] row {i+1}: region '{r}' not in canonical regions/GLOBAL")
        if as_float(row.get("year_sort")) is None and not is_null(row.get("year_sort")):
            rep.fail(f"[events] row {i+1}: year_sort '{row.get('year_sort')}' is not numeric")


def check_strands(rows: list[dict], rep: Report) -> None:
    for i, row in enumerate(rows):
        mt = row.get("mechanism_template", "")
        if not is_null(mt) and mt not in S.STRAND_MECHANISM_ENUM:
            rep.fail(f"[strands] row {i+1} ({row.get('name')}): mechanism_template '{mt}' "
                     f"not in the 8 {S.STRAND_MECHANISM_ENUM}")
        conf = row.get("confidence", "")
        if not is_null(conf) and conf not in S.CONFIDENCE_ENUM:
            rep.fail(f"[strands] row {i+1}: confidence '{conf}' not in {S.CONFIDENCE_ENUM}")
        tier = row.get("depth_tier", "")
        if not is_null(tier) and tier not in S.DEPTH_TIERS:
            rep.fail(f"[strands] row {i+1}: depth_tier '{tier}' not in {S.DEPTH_TIERS}")
        for col in ("primary_region", "regions_affected"):
            for r in S.load_multiselect(row.get(col)):
                if r not in REGIONS_SET:
                    rep.fail(f"[strands] row {i+1} ({row.get('name')}): {col} value '{r}' "
                             f"not in canonical regions/GLOBAL")
        # effect window sanity (warn, not fail).
        ws, we = as_float(row.get("effect_window_start")), as_float(row.get("effect_window_end"))
        if ws is not None and we is not None and ws > we:
            rep.warning(f"[strands] row {i+1} ({row.get('name')}): effect_window_start "
                        f"{ws} > effect_window_end {we}")
        strv = as_float(row.get("strength"))
        if strv is not None and not (1 <= strv <= 5):
            rep.warning(f"[strands] row {i+1} ({row.get('name')}): strength {strv} outside 1..5")


def check_reconciliation(anchors: list[dict], rep: Report) -> None:
    """Regional sum vs GLOBAL central — WARNING only, by design."""
    # GLOBAL central by year.
    global_central = {}
    for r in anchors:
        if r.get("region") == S.GLOBAL:
            y = as_float(r.get("year"))
            c = as_float(r.get("christians_central"))
            if y is not None and c is not None:
                global_central[int(y)] = c
    # Regional rows by year.
    regional_by_year: dict[int, dict[str, float]] = {}
    for r in anchors:
        reg = r.get("region")
        if reg in S.REGIONS:
            y = as_float(r.get("year"))
            c = as_float(r.get("christians_central"))
            if y is not None and c is not None:
                regional_by_year.setdefault(int(y), {})[reg] = c

    rep.note("Reconciliation rule: regional christians_central is summed and compared "
             "to the GLOBAL central ONLY for anchor years with >= 8/10 regions present "
             f"(tolerance ±{int(RECONCILE_TOLERANCE*100)}%). Other years are skipped by "
             "design (sparse coverage; pre-640 concentrated in Roman/Mediterranean to "
             "avoid double-counting). Reconciliation NEVER hard-fails.")

    for y in S.ANCHOR_YEARS:
        present = regional_by_year.get(y, {})
        n = len(present)
        if n >= 8:
            s = sum(present.values())
            g = global_central.get(y)
            if g:
                rel = abs(s - g) / g
                status = "OK" if rel <= RECONCILE_TOLERANCE else "OUT-OF-TOLERANCE"
                msg = (f"[reconcile] {y}: {n}/10 regions present; regional sum "
                       f"{s:,.0f} vs GLOBAL {g:,.0f} (Δ {rel*100:.1f}%) — {status}")
                if rel <= RECONCILE_TOLERANCE:
                    rep.note(msg)
                else:
                    rep.warning(msg)
        else:
            rep.note(f"[reconcile] {y}: {n}/10 regions present (<8) — comparison skipped by design")


# ---- output -----------------------------------------------------------------------
def render_report(rep: Report, data_dir: str) -> str:
    lines = ["# Validation report", "", f"_Data dir: `{data_dir}`_", ""]
    lines.append(f"- HARD FAILS: **{len(rep.hard)}**")
    lines.append(f"- WARNINGS: {len(rep.warn)}")
    lines.append("")
    if rep.hard:
        lines.append("## HARD FAILS")
        lines += [f"- {m}" for m in rep.hard]
        lines.append("")
    if rep.warn:
        lines.append("## WARNINGS (non-fatal, by design)")
        lines += [f"- {m}" for m in rep.warn]
        lines.append("")
    if rep.info:
        lines.append("## Notes")
        lines += [f"- {m}" for m in rep.info]
        lines.append("")
    return "\n".join(lines)


def update_blockers(rep: Report) -> None:
    """Rewrite a managed validation block in BLOCKERS.md (no unbounded growth)."""
    path = os.path.join(REPO_ROOT, "BLOCKERS.md")
    start, end = "<!-- VALIDATION:START -->", "<!-- VALIDATION:END -->"
    block_lines = [start, "", "## Validation (latest run, auto-managed)",
                   f"- HARD FAILS: {len(rep.hard)} | WARNINGS: {len(rep.warn)}"]
    for m in rep.warn:
        block_lines.append(f"- WARNING {m}")
    if not rep.warn:
        block_lines.append("- (no warnings)")
    block_lines += ["", end]
    block = "\n".join(block_lines)

    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    if start in existing and end in existing:
        pre = existing.split(start)[0].rstrip()
        post = existing.split(end)[1]
        new = f"{pre}\n\n{block}\n{post}"
    else:
        new = existing.rstrip() + "\n\n" + block + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(REPO_ROOT, "data"))
    args = ap.parse_args()
    data_dir = args.data_dir

    rep = Report()
    files = {n: read_csv(os.path.join(data_dir, f"{n}.csv"))
             for n in ("regions", "anchors", "events", "strands")}

    for name, rows in files.items():
        if not rows:
            rep.fail(f"[{name}] no rows found at {data_dir}/{name}.csv")
        else:
            check_required(rows, name, rep)

    if files["anchors"]:
        check_anchors(files["anchors"], rep)
        check_reconciliation(files["anchors"], rep)
    if files["events"]:
        check_events(files["events"], rep)
    if files["strands"]:
        check_strands(files["strands"], rep)

    report_md = render_report(rep, data_dir)
    os.makedirs(os.path.join(REPO_ROOT, "reports"), exist_ok=True)
    with open(os.path.join(REPO_ROOT, "reports", "validation_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
    update_blockers(rep)

    print(report_md)
    if rep.hard:
        print(f"\nVALIDATION FAILED with {len(rep.hard)} hard error(s).")
        return 1
    print(f"\nVALIDATION PASSED ({len(rep.warn)} warning(s), non-fatal).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
