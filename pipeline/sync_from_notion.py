"""Pull the authoritative inputs from the Notion Knowledge Base into data/*.csv.

Reads NOTION_TOKEN from the environment and the database/page IDs from
config/notion_ids.json (BY ID, never by name). Pulls the four databases into
data/{regions,anchors,events,strands}.csv and best-effort-parses the Representative
Lives PAGE into data/lives.csv. Multi-selects are serialized as JSON-array strings so
Notion pulls and the synthetic fixtures are byte-for-byte interchangeable.

TWO FAILURE CASES are distinguished (per the sync contract):
  (a) config/notion_ids.json missing OR NOTION_TOKEN unset -> log to BLOCKERS.md and
      FALL BACK to fixtures (expected early on; quiet).
  (b) token + IDs present but a database returns ZERO rows -> do NOT silently fall
      back (that usually means the DB wasn't shared with the integration). Write a LOUD
      BLOCKERS.md entry naming the empty database, keep the last-good CSV, and continue.

Run: NOTION_TOKEN=secret_xxx python pipeline/sync_from_notion.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import schema as S  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CONFIG = os.path.join(REPO_ROOT, "config", "notion_ids.json")
BLOCKERS = os.path.join(REPO_ROOT, "BLOCKERS.md")


def log_blocker(level: str, msg: str) -> None:
    line = f"- [9] {level} ({date.today().isoformat()}) — {msg}\n"
    header = "\n## Step 9 — Notion sync\n"
    existing = ""
    if os.path.exists(BLOCKERS):
        with open(BLOCKERS, encoding="utf-8") as f:
            existing = f.read()
    if "## Step 9 — Notion sync" not in existing:
        # Insert before the managed validation block if present, else append.
        marker = "<!-- VALIDATION:START -->"
        if marker in existing:
            existing = existing.replace(marker, header + line + "\n" + marker)
        else:
            existing = existing.rstrip() + "\n" + header + line
    else:
        existing = existing.rstrip() + "\n" + line
    with open(BLOCKERS, "w", encoding="utf-8") as f:
        f.write(existing)
    print(f"[sync] {level}: {msg}")


# ---- Notion property extractors ---------------------------------------------------
def _plain(prop) -> str:
    if not prop:
        return ""
    t = prop.get("type")
    arr = prop.get(t) if t else None
    if isinstance(arr, list):
        return "".join(seg.get("plain_text", "") for seg in arr)
    return ""


def _title(prop) -> str:
    return _plain(prop)


def _number(prop):
    if not prop:
        return ""
    v = prop.get("number")
    return "" if v is None else v


def _select(prop) -> str:
    if not prop:
        return ""
    sel = prop.get("select")
    return sel.get("name", "") if sel else ""


def _multiselect(prop) -> str:
    if not prop:
        return S.dump_multiselect([])
    arr = prop.get("multi_select") or []
    return S.dump_multiselect([o.get("name", "") for o in arr])


def _url(prop) -> str:
    if not prop:
        return ""
    return prop.get("url") or ""


# ---- paginated query with data-source fallback ------------------------------------
def query_all(client, db_id: str, ds_id: str | None):
    """Query every page of a database. notion-client exposes databases.query; if the
    API reports the database has multiple/non-single data sources, retry against the
    matching data-source collection id from config (per the sync contract)."""
    def _paginate(query_fn, **base):
        rows, cursor = [], None
        while True:
            kwargs = dict(base)
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = query_fn(**kwargs)
            rows.extend(resp.get("results", []))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return rows

    try:
        return _paginate(client.databases.query, database_id=db_id)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if ds_id and ("data source" in msg or "data_source" in msg or "single" in msg):
            # Newer Notion API: query the data source directly.
            try:
                if hasattr(client, "data_sources"):
                    return _paginate(client.data_sources.query, data_source_id=ds_id)
                return _paginate(client.databases.query, database_id=ds_id)
            except Exception as exc2:  # noqa: BLE001
                raise RuntimeError(f"data-source fallback failed: {exc2}") from exc2
        raise


# ---- row mappers (Notion property name -> CSV column) -----------------------------
def map_region(props) -> dict:
    return {
        "Name": _title(props.get("Name")),
        "Modern Definition": _plain(props.get("Modern Definition")),
        "Boundary Notes": _plain(props.get("Boundary Notes")),
    }


def map_anchor(props) -> dict:
    return {
        "label": _title(props.get("label")),
        "region": _select(props.get("region")),
        "year": _number(props.get("year")),
        "christians_low": _number(props.get("christians_low")),
        "christians_central": _number(props.get("christians_central")),
        "christians_high": _number(props.get("christians_high")),
        "total_population": _number(props.get("total_population")),
        "christians_pct_central": _number(props.get("christians_pct_central")),
        "practicing_pct": _number(props.get("practicing_pct")),
        "source": _plain(props.get("source")),
        "source_url": _url(props.get("source_url")),
        "confidence": _select(props.get("confidence")),
        "notes": _plain(props.get("notes")),
    }


def map_event(props) -> dict:
    return {
        "Event Name": _title(props.get("Event Name")),
        "year": _plain(props.get("year")),
        "year_sort": _number(props.get("year_sort")),
        "regions": _multiselect(props.get("regions")),
        "description": _plain(props.get("description")),
        "effect": _select(props.get("effect")),
        "mechanism": _select(props.get("mechanism")),
        "source": _plain(props.get("source")),
        "source_url": _url(props.get("source_url")),
    }


def map_strand(props) -> dict:
    return {
        "name": _title(props.get("name")),
        "birth_year": _number(props.get("birth_year")),
        "death_year": _number(props.get("death_year")),
        "primary_region": _multiselect(props.get("primary_region")),
        "role": _plain(props.get("role")),
        "mechanism_template": _select(props.get("mechanism_template")),
        "regions_affected": _multiselect(props.get("regions_affected")),
        "effect_window_start": _number(props.get("effect_window_start")),
        "effect_window_end": _number(props.get("effect_window_end")),
        "strength": _number(props.get("strength")),
        "depth_tier": _select(props.get("depth_tier")),
        "confidence": _select(props.get("confidence")),
        "sources": _plain(props.get("sources")),
    }


DB_SPECS = {
    "regions": (S.REGIONS_COLUMNS, map_region),
    "anchors": (S.ANCHORS_COLUMNS, map_anchor),
    "events": (S.EVENTS_COLUMNS, map_event),
    "strands": (S.STRANDS_COLUMNS, map_strand),
}


def write_csv(name: str, columns: list[str], rows: list[dict]) -> None:
    path = os.path.join(DATA_DIR, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


# ---- Representative Lives PAGE -> data/lives.csv ----------------------------------
def parse_lives_page(client, page_id: str) -> list[dict]:
    """Best-effort parse of the narrative page's 8 profile blocks into columns.
    Headings start a profile; labelled lines (Era:, Region:, Disposition:, Trajectory:,
    Drivers:) fill fields; remaining paragraphs become the summary."""
    blocks, cursor = [], None
    while True:
        kw = {"block_id": page_id}
        if cursor:
            kw["start_cursor"] = cursor
        resp = client.blocks.children.list(**kw)
        blocks.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    profiles, cur = [], None
    FIELD = {"era": "era", "region": "region", "disposition": "start_disposition",
             "start disposition": "start_disposition", "trajectory": "trajectory",
             "drivers": "drivers"}

    def text_of(block) -> str:
        t = block.get("type")
        data = block.get(t, {})
        rt = data.get("rich_text", [])
        return "".join(s.get("plain_text", "") for s in rt).strip()

    for b in blocks:
        t = b.get("type", "")
        txt = text_of(b)
        if t.startswith("heading"):
            if cur:
                profiles.append(cur)
            cur = {"id": f"life_{len(profiles)+1}", "name": txt, "era": "", "region": "",
                   "start_disposition": "", "trajectory": "", "drivers": "", "summary": ""}
        elif cur is not None and txt:
            low = txt.lower()
            matched = False
            for label, col in FIELD.items():
                if low.startswith(label + ":") or low.startswith(label + " —") or low.startswith(label + " -"):
                    cur[col] = txt.split(":", 1)[-1].strip() if ":" in txt else txt
                    matched = True
                    break
            if not matched:
                cur["summary"] = (cur["summary"] + " " + txt).strip()
    if cur:
        profiles.append(cur)
    return profiles


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    token = os.environ.get("NOTION_TOKEN")

    # CASE (a): missing creds/config -> quiet fixture fallback.
    if not os.path.exists(CONFIG) or not token:
        why = "config/notion_ids.json missing" if not os.path.exists(CONFIG) else "NOTION_TOKEN unset"
        log_blocker("INFO", f"{why}; falling back to synthetic fixtures (expected until the "
                            "integration token is set and the root page is shared). "
                            "Existing data/*.csv (fixtures or last-good) are kept as-is.")
        if not os.path.exists(os.path.join(DATA_DIR, "anchors.csv")):
            from pipeline import make_fixtures
            make_fixtures.main()
            log_blocker("INFO", "no data/*.csv present; generated fixtures.")
        print("[sync] fixture fallback complete (no Notion pull).")
        return 0

    # Creds present -> pull from Notion.
    try:
        from notion_client import Client
    except Exception as exc:  # noqa: BLE001
        log_blocker("BLOCKER", f"notion-client not importable ({exc}); kept last-good data.")
        return 0

    with open(CONFIG, encoding="utf-8") as f:
        ids = json.load(f)
    client = Client(auth=token)
    data_sources = ids.get("data_sources", {})

    any_empty = False
    for name, (columns, mapper) in DB_SPECS.items():
        db_id = ids.get(name)
        ds_id = data_sources.get(name)
        try:
            pages = query_all(client, db_id, ds_id)
        except Exception as exc:  # noqa: BLE001
            log_blocker("BLOCKER", f"database '{name}' query failed ({exc}); kept last-good "
                                  f"data/{name}.csv.")
            any_empty = True
            continue
        # CASE (b): zero rows despite creds -> loud blocker, keep last-good.
        if not pages:
            log_blocker("BLOCKER", f"database '{name}' (id {db_id}) returned ZERO rows despite "
                                  "valid token+IDs — the database is almost certainly NOT shared "
                                  f"with the integration. Kept last-good data/{name}.csv; continuing.")
            any_empty = True
            continue
        rows = [mapper(p.get("properties", {})) for p in pages]
        write_csv(name, columns, rows)
        print(f"[sync] {name}: pulled {len(rows)} rows -> data/{name}.csv")

    # Representative Lives PAGE -> lives.csv (illustrative; never hard-fail).
    try:
        profiles = parse_lives_page(client, ids["lives_page"])
        if len(profiles) < 6:
            raise ValueError(f"only parsed {len(profiles)} profiles (< 6)")
        write_csv("lives", S.LIVES_COLUMNS, profiles)
        print(f"[sync] lives: parsed {len(profiles)} profiles -> data/lives.csv")
    except Exception as exc:  # noqa: BLE001
        log_blocker("WARNING", f"Representative Lives page parse fell short ({exc}); kept the "
                              "lives fixture (lives is illustrative seed material, not authoritative).")

    if any_empty:
        log_blocker("BLOCKER", "one or more databases were empty/failed — see entries above. "
                              "Build proceeds on last-good data.")
    print("[sync] Notion pull complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
