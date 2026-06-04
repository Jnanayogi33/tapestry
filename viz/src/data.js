// Load all the derived data the visualization reads. Nothing is hardcoded — every
// thread, label and event comes from these files (copied into public/data by the
// copy-data script). Multi-select CSV cells are JSON-array strings (json.loads-style).
import Papa from "papaparse";

const BASE = import.meta.env.BASE_URL || "/";

async function fetchText(name) {
  const res = await fetch(`${BASE}data/${name}`);
  if (!res.ok) throw new Error(`failed to load ${name}: ${res.status}`);
  return res.text();
}

async function fetchJSON(name) {
  return JSON.parse(await fetchText(name));
}

function parseCSV(text) {
  return Papa.parse(text.trim(), { header: true, skipEmptyLines: true }).data;
}

function parseMultiselect(cell) {
  if (cell == null || cell === "") return [];
  try {
    const v = JSON.parse(cell);
    return Array.isArray(v) ? v.map(String) : [String(v)];
  } catch {
    return String(cell).split(",").map((s) => s.trim()).filter(Boolean);
  }
}

const num = (v) => (v === "" || v == null ? null : Number(v));

export async function loadAll() {
  const [sim, lives, strandsCsv, eventsCsv] = await Promise.all([
    fetchJSON("simulation_output.json"),
    fetchJSON("example_lives.json").catch(() => null),
    fetchText("strands.csv").catch(() => ""),
    fetchText("events.csv").catch(() => ""),
  ]);

  const strands = parseCSV(strandsCsv).map((r) => ({
    name: r.name,
    birth_year: num(r.birth_year),
    death_year: num(r.death_year),
    primary_region: parseMultiselect(r.primary_region),
    role: r.role,
    mechanism_template: r.mechanism_template,
    regions_affected: parseMultiselect(r.regions_affected),
    effect_window_start: num(r.effect_window_start),
    effect_window_end: num(r.effect_window_end),
    strength: num(r.strength) || 1,
    depth_tier: r.depth_tier || "Tier 3",
    confidence: r.confidence,
    sources: r.sources,
  })).filter((s) => s.name);

  const events = parseCSV(eventsCsv).map((r) => ({
    name: r["Event Name"],
    year_text: r.year,
    year_sort: num(r.year_sort),
    regions: parseMultiselect(r.regions),
    description: r.description,
    effect: r.effect,
    mechanism: r.mechanism,
  })).filter((e) => e.name && e.year_sort != null);

  return { sim, lives, strands, events };
}
