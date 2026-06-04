// The Tapestry — macro view. Luminous gold threads on a dark ground, beginning at a
// single point (Christ, AD 30) and ramifying across the regions over two thousand
// years; brightening as belief spreads, dimming and fraying where it declines or is
// suppressed. WebGL via PixiJS, additive blending for glow. NOT a filled streamgraph.
import { Application, Container, Graphics, Text, BlurFilter } from "pixi.js";

const W = 2400;          // logical world width
const H = 1350;          // logical world height
const X0 = 150;          // left margin (origin x)
const X1 = W - 70;       // right edge
const TOP = 120;
const BOT = H - 120;

const GOLD = 0xffce6b;
const GOLD_BRIGHT = 0xfff0c4;
const SEED_COL = 0xfff6da;
const MECH_COLOR = {
  SEED: 0xfff6da,
  APOSTOLIC_PROPAGATION: 0xffce6b,
  INSTITUTIONAL: 0xe9b34d,
  THEOLOGICAL: 0xc9d8ff,
  TRANSLATION: 0x9fe6c8,
  MARTYRDOM: 0xff6b6b,
  REVIVAL: 0xff9d5c,
  SUPPRESSION: 0x5b6cff,
};

// Region order: roughly the order each enters the story (origin first).
const REGION_ORDER = [
  "Roman/Mediterranean",
  "Western Europe",
  "Eastern Europe & Russia",
  "Middle East & North Africa",
  "Sub-Saharan Africa",
  "North America",
  "Latin America",
  "South Asia",
  "Southeast Asia",
  "East Asia",
];

export class Tapestry {
  constructor(data, opts = {}) {
    this.data = data;
    this.onStrand = opts.onStrand || (() => {});
    this.onEvent = opts.onEvent || (() => {});
    this.years = data.sim.years;
    this.y0 = this.years[0];
    this.y1 = this.years[this.years.length - 1];
    this.regions = REGION_ORDER.filter((r) => data.sim.regions[r]);
    this.playing = false;
    this.frontYear = this.y1;
  }

  async init(canvas) {
    const app = new Application();
    await app.init({
      canvas,
      background: 0x05060c,
      antialias: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      autoDensity: true,
      resizeTo: window,
      preference: "webgl",
    });
    this.app = app;

    this.world = new Container();
    app.stage.addChild(this.world);

    // Layers (back to front).
    this.backdrop = new Container();
    this.glow = new Container();      // additive + blurred glow copy of threads
    this.threads = new Container();   // crisp threads (additive)
    this.branches = new Container();
    this.nodes = new Container();
    this.labels = new Container();
    this.axis = new Container();
    this.eventsLayer = new Container();
    this.world.addChild(this.backdrop, this.glow, this.threads, this.branches,
                        this.eventsLayer, this.nodes, this.labels, this.axis);

    this.glow.blendMode = "add";
    this.threads.blendMode = "add";
    this.branches.blendMode = "add";
    this.glow.filters = [new BlurFilter({ strength: 14, quality: 3 })];
    this.glow.alpha = 0.55;

    // Reveal mask grows left->right as the time front sweeps.
    this.revealMask = new Graphics();
    this.world.addChild(this.revealMask);
    for (const layer of [this.glow, this.threads, this.branches, this.nodes, this.labels, this.eventsLayer]) {
      layer.mask = this.revealMask;
    }

    this._buildBackdrop();
    this._buildThreads();
    this._buildBranches();
    this._buildNodes();
    this._buildEvents();
    this._buildAxis();
    this._buildOrigin();

    this._initView();
    this._bindInteraction();

    app.ticker.add((t) => this._tick(t));
    this.setFront(this.y1);
    this.updateLabelVisibility();
    return this;
  }

  // -- coordinate mapping --------------------------------------------------------
  xOf(year) {
    const f = (year - this.y0) / (this.y1 - this.y0);
    return X0 + f * (X1 - X0);
  }
  bandHeight() { return (BOT - TOP) / this.regions.length; }
  yOf(region) {
    const i = this.regions.indexOf(region);
    return TOP + (i + 0.5) * this.bandHeight();
  }
  series(region) { return this.data.sim.regions[region].christian_pct; }
  pctAt(region, year) {
    const ys = this.years, s = this.series(region);
    if (year <= ys[0]) return s[0];
    if (year >= ys[ys.length - 1]) return s[s.length - 1];
    for (let i = 0; i < ys.length - 1; i++) {
      if (year >= ys[i] && year <= ys[i + 1]) {
        const t = (year - ys[i]) / (ys[i + 1] - ys[i]);
        return s[i] + t * (s[i + 1] - s[i]);
      }
    }
    return s[s.length - 1];
  }

  // -- backdrop: faint region envelopes + names ----------------------------------
  _buildBackdrop() {
    const bh = this.bandHeight();
    for (const r of this.regions) {
      const yc = this.yOf(r);
      const g = new Graphics();
      g.moveTo(X0, yc).lineTo(X1, yc).stroke({ width: 1, color: 0x223, alpha: 0.5 });
      // faint envelope
      g.rect(X0, yc - bh * 0.42, X1 - X0, bh * 0.84).fill({ color: 0x0c1020, alpha: 0.35 });
      this.backdrop.addChild(g);
      const label = new Text({
        text: r,
        style: { fill: 0x6a7390, fontSize: 17, fontFamily: "Georgia, serif", fontStyle: "italic" },
      });
      label.x = X0 + 6;
      label.y = yc - bh * 0.42 + 4;
      label.alpha = 0.7;
      this.backdrop.addChild(label);
    }
  }

  // -- the threads: per region, a ribbon of filaments modulated by Christian% ----
  _buildThreads() {
    const bh = this.bandHeight();
    const peak = 100;
    const N_FIL = 7;
    for (const r of this.regions) {
      const yc = this.yOf(r);
      const s = this.series(r);
      for (let f = 0; f < N_FIL; f++) {
        const phase = (f / N_FIL) * Math.PI * 2;
        const gThread = new Graphics();
        const gGlow = new Graphics();
        let started = false;
        for (let i = 0; i < this.years.length; i++) {
          const yr = this.years[i];
          const pct = s[i];
          const frac = Math.min(1, pct / peak);
          // filament vertical position: spreads with prevalence (lush when high).
          const spread = bh * 0.40 * (0.25 + 0.75 * frac);
          const wobble = Math.sin(phase + i * 0.18) * spread * ((f - (N_FIL - 1) / 2) / N_FIL) * 2;
          const x = this.xOf(yr);
          const y = yc + wobble;
          if (pct < 0.15) { started = false; continue; }   // thread absent below ~0.15%
          if (!started) { gThread.moveTo(x, y); gGlow.moveTo(x, y); started = true; }
          else { gThread.lineTo(x, y); gGlow.lineTo(x, y); }
          // brighten with prevalence; fade toward dim-orange where it has declined.
          const declining = i > 0 && s[i] < s[i - 1] - 0.5;
          const col = declining ? 0xffa24b : (frac > 0.55 ? GOLD_BRIGHT : GOLD);
          const a = 0.10 + 0.7 * Math.pow(frac, 0.7);
          const wdt = 0.6 + 2.4 * frac;
          gThread.stroke({ width: wdt, color: col, alpha: a, cap: "round", join: "round" });
          gThread.moveTo(x, y); gGlow.moveTo(x, y);
          gGlow.lineTo(x, y);
          gGlow.stroke({ width: wdt * 2.4, color: col, alpha: a * 0.5, cap: "round" });
          gGlow.moveTo(x, y);
        }
        this.threads.addChild(gThread);
        this.glow.addChild(gGlow);
      }
    }
  }

  // -- branches: the gospel reaching each region from the origin -----------------
  _buildBranches() {
    const origin = { x: this.xOf(this.y0) + 4, y: this.yOf(this.regions[0]) };
    for (const r of this.regions) {
      // ignition year: first year this region crosses ~1.5% (or earliest apostolic strand).
      const s = this.series(r);
      let ig = null;
      for (let i = 0; i < this.years.length; i++) {
        if (s[i] >= 1.5) { ig = this.years[i]; break; }
      }
      const apostolic = this.data.strands
        .filter((st) => st.mechanism_template === "APOSTOLIC_PROPAGATION" &&
          (st.regions_affected.includes(r) || st.regions_affected.includes("GLOBAL")))
        .map((st) => st.effect_window_start).filter((v) => v != null);
      if (apostolic.length) ig = Math.min(ig ?? Infinity, Math.min(...apostolic));
      if (ig == null) continue;
      const tx = this.xOf(ig), ty = this.yOf(r);
      const peakFrac = Math.min(1, Math.max(...s) / 100);
      const g = new Graphics();
      const midx = (origin.x + tx) / 2;
      const midy = (origin.y + ty) / 2 - Math.sign(ty - origin.y || 1) * 40 - 30;
      g.moveTo(origin.x, origin.y);
      g.bezierCurveTo(midx, origin.y, midx, midy, tx, ty);
      g.stroke({ width: 1 + 2.5 * peakFrac, color: GOLD, alpha: 0.18 + 0.4 * peakFrac, cap: "round" });
      this.branches.addChild(g);
    }
  }

  // -- the origin: Christ, the single seed at AD 30 ------------------------------
  _buildOrigin() {
    const x = this.xOf(this.y0) + 4, y = this.yOf(this.regions[0]);
    const g = new Graphics();
    g.circle(x, y, 4).fill({ color: SEED_COL, alpha: 1 });
    g.circle(x, y, 11).fill({ color: SEED_COL, alpha: 0.35 });
    g.circle(x, y, 22).fill({ color: SEED_COL, alpha: 0.12 });
    g.blendMode = "add";
    g.eventMode = "static";
    g.cursor = "pointer";
    const seed = this.data.strands.find((s) => s.mechanism_template === "SEED");
    if (seed) g.on("pointertap", () => this.onStrand(seed));
    this.nodes.addChild(g);
    this._originGlow = g;
    this._originXY = { x, y };

    const lbl = new Text({
      text: (seed && seed.name) || "Jesus of Nazareth",
      style: { fill: SEED_COL, fontSize: 15, fontFamily: "Georgia, serif", fontStyle: "italic" },
    });
    lbl.x = x + 14; lbl.y = y - 26;
    this.labels.addChild(lbl);
    this._originLabel = lbl;
  }

  // -- named strands as glowing, labelled nodes ----------------------------------
  _buildNodes() {
    this.strandNodes = [];
    for (const st of this.data.strands) {
      if (st.mechanism_template === "SEED") continue;       // origin already drawn
      const yr = st.effect_window_start ?? st.birth_year ?? st.death_year;
      if (yr == null) continue;
      const region = (st.primary_region && st.primary_region[0]) || this.regions[0];
      if (!this.regions.includes(region)) continue;
      const x = this.xOf(yr);
      const jitter = (st.name.length % 5 - 2) * 6;
      const y = this.yOf(region) + jitter;
      const col = MECH_COLOR[st.mechanism_template] || GOLD;
      const r = 1.8 + st.strength * 0.9;

      const g = new Graphics();
      g.circle(0, 0, r).fill({ color: col, alpha: 0.95 });
      g.circle(0, 0, r * 2.6).fill({ color: col, alpha: 0.22 });
      g.x = x; g.y = y;
      g.blendMode = "add";
      g.eventMode = "static";
      g.cursor = "pointer";
      g.on("pointertap", () => this.onStrand(st));
      g.on("pointerenter", () => { g.scale.set(1.5); });
      g.on("pointerleave", () => { g.scale.set(1.0); });
      this.nodes.addChild(g);

      const tierRank = { "Tier 1": 1, "Tier 2": 2, "Tier 3": 3 }[st.depth_tier] || 3;
      const label = new Text({
        text: st.name,
        style: { fill: 0xeae4d6, fontSize: 13, fontFamily: "Georgia, serif" },
      });
      label.x = x + r + 4; label.y = y - 8;
      label.alpha = 0.85;
      this.labels.addChild(label);
      this.strandNodes.push({ st, g, label, x, tierRank });
    }
  }

  // -- events as subtle timeline markers -----------------------------------------
  _buildEvents() {
    const yTick = BOT + 6;
    for (const ev of this.data.events) {
      const x = this.xOf(ev.year_sort);
      const g = new Graphics();
      const up = ev.effect && ev.effect.includes("+");
      const col = up ? GOLD : (ev.effect && ev.effect.includes("-") ? 0x7f88c0 : 0x556);
      g.moveTo(x, TOP - 8).lineTo(x, yTick).stroke({ width: 1, color: col, alpha: 0.12 });
      g.circle(x, yTick, 3.5).fill({ color: col, alpha: 0.8 });
      g.x = 0; g.y = 0;
      g.eventMode = "static";
      g.cursor = "help";
      g.hitArea = { contains: (px, py) => Math.abs(px - x) < 6 && py > TOP - 10 && py < yTick + 8 };
      g.on("pointerenter", () => this.onEvent(ev, this.toScreen(x, yTick)));
      g.on("pointerleave", () => this.onEvent(null));
      this.eventsLayer.addChild(g);
    }
  }

  _buildAxis() {
    const ticks = [30, 100, 300, 313, 500, 1000, 1054, 1500, 1517, 1800, 1900, 1970, 2000, 2025]
      .filter((y) => y >= this.y0 && y <= this.y1);
    for (const yr of ticks) {
      const x = this.xOf(yr);
      const t = new Text({
        text: yr === 30 ? "AD 30" : String(yr),
        style: { fill: 0x8089a8, fontSize: 13, fontFamily: "Georgia, serif" },
      });
      t.x = x - 14; t.y = BOT + 16;
      this.axis.addChild(t);
    }
  }

  // -- view: fit world to screen, then allow zoom/pan ----------------------------
  _initView() {
    this.resetView();
    // Refit after the renderer settles to the real window size, and on any resize
    // (a full refit is the expected behaviour when the window changes size).
    requestAnimationFrame(() => this.resetView());
    setTimeout(() => this.resetView(), 200);
    let rt;
    window.addEventListener("resize", () => {
      clearTimeout(rt);
      rt = setTimeout(() => this.resetView(), 120);
    });
  }
  resetView() {
    const sw = window.innerWidth;
    const sh = window.innerHeight;
    if (this.app.renderer.width !== sw * this.app.renderer.resolution) {
      this.app.renderer.resize(sw, sh);
    }
    const scale = Math.min(sw / W, sh / H) * 0.98;
    this.world.scale.set(scale);
    this.world.x = (sw - W * scale) / 2;
    this.world.y = (sh - H * scale) / 2;
    this.fitScale = scale;            // z == 1 at the fitted full view
    this.minScale = scale * 0.85;
    this.maxScale = scale * 16;
    this.updateLabelVisibility();
  }
  _clampView() {
    this.world.scale.x = Math.max(this.minScale, Math.min(this.maxScale, this.world.scale.x));
    this.world.scale.y = this.world.scale.x;
  }

  toScreen(wx, wy) {
    return { x: this.world.x + wx * this.world.scale.x, y: this.world.y + wy * this.world.scale.y };
  }

  _bindInteraction() {
    const canvas = this.app.canvas;
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const wx = (mx - this.world.x) / this.world.scale.x;
      const wy = (my - this.world.y) / this.world.scale.y;
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      let ns = this.world.scale.x * factor;
      ns = Math.max(this.minScale, Math.min(this.maxScale, ns));
      this.world.scale.set(ns);
      this.world.x = mx - wx * ns;
      this.world.y = my - wy * ns;
      this.updateLabelVisibility();
    }, { passive: false });

    let dragging = false, lx = 0, ly = 0;
    canvas.addEventListener("pointerdown", (e) => { dragging = true; lx = e.clientX; ly = e.clientY; });
    window.addEventListener("pointerup", () => { dragging = false; });
    window.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      this.world.x += e.clientX - lx;
      this.world.y += e.clientY - ly;
      lx = e.clientX; ly = e.clientY;
    });
  }

  // Label LOD: gate by zoom × tier × strength so only pivotal threads show when zoomed out.
  updateLabelVisibility() {
    const z = this.world.scale.x / (this.fitScale || this.minScale);   // 1 at full view
    for (const sn of this.strandNodes) {
      // At full view only the pivotal (strength-5 Tier-1) threads are labelled;
      // more appear as you zoom in, gated by depth_tier then strength.
      const show =
        (sn.tierRank === 1 && (sn.st.strength >= 5 || z > 1.6)) ||
        (sn.tierRank === 2 && z > 2.6) ||
        (sn.tierRank === 3 && z > 4.8);
      sn.label.visible = show && sn.x <= this.xOf(this.frontYear) + 2;
      sn.label.style.fontSize = Math.max(8.5, 13 / Math.sqrt(z));
    }
    if (this._originLabel) this._originLabel.style.fontSize = Math.max(10, 15 / Math.sqrt(z));
  }

  // -- time reveal ---------------------------------------------------------------
  setFront(year) {
    this.frontYear = Math.max(this.y0, Math.min(this.y1, year));
    const fx = this.xOf(this.frontYear);
    this.revealMask.clear();
    this.revealMask.rect(0, 0, fx + 2, H).fill(0xffffff);
    // origin pulse near Pentecost
    const pent = Math.max(0, 1 - Math.abs(this.frontYear - 33) / 60);
    if (this._originGlow) this._originGlow.scale.set(1 + pent * 0.8);
    this.updateLabelVisibility();
    if (this.onFront) this.onFront(Math.round(this.frontYear));
  }

  play() { this.playing = true; if (this.frontYear >= this.y1) this.setFront(this.y0); }
  pause() { this.playing = false; }
  togglePlay() { this.playing ? this.pause() : this.play(); return this.playing; }

  _tick(ticker) {
    if (this.playing) {
      const dt = ticker.deltaMS / 1000;
      const yearsPerSec = (this.y1 - this.y0) / 26;   // full sweep ~26s
      this.setFront(this.frontYear + yearsPerSec * dt);
      if (this.frontYear >= this.y1) this.pause();
    }
    // gentle shimmer on the threads
    const tsec = (this._t = (this._t || 0) + ticker.deltaMS / 1000);
    this.threads.alpha = 0.92 + 0.08 * Math.sin(tsec * 1.3);
  }
}
