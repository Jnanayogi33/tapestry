// Entry point: load the data, raise the tapestry, wire the controls, the info panel,
// the event tooltip and the micro view. Everything is read from data files — nothing
// about the history is hardcoded here.
import { loadAll } from "./data.js";
import { Tapestry } from "./tapestry.js";
import { MicroView } from "./micro.js";

const $ = (id) => document.getElementById(id);

async function boot() {
  const loading = $("loading");
  let data;
  try {
    data = await loadAll();
  } catch (err) {
    loading.textContent = "Could not load the data. Run the pipeline, then rebuild the viz.";
    console.error(err);
    return;
  }

  $("endyear").textContent = data.sim.years[data.sim.years.length - 1];

  const info = $("info");
  const tip = makeTooltip();

  const tap = new Tapestry(data, {
    onStrand: (st) => showStrand(info, st),
    onEvent: (ev, screen) => {
      if (!ev) { tip.hide(); return; }
      tip.show(`<b>${ev.name}</b> · ${ev.year_text}<br>${ev.description}`, screen);
    },
  });
  await tap.init($("stage"));
  window.__tap = tap;            // debug/testing hook
  window.__data = data;

  // --- time controls ---
  const slider = $("timeline");
  const yearlabel = $("yearlabel");
  const y0 = data.sim.years[0], y1 = data.sim.years[data.sim.years.length - 1];
  const toYear = (v) => Math.round(y0 + (v / 1000) * (y1 - y0));
  const toSlider = (yr) => Math.round(((yr - y0) / (y1 - y0)) * 1000);

  tap.onFront = (yr) => {
    yearlabel.textContent = yr <= 0 ? `${1 - yr} BC` : yr;
    slider.value = toSlider(yr);
  };
  slider.addEventListener("input", () => {
    tap.pause();
    $("play").textContent = "► Play";
    tap.setFront(toYear(Number(slider.value)));
  });

  $("play").addEventListener("click", () => {
    const playing = tap.togglePlay();
    $("play").textContent = playing ? "❚❚ Pause" : "► Play";
  });
  $("reset").addEventListener("click", () => tap.resetView());

  // --- micro view ---
  let micro = null;
  $("toggle-micro").addEventListener("click", () => {
    const panel = $("micro");
    panel.classList.remove("hidden");
    if (!micro) micro = new MicroView(panel, data.lives);
  });
  $("micro-close").addEventListener("click", () => $("micro").classList.add("hidden"));

  // keyboard: space toggles play
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); $("play").click(); }
    if (e.key === "Escape") { info.classList.add("hidden"); $("micro").classList.add("hidden"); }
  });

  loading.style.opacity = "0";
  setTimeout(() => loading.classList.add("hidden"), 700);
}

function showStrand(info, st) {
  const dates = fmtDates(st.birth_year, st.death_year);
  const regions = (st.regions_affected || []).join(", ");
  info.innerHTML = `
    <span class="close">✕</span>
    <h3>${st.name}</h3>
    <div class="role">${st.role || ""}</div>
    <div class="meta-row">${dates}${st.depth_tier ? " · " + st.depth_tier : ""}${st.confidence ? " · " + st.confidence : ""}</div>
    <div style="margin:8px 0"><span class="tag">${st.mechanism_template}</span><span class="tag">strength ${st.strength}</span></div>
    <div class="meta-row"><b>reaches:</b> ${regions || "—"}</div>
    ${st.effect_window_start != null ? `<div class="meta-row"><b>bends the curve:</b> ${fmtYear(st.effect_window_start)}–${fmtYear(st.effect_window_end)}</div>` : ""}
  `;
  info.classList.remove("hidden");
  info.querySelector(".close").onclick = () => info.classList.add("hidden");
}

function fmtYear(y) {
  if (y == null) return "?";
  return y < 0 ? `${-y} BC` : `AD ${y}`;
}
function fmtDates(b, d) {
  if (b == null && d == null) return "dates uncertain";
  return `${b == null ? "?" : fmtYear(b)} – ${d == null ? "?" : fmtYear(d)}`;
}

function makeTooltip() {
  const el = document.createElement("div");
  el.style.cssText =
    "position:absolute;pointer-events:none;z-index:30;max-width:280px;padding:8px 12px;" +
    "background:rgba(12,14,24,0.95);border:1px solid rgba(255,206,107,0.3);border-radius:8px;" +
    "color:#e8e4d6;font:13px Georgia,serif;line-height:1.4;display:none;box-shadow:0 6px 24px rgba(0,0,0,.6)";
  document.getElementById("app").appendChild(el);
  return {
    show(html, screen) {
      el.innerHTML = html;
      el.style.left = Math.min(window.innerWidth - 290, screen.x + 12) + "px";
      el.style.top = (screen.y - 10) + "px";
      el.style.display = "block";
    },
    hide() { el.style.display = "none"; },
  };
}

boot();
