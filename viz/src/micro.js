// Micro view (first-class): open one example life and watch it move through belief
// states over time, annotated with what drove each change. Reads example_lives.json —
// a real dump from the micro simulation. Rendered as DOM for crisp text + interaction.

const STATE_COLOR = {
  Unexposed: "#555c70",
  Affiliated: "#b88a3a",
  Practicing: "#ffce6b",
  Lapsed: "#5b6c99",
  Unaffiliated: "#2e3a57",
};

export class MicroView {
  constructor(root, lives) {
    this.root = root;
    this.data = lives;            // full example_lives.json
    this.selectEl = document.getElementById("micro-select");
    this.body = document.getElementById("micro-body");
    if (!this.data || !this.data.lives || !this.data.lives.length) {
      this.body.innerHTML = '<p class="micro-note">No example lives available. Run the micro simulation first.</p>';
      return;
    }
    this._populate();
    this.selectEl.onchange = () => this.render(this.selectEl.value);
    this.render(this.selectEl.value);
  }

  _populate() {
    const lives = [...this.data.lives].sort((a, b) => (b.is_target_arc - a.is_target_arc));
    this.selectEl.innerHTML = "";
    for (const l of lives) {
      const opt = document.createElement("option");
      opt.value = l.id;
      const tag = l.is_target_arc ? "★ Lyudmila arc — " : "";
      const start = l.trajectory[0]?.state;
      const end = l.trajectory[l.trajectory.length - 1]?.state;
      opt.textContent = `${tag}${l.id} (${start} → ${end})`;
      this.selectEl.appendChild(opt);
    }
  }

  render(id) {
    const life = this.data.lives.find((l) => l.id === id) || this.data.lives[0];
    const traj = life.trajectory;
    const years = traj.map((p) => p.year);
    const y0 = years[0], y1 = years[years.length - 1];
    const span = Math.max(1, y1 - y0);
    const xOf = (yr) => ((yr - y0) / span) * 100;

    // contiguous state segments
    const segs = [];
    for (let i = 0; i < traj.length; i++) {
      const s = traj[i].state;
      if (!segs.length || segs[segs.length - 1].state !== s) {
        segs.push({ state: s, from: traj[i].year, to: traj[i].year });
      } else {
        segs[segs.length - 1].to = traj[i].year;
      }
    }
    const segHTML = segs.map((sg) => {
      const left = xOf(sg.from);
      const w = Math.max(0.5, xOf(sg.to + 1) - left);
      return `<div class="life-seg" title="${sg.state}: ${sg.from}–${sg.to}" style="left:${left}%;width:${w}%;background:${STATE_COLOR[sg.state] || "#888"}"></div>`;
    }).join("");

    // axis ticks
    const tickYears = [];
    for (let yr = Math.ceil(y0 / 20) * 20; yr <= y1; yr += 20) tickYears.push(yr);
    const axisHTML = tickYears.map((yr) => `<span style="left:${xOf(yr)}%">${yr}</span>`).join("");

    // driver annotations: list each state change with its driver
    const changes = [];
    for (let i = 1; i < traj.length; i++) {
      if (traj[i].state !== traj[i - 1].state) {
        changes.push(`<div>${traj[i].year} — became <b>${traj[i].state}</b>${traj[i].driver ? ` <span style="opacity:.75">(${traj[i].driver})</span>` : ""}</div>`);
      }
    }

    const legend = Object.entries(STATE_COLOR)
      .map(([s, c]) => `<i style="background:${c}"></i>${s}`).join("");

    // society context (secular pressure + revival) as a faint overlay band
    const soc = this.data.society;
    let socHTML = "";
    if (soc && soc.years && soc.years.length) {
      const sx = (yr) => ((yr - y0) / span) * 100;
      const sp = soc.years.map((yr, i) => `${sx(yr)},${30 - soc.secular_pressure[i] * 28}`).join(" ");
      const rv = soc.years.map((yr, i) => `${sx(yr)},${30 - soc.revival[i] * 28}`).join(" ");
      socHTML = `
        <div class="micro-note">society around this life — <span style="color:#7f88c0">secular pressure</span>, <span style="color:#ff9d5c">revival</span></div>
        <svg viewBox="0 0 100 32" preserveAspectRatio="none" style="width:100%;height:44px;background:#0a0c16;border-radius:6px">
          <polyline points="${sp}" fill="none" stroke="#7f88c0" stroke-width="0.6" vector-effect="non-scaling-stroke"/>
          <polyline points="${rv}" fill="none" stroke="#ff9d5c" stroke-width="0.6" vector-effect="non-scaling-stroke"/>
        </svg>`;
    }

    const flag = life.is_target_arc
      ? '<span style="color:#ffce6b">★ the target arc — affiliated → unbelieving → strongly-practicing, returning through believing ties</span>'
      : (this.data.meta && !this.data.meta.target_arc_found
          ? '<span class="micro-note">closest trajectory found; the exact target arc did not emerge naturally this run</span>' : "");

    this.body.innerHTML = `
      <p class="micro-summary">${life.summary || ""}</p>
      <div class="life-label">disposition ${life.disposition} · ${life.network_degree} social ties · ${life.region} · ${flag}</div>
      <div class="state-legend">${legend}</div>
      <div class="life-track">${segHTML}</div>
      <div class="life-axis">${axisHTML}</div>
      ${socHTML}
      <div class="life-drivers"><div class="life-label">what drove each turn</div>${changes.join("") || "<div>(steady throughout)</div>"}</div>
    `;
  }
}
