// The Tapestry v2 — a deep-zoom viewer over the BAKED image of a real agent-based
// contagion. The image is pure light; all chrome lives in panels. Navigation flies the
// camera to a coordinate from data/nav_index.json; the timeline scrubs the era frames
// (the animated reveal); a single life can be traced from data/example_lives.json.
// Nothing about the history is hardcoded here — it is all read from the baked outputs.
import OpenSeadragon from "openseadragon";
import "./style.css";

const BASE = import.meta.env.BASE_URL || "/";
const $ = (s) => document.querySelector(s);

async function loadJSON(path) {
  const r = await fetch(BASE + path, { cache: "no-cache" });
  if (!r.ok) throw new Error(`fetch ${path}: ${r.status}`);
  return r.json();
}

const STATE_SHADE = {
  Practicing: "#ffd98a", Affiliated: "#c79a55", Nominal: "#c79a55", Lapsed: "#8f7340",
  Unexposed: "#3a342a", Unaffiliated: "#3a342a", Martyred: "#fff1cf",
};

let viewer, manifest, nav, lives, aspect = 0.5;
let sources = [];        // [{year, url, idx}]
let curIdx = 0;
let playing = false, playRAF = 0;
let activeLife = null;

async function main() {
  manifest = await loadJSON("tapestry/manifest.json");
  aspect = manifest.height / manifest.width;
  nav = await loadJSON("data/nav_index.json").catch(() => ({}));
  lives = await loadJSON("data/example_lives.json").catch(() => ({ lives: [] }));

  // sources: era frames for the reveal, then the full-res climax as the final (2025).
  const frames = manifest.frames || [];
  const years = manifest.era_years || [];
  sources = frames.map((url, i) => ({ year: years[i], url }));
  // use the high-res climax for the final (full-reveal) position
  if (sources.length) sources[sources.length - 1] = { year: years[years.length - 1] || 2025, url: manifest.climax };
  else sources = [{ year: 2025, url: manifest.climax }];

  buildViewer();
  buildTimeline();
  buildNav();
  wireChrome();
}

function buildViewer() {
  viewer = OpenSeadragon({
    id: "osd",
    prefixUrl: "",
    showNavigationControl: false,
    background: "#07080d",
    animationTime: 0.9,
    springStiffness: 7,
    maxZoomPixelRatio: 2.2,
    minZoomImageRatio: 0.9,
    visibilityRatio: 1,
    constrainDuringPan: true,
    gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true },
  });

  // Stack every era frame as a tiled image at the same place; show one at a time.
  let pending = sources.length;
  sources.forEach((s, i) => {
    viewer.addTiledImage({
      tileSource: { type: "image", url: BASE + s.url },
      opacity: i === sources.length - 1 ? 1 : 0,
      index: i,
      success: () => { if (--pending === 0) onReady(); },
      error: () => { if (--pending === 0) onReady(); },
    });
  });
  curIdx = sources.length - 1;

  // life-trace overlay redraws with the viewport
  const redraw = () => drawLifeOverlay();
  viewer.addHandler("update-viewport", redraw);
  viewer.addHandler("animation", redraw);
  viewer.addHandler("resize", redraw);
}

function onReady() {
  $("#loading").classList.add("gone");
  setTimeout(() => $("#loading").remove(), 700);
}

function showFrame(i) {
  i = Math.max(0, Math.min(sources.length - 1, i));
  const n = viewer.world.getItemCount();
  for (let k = 0; k < n && k < sources.length; k++) {
    const item = viewer.world.getItemAt(k);
    if (item) item.setOpacity(k === i ? 1 : 0);
  }
  curIdx = i;
  $("#yearlabel").textContent = (sources[i].year >= 0 ? "AD " : "") + sources[i].year;
  $("#timeline").value = String(i);
}

// ---- timeline / play ----
function buildTimeline() {
  const tl = $("#timeline");
  tl.max = String(sources.length - 1);
  tl.value = String(sources.length - 1);
  tl.addEventListener("input", () => { stopPlay(); showFrame(+tl.value); });
  $("#play").addEventListener("click", togglePlay);
  $("#reset").addEventListener("click", () => {
    clearLife(); viewer.viewport.goHome();
  });
  showFrame(sources.length - 1);
}

function togglePlay() {
  if (playing) return stopPlay();
  playing = true; $("#play").textContent = "❚❚ Pause";
  if (curIdx >= sources.length - 1) showFrame(0);
  let last = performance.now(), acc = 0;
  const tick = (now) => {
    if (!playing) return;
    acc += now - last; last = now;
    if (acc > 900) { acc = 0;
      if (curIdx >= sources.length - 1) { stopPlay(); return; }
      showFrame(curIdx + 1);
    }
    playRAF = requestAnimationFrame(tick);
  };
  playRAF = requestAnimationFrame(tick);
}
function stopPlay() { playing = false; cancelAnimationFrame(playRAF); $("#play").textContent = "► Play"; }

// ---- camera fly ----
function flyTo(x, y, zoom) {
  const pt = new OpenSeadragon.Point(x, y * aspect);
  viewer.viewport.panTo(pt, false);
  if (zoom) viewer.viewport.zoomTo(zoom, pt, false);
  viewer.viewport.applyConstraints();
}

// ---- navigation menu ----
function buildNav() {
  const groups = [];
  const strands = (nav.strands || []).slice().sort((a, b) =>
    (a.depth_tier || "").localeCompare(b.depth_tier || "") || (b.strength || 0) - (a.strength || 0));
  groups.push(["People (strands)", strands.map((s) => ({
    label: s.name, meta: `${fmtYear(s.birth_year)}–${fmtYear(s.death_year)}`,
    x: s.x, y: s.y, zoom: s.zoom, kind: "strand", data: s,
  }))]);
  groups.push(["Events", (nav.events || []).map((e) => ({
    label: e.name, meta: e.year, x: e.x, y: e.y, zoom: e.zoom, kind: "event", data: e,
  }))]);
  groups.push(["Places", (nav.places || []).map((p) => ({
    label: p.name, meta: p.branch, x: p.x, y: p.y, zoom: p.zoom, kind: "place", data: p,
  }))]);
  groups.push(["Lives (trace one)", (lives.lives || []).map((l) => ({
    label: lifeName(l) + (l.is_target_arc ? " ★" : ""), meta: l.region, kind: "life", data: l,
  }))]);
  if (nav.seed) groups.unshift(["The Seed", [{ label: nav.seed.name, meta: "AD 30",
    x: nav.seed.x, y: nav.seed.y, zoom: nav.seed.zoom, kind: "seed", data: nav.seed }]]);

  const render = (q) => {
    const box = $("#nav-results"); box.innerHTML = "";
    const ql = q.trim().toLowerCase();
    for (const [title, items] of groups) {
      const matched = ql ? items.filter((it) => it.label.toLowerCase().includes(ql) ||
        (it.meta || "").toString().toLowerCase().includes(ql)) : items.slice(0, 24);
      if (!matched.length) continue;
      const h = document.createElement("div"); h.className = "nav-group"; h.textContent = title;
      box.appendChild(h);
      for (const it of matched) {
        const b = document.createElement("button"); b.className = "nav-item";
        b.innerHTML = `<span>${it.label}</span><span class="meta">${it.meta || ""}</span>`;
        b.addEventListener("click", () => selectItem(it));
        box.appendChild(b);
      }
    }
  };
  $("#nav-search").addEventListener("input", (e) => render(e.target.value));
  render("");
}

function selectItem(it) {
  clearLife();
  if (it.kind === "life") { traceLife(it.data); return; }
  showFrame(sources.length - 1);                 // full reveal so the target is visible
  flyTo(it.x, it.y, it.zoom);
  showPanel(it);
  if (window.matchMedia("(max-width: 620px)").matches) $("#nav-drawer").classList.add("hidden");
}

// ---- info panel ----
function showPanel(it) {
  const p = $("#panel"); p.classList.remove("hidden");
  const d = it.data || {};
  let html = `<button class="close" data-close="panel">×</button>`;
  if (it.kind === "strand") {
    html += `<h3>${d.name}</h3><div class="sub">${d.role || ""}</div>`;
    html += `<p>${fmtYear(d.birth_year)} – ${fmtYear(d.death_year)} · ${d.place || ""}</p>`;
    html += `<p>${tag(d.mechanism_template)} ${tag(d.depth_tier)} strength ${d.strength}/5 · ${tag(d.confidence)}</p>`;
    const ra = (d.regions_affected || []).join(", ");
    if (ra) html += `<p><b>Reaches:</b> ${ra}</p>`;
  } else if (it.kind === "event") {
    html += `<h3>${d.name}</h3><div class="sub">${d.year} · ${tag(d.effect)} ${tag(d.mechanism)}</div>`;
    html += `<p>${d.description || ""}</p>`;
    if ((d.regions || []).length) html += `<p><b>Where:</b> ${d.regions.join(", ")}</p>`;
  } else if (it.kind === "place") {
    html += `<h3>${d.name}</h3><div class="sub">${d.parent_macro_region} · ${d.branch}</div>`;
    html += `<p>${d.era_note ? "<b>" + d.era_note + "</b> · " : ""}${d.notes || ""}</p>`;
    html += `<p class="arc">distance from Judaea: ${Math.round(d.distance_norm)}/100</p>`;
  } else if (it.kind === "seed") {
    html += `<h3>${d.name}</h3><div class="sub">AD 30 · Judaea</div><p>${d.description || ""}</p>`;
  }
  p.innerHTML = html;
}

// ---- single-life trace ----
function traceLife(life) {
  activeLife = life;
  // fit camera to the life's path
  const pts = life.path || [];
  if (pts.length) {
    const xs = pts.map((q) => q.x), ys = pts.map((q) => q.y * aspect);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    showFrame(sources.length - 1);
    viewer.viewport.panTo(new OpenSeadragon.Point(cx, cy), false);
    viewer.viewport.zoomTo(Math.min(7, 0.7 / Math.max(0.02, x1 - x0)), new OpenSeadragon.Point(cx, cy), false);
    viewer.viewport.applyConstraints();
  }
  // panel describing the life + arc
  const p = $("#panel"); p.classList.remove("hidden");
  const arc = (life.trajectory || []).reduce((acc, t) => {
    const last = acc[acc.length - 1];
    if (!last || last.state !== t.state) acc.push({ ...t });
    return acc;
  }, []);
  const arcStr = arc.map((t) => `<b>${t.year}</b> ${t.state}${t.driver ? ` <i>(${t.driver})</i>` : ""}`).join(" → ");
  p.innerHTML = `<button class="close" data-close="panel">×</button>
    <h3>${lifeName(life)}${life.is_target_arc ? " ★" : ""}</h3>
    <div class="sub">a sampled life · ${life.region}${life.place ? " · " + life.place : ""}</div>
    <p>${life.summary || ""}</p>
    <p class="arc">${arcStr}</p>
    <div class="actions"><button data-clearlife>← back to the whole</button></div>`;
  drawLifeOverlay();
}

function drawLifeOverlay() {
  const cv = $("#life-overlay");
  const r = viewer.viewport.getContainerSize();
  if (cv.width !== r.x) cv.width = r.x;
  if (cv.height !== r.y) cv.height = r.y;
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, cv.width, cv.height);
  if (!activeLife || !(activeLife.path || []).length) return;
  const pts = activeLife.path;
  const px = pts.map((q) => {
    const e = viewer.viewport.pixelFromPoint(new OpenSeadragon.Point(q.x, q.y * aspect), true);
    return { x: e.x, y: e.y, shade: q.shade, state: q.state, driver: q.driver, year: q.year };
  });
  // soft glow line
  ctx.lineWidth = 3; ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.shadowColor = "#ffce7a"; ctx.shadowBlur = 14;
  for (let i = 1; i < px.length; i++) {
    ctx.beginPath();
    ctx.strokeStyle = STATE_SHADE[px[i].state] || "#c79a55";
    ctx.moveTo(px[i - 1].x, px[i - 1].y); ctx.lineTo(px[i].x, px[i].y); ctx.stroke();
  }
  ctx.shadowBlur = 0;
  // mark state transitions with a dot + label
  let prev = null;
  px.forEach((q) => {
    if (prev && prev.state === q.state) return;
    prev = q;
    ctx.fillStyle = STATE_SHADE[q.state] || "#c79a55";
    ctx.beginPath(); ctx.arc(q.x, q.y, 4, 0, 7); ctx.fill();
    ctx.fillStyle = "rgba(232,226,212,0.92)"; ctx.font = "12px Georgia";
    const lbl = `${q.year} ${q.state}${q.driver ? " · " + q.driver : ""}`;
    ctx.fillText(lbl, q.x + 8, q.y - 8);
  });
}

function clearLife() { activeLife = null; drawLifeOverlay(); }

// ---- chrome wiring ----
function wireChrome() {
  $("#nav-toggle").addEventListener("click", () => $("#nav-drawer").classList.toggle("hidden"));
  $("#about-toggle").addEventListener("click", () => $("#about").classList.toggle("hidden"));
  document.addEventListener("click", (e) => {
    const c = e.target.getAttribute && e.target.getAttribute("data-close");
    if (c) $("#" + c).classList.add("hidden");
    if (e.target.hasAttribute && e.target.hasAttribute("data-clearlife")) {
      clearLife(); $("#panel").classList.add("hidden"); viewer.viewport.goHome();
    }
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { $("#panel").classList.add("hidden"); $("#about").classList.add("hidden"); clearLife(); }
    if (e.key === " ") { e.preventDefault(); togglePlay(); }
  });
}

// ---- helpers ----
function tag(v) { return v ? `<span class="tag">${v}</span>` : ""; }
function lifeName(l) {
  if (l.matched_profile) {
    const s = l.matched_profile.replace(/^life_/, "");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
  return "Life " + String(l.id || "").replace("agent_", "");
}
function fmtYear(y) {
  if (y === null || y === undefined || y === "") return "?";
  y = Math.round(+y);
  return y < 0 ? `${-y} BC` : `AD ${y}`;
}

main().catch((e) => {
  console.error(e);
  const l = $("#loading"); if (l) l.textContent = "could not load the tapestry — see console";
});
