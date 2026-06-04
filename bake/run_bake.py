"""Drive the offline bake: thread forest -> climax still + era frames + manifest.

Outputs land under viz/public/tapestry/ so the Vite build picks them up as static
assets, plus a downscaled inspection copy under reports/look/ for the visual loop.

Run:
  python -m bake.run_bake --fast            # quick low-res iteration
  python -m bake.run_bake                    # full bake
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json  # noqa: E402

from PIL import Image  # noqa: E402

from pipeline import schema as S  # noqa: E402
from sim import data as D  # noqa: E402
from sim.threads.agents import AgentField, AgentConfig, DEFAULT_PARAMS  # noqa: E402
from bake.render import Tapestry  # noqa: E402


def load_params():
    path = os.path.join(D.DEFAULT_DATA_DIR, "thread_params.json")
    if os.path.exists(path):
        return json.load(open(path))["params"]
    return dict(DEFAULT_PARAMS)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "viz", "public", "tapestry")
LOOK_DIR = os.path.join(REPO_ROOT, "reports", "look")

ERA_YEARS = [100, 313, 500, 1000, 1517, 1800, 1900, 1970, 2025]


def downscale_save(img_path: str, dst: str, max_w: int = 2000) -> None:
    im = Image.open(img_path)
    if im.width > max_w:
        h = round(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst)


def make_renderer(width, height, params) -> Tapestry:
    return Tapestry(width=width, height=height, **params)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="low-res, fewer threads (iteration)")
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--budget-lit", type=int, default=0)
    ap.add_argument("--budget-dark", type=int, default=0)
    ap.add_argument("--iter", type=str, default="01", help="iteration tag for reports/look")
    ap.add_argument("--frames", action="store_true", help="also render era frames")
    ap.add_argument("--params", type=str, default="", help="JSON of Tapestry render params")
    args = ap.parse_args()

    if args.fast:
        width = args.width or 2200
        height = args.height or 1100
        n_lives = args.budget_lit or 120_000
        max_lit, max_links, max_dark = 90_000, 30_000, 45_000
    else:
        width = args.width or 6400
        height = args.height or 3200
        n_lives = args.budget_lit or 300_000
        max_lit, max_links, max_dark = 220_000, 70_000, 110_000

    render_params = json.loads(args.params) if args.params else {}
    sim_params = load_params()

    t0 = time.time()
    print(f"[bake] running agent contagion (n_lives={n_lives}) with calibrated params ...")
    af = AgentField(AgentConfig(n_lives=n_lives, quiet=False))
    forest = af.export_forest(sim_params, max_lit=max_lit, max_links=max_links, max_dark=max_dark)
    print(f"[bake] real forest built in {time.time()-t0:.1f}s — {forest['meta']}")

    os.makedirs(OUT_DIR, exist_ok=True)

    # Climax (full reveal).
    t1 = time.time()
    tap = make_renderer(width, height, render_params)
    tap.render_forest(forest, reveal_x=1.0)
    climax_path = os.path.join(OUT_DIR, "climax.jpg")
    tap.save(climax_path)
    print(f"[bake] climax {width}x{height} rendered in {time.time()-t1:.1f}s -> {climax_path}")

    # Inspection copy.
    look_path = os.path.join(LOOK_DIR, f"climax_i{args.iter}.png")
    downscale_save(climax_path, look_path, max_w=2000)
    print(f"[bake] inspection copy -> {look_path}")

    manifest = {"climax": "tapestry/climax.jpg", "width": width, "height": height,
                "frames": [], "era_years": []}

    if args.frames:
        fdir = os.path.join(OUT_DIR, "frames")
        os.makedirs(fdir, exist_ok=True)
        fw, fh = (width if args.fast else 2600), (height if args.fast else 1300)
        for yr in ERA_YEARS:
            ft = make_renderer(fw, fh, render_params)
            ft.render_forest(forest, reveal_x=S.x_of_year(yr))
            fp = os.path.join(fdir, f"frame_{yr}.jpg")
            ft.save(fp)
            manifest["frames"].append(f"tapestry/frames/frame_{yr}.jpg")
            manifest["era_years"].append(yr)
            print(f"[bake] era frame {yr} -> {fp}")
            if yr in (313, 1000, 2025):
                downscale_save(fp, os.path.join(LOOK_DIR, f"frame_{yr}_i{args.iter}.png"), 1300)

    json.dump(manifest, open(os.path.join(OUT_DIR, "manifest.json"), "w"), indent=1)
    print(f"[bake] manifest -> {os.path.join(OUT_DIR, 'manifest.json')}")
    print(f"[bake] total {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
