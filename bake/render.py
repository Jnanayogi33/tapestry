"""Offline bake: turn the thread FOREST into the luminous tapestry image.

Additive-accumulate glowing curves — faint dark warp (the woven ground of every unlit
life), gold/gray-gold lineage polylines, and curved transmission filaments — into
float intensity buffers; tone-map; BLOOM (gaussian, additive); colorize gold/gray/dark;
composite over a woven dark ground with vignette and frame. The right edge blazes
because thread density scales with the (log) Christian count.

This is pure numpy + scipy + PIL so it runs offline and bakes a still the browser just
navigates. Era frames are the same render with a time reveal (x <= reveal_x).
"""
from __future__ import annotations

import math
import os

import numpy as np
from scipy.ndimage import gaussian_filter

# Palette (RGB 0..1). Dark woven ground, warm gold fiber, hot white-gold blaze.
GROUND = np.array([0.016, 0.018, 0.030])
WOVEN = np.array([0.040, 0.036, 0.046])  # subtle weave tint
GOLD_CORE = np.array([1.00, 0.72, 0.28])
GOLD_HOT = np.array([1.00, 0.94, 0.78])
GRAY_GOLD = np.array([0.50, 0.40, 0.26])
DARK_FIBER = np.array([0.115, 0.097, 0.083])


class Tapestry:
    def __init__(self, width: int = 2400, height: int = 1200,
                 gold_gain: float = 0.80, gray_gain: float = 0.50, dark_gain: float = 0.26,
                 bloom_sigma: float = 7.0, bloom_strength: float = 1.25,
                 tone_k_gold: float = 0.62, line_width: float = 1.0):
        self.W = width
        self.H = height
        self.gold = np.zeros((height, width), np.float32)
        self.gray = np.zeros((height, width), np.float32)
        self.dark = np.zeros((height, width), np.float32)
        self.gold_gain = gold_gain
        self.gray_gain = gray_gain
        self.dark_gain = dark_gain
        self.bloom_sigma = bloom_sigma
        self.bloom_strength = bloom_strength
        self.tone_k_gold = tone_k_gold
        self.line_width = line_width

    # -- splatting -----------------------------------------------------------------
    def _splat(self, buf, xs, ys, w):
        """Additive bilinear splat of intensity w at fractional pixel coords."""
        if len(xs) == 0:
            return
        px = np.clip(np.asarray(xs) * (self.W - 1), 0, self.W - 1.001)
        py = np.clip(np.asarray(ys) * (self.H - 1), 0, self.H - 1.001)
        x0 = px.astype(np.int32); y0 = py.astype(np.int32)
        fx = px - x0; fy = py - y0
        wv = np.full(px.shape, w, np.float32) if np.isscalar(w) else np.asarray(w, np.float32)
        for dx, dy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                           (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(buf, (np.clip(y0 + dy, 0, self.H - 1),
                            np.clip(x0 + dx, 0, self.W - 1)), wv * wt)

    def _resample(self, xs, ys):
        """Resample a polyline to ~1px spacing in image space."""
        xs = np.asarray(xs, np.float64); ys = np.asarray(ys, np.float64)
        if len(xs) < 2:
            return xs, ys
        dx = np.diff(xs) * self.W; dy = np.diff(ys) * self.H
        seg = np.sqrt(dx * dx + dy * dy)
        cum = np.concatenate([[0], np.cumsum(seg)])
        total = cum[-1]
        if total < 1:
            return xs, ys
        n = int(total) + 1
        t = np.linspace(0, total, n)
        return np.interp(t, cum, xs), np.interp(t, cum, ys)

    def add_polyline(self, xs, ys, buf, intensity):
        rx, ry = self._resample(xs, ys)
        self._splat(buf, rx, ry, intensity)

    def add_curve(self, p0, p1, buf, intensity, bow=0.16, sign=1):
        """Quadratic bezier from p0 to p1, bowed perpendicular (signed) for an organic
        arc — never a straight line. `bow` is a fraction of segment length."""
        (x0, y0), (x1, y1) = p0, p1
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dxn, dyn = (x1 - x0), (y1 - y0)
        L = math.hypot(dxn, dyn) + 1e-9
        nx, ny = -dyn / L, dxn / L
        b = bow * L * sign
        cx, cy = mx + nx * b, my + ny * b
        n = max(6, int(L * self.W / 5))
        t = np.linspace(0, 1, n)
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        self._splat(buf, bx, by, intensity)

    def add_chain(self, wp, buf, intensity, sign, phase):
        """Render a lineage chain as ONE smooth Catmull-Rom spline through its waypoints
        (no per-segment kinks, no vertical jumps), with a gentle perpendicular meander
        so threads braid, and intensity RAMPING from dim near the seed to bright near
        the leaf — so density and the blaze accumulate on the right (the billions)."""
        if len(wp) < 2:
            return
        P = np.array(wp, dtype=np.float64)
        n = len(P)
        xs_out = []; ys_out = []; prog_out = []
        for i in range(n - 1):
            p0 = P[max(0, i - 1)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(n - 1, i + 2)]
            seglen = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            steps = max(3, int(seglen * self.W / 5))
            t = np.linspace(0, 1, steps, endpoint=False)
            t2 = t * t; t3 = t2 * t
            for dim, out in ((0, xs_out), (1, ys_out)):
                a = 0.5 * ((2 * p1[dim]) + (-p0[dim] + p2[dim]) * t +
                           (2 * p0[dim] - 5 * p1[dim] + 4 * p2[dim] - p3[dim]) * t2 +
                           (-p0[dim] + 3 * p1[dim] - 3 * p2[dim] + p3[dim]) * t3)
                out.extend(a.tolist())
            prog_out.extend(((i + t) / (n - 1)).tolist())
        xs = np.array(xs_out); ys = np.array(ys_out); prog = np.array(prog_out)
        if len(xs) < 2:
            return
        # perpendicular meander along the path (braid)
        amp = 0.010 + 0.012 * ((phase * 7.3) % 1.0)
        mer = sign * amp * np.sin(prog * (10 + 8 * ((phase * 3.1) % 1.0)) + phase * 6.28)
        dx = np.gradient(xs); dy = np.gradient(ys)
        L = np.hypot(dx, dy) + 1e-9
        ys = ys + mer * (dx / L)
        xs = xs - mer * (dy / L)
        inten = intensity * (0.25 + 1.05 * prog)
        self._splat(buf, np.clip(xs, 0, 1), np.clip(ys, 0, 1), inten)

    # -- compose the forest --------------------------------------------------------
    def render_forest(self, forest, reveal_x: float = 1.0):
        # dark warp first (faint ground of unlit lives)
        for d in forest["dark"]:
            x0 = d["x0"]; x1 = min(d["x1"], reveal_x)
            if x0 > reveal_x or x1 <= x0:
                continue
            n = max(2, int((x1 - x0) * self.W / 3))
            t = np.linspace(0, 1, n)
            xs = x0 + (x1 - x0) * t
            ys = d["y"] + d["amp"] * np.sin(6.0 * t + d["phase"])
            self._splat(self.dark, xs, ys, 0.16)

        # LIT-LIFE DENSITY UNDERLAY — every (sampled) lit life as a faint short thread.
        # The modern multitude makes the right edge blaze; kept faint so the lineage
        # threads read on top.
        for L in forest.get("lit_lives", []):
            x0 = L["x0"]; x1 = min(L["x1"], reveal_x)
            if x0 > reveal_x or x1 <= x0:
                continue
            n = max(2, int((x1 - x0) * self.W / 3))
            t = np.linspace(0, 1, n)
            xs = x0 + (x1 - x0) * t
            ys = L["y"] + 0.006 * np.sin(5.0 * t + L["phase"])
            buf = self.gold if L["gold"] else self.gray
            self._splat(buf, xs, ys, 0.16 if L["gold"] else 0.10)

        # real lineage CHAINS — who-lit-whom traced back to the seed; the flowing gold
        # threads that fan out and braid, emanating from the one origin.
        for ch in forest.get("chains", []):
            wp = [(x, y) for (x, y) in ch["wp"] if x <= reveal_x + 1e-6]
            if len(wp) < 2:
                continue
            buf = self.gold if ch["gold"] else self.gray
            inten = 0.34 if ch["gold"] else 0.22
            self.add_chain(wp, buf, inten, ch.get("sign", 1), ch.get("phase", 0.0))

        # the seed: a concentrated bright point at left-center (a tiny gaussian blob so
        # it reads as a single ignition point, not a band).
        sx, sy = forest["seed_xy"]
        if sx <= reveal_x:
            rr = np.linspace(-0.012, 0.012, 25)
            gx, gy = np.meshgrid(rr, rr)
            w = np.exp(-(gx ** 2 + gy ** 2) / (2 * 0.0045 ** 2))
            self._splat(self.gold, (sx + gx).ravel(), (sy + gy).ravel(), (1.3 * w).ravel())

    # -- tone-map + bloom + colorize ----------------------------------------------
    def compose(self) -> np.ndarray:
        H, W = self.H, self.W
        # gentle line widening so 1px splats read as glowing fibers
        g = gaussian_filter(self.gold, 0.9)
        gr = gaussian_filter(self.gray, 0.9)
        dk = gaussian_filter(self.dark, 1.0)

        # tone-map each (compress to 0..1)
        gold_v = 1.0 - np.exp(-self.tone_k_gold * self.gold_gain * g)
        gray_v = 1.0 - np.exp(-1.1 * self.gray_gain * gr)
        dark_v = 1.0 - np.exp(-1.4 * self.dark_gain * dk)

        # bloom (additive glow) from the bright gold
        bloom = np.zeros_like(g)
        for s, amp in ((self.bloom_sigma, 1.0), (self.bloom_sigma * 3.0, 0.5),
                       (self.bloom_sigma * 8.0, 0.28)):
            bloom += amp * gaussian_filter(gold_v, s)
        bloom *= self.bloom_strength

        # woven ground + vignette
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        weave = (0.5 + 0.5 * np.sin(yy * math.pi * 2 * (H / 7.0) / H)) * \
                (0.5 + 0.5 * np.sin(xx * math.pi * 2 * (W / 9.0) / W))
        ground = (GROUND[None, None, :] + WOVEN[None, None, :] * (0.18 * weave)[..., None]).astype(np.float32)
        ground = np.broadcast_to(ground, (H, W, 3)).copy()

        img = ground.copy()
        # dark fiber over ground
        img += DARK_FIBER[None, None, :] * dark_v[..., None]
        # gray-gold
        img += GRAY_GOLD[None, None, :] * gray_v[..., None]
        # gold core: warm -> hot white as it intensifies
        hot = np.clip(gold_v, 0, 1)[..., None]
        gold_col = GOLD_CORE[None, None, :] * (1 - hot ** 1.5) + GOLD_HOT[None, None, :] * (hot ** 1.5)
        img += gold_col * gold_v[..., None]
        # bloom in warm gold
        img += GOLD_CORE[None, None, :] * bloom[..., None] * 0.5
        img += GOLD_HOT[None, None, :] * (bloom ** 2)[..., None] * 0.15

        # vignette + frame
        cx, cy = W / 2, H / 2
        r = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
        vig = np.clip(1.15 - 0.55 * r ** 2, 0.45, 1.0)
        img *= vig[..., None]
        # thin frame
        b = max(2, int(min(W, H) * 0.012))
        img[:b, :, :] *= 0.25; img[-b:, :, :] *= 0.25
        img[:, :b, :] *= 0.25; img[:, -b:, :] *= 0.25

        img = np.clip(img, 0, 1)
        # mild filmic
        img = img / (img + 0.85) * 1.85
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)

    def save(self, path: str, arr=None) -> None:
        from PIL import Image
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        im = Image.fromarray(self.compose() if arr is None else arr, "RGB")
        if path.lower().endswith((".jpg", ".jpeg")):
            im.save(path, quality=88, optimize=True)
        else:
            im.save(path)
