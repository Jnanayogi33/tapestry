"""Agent-based spatio-temporal contagion — the REAL simulation behind the tapestry.

Every thread is one sampled human life. Lives are sampled across places and birth
decades by population (so the field is filled by real people, most of them dark). They
sit in a network of actual ties — family (a parent in the previous generation, same
place), spatial neighbours (contemporaries in the same and adjacent places), and the
long-range bridges carried by named strands (a missionary connecting an old-world
believer to a new-world field). The ONLY life lit a priori is the seed — Christ, AD 30,
Judaea. From there belief spreads ONLY by intersection: an Unexposed life turns
Affiliated when enough of its actual neighbours are already lit (complex contagion),
or when a named strand locally ignites it. Practice deepens, faith frays under
secular/suppression pressure, the lapsed return through believing family ties — all per
life, all emergent. Who-lit-whom is recorded, so everything gold traces back to Christ.

The aggregate region×decade lit-fraction is CALIBRATED (global rates only) to the
anchors — never imposed. The renderer then draws the actual lives and the actual
transmission tree; the fan, the outward spread and the modern blaze are emergent.

Sampling: ~10^5 lives stand in for billions (documented). Contagion is vectorised with
scipy.sparse so the calibration loop is fast; the network is built once.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import numpy as np
from scipy import sparse

from pipeline import schema as S
from sim import data as D
from sim.embedding import Embedding
from sim.threads.targets import Targets

# Belief states.
U, AFF, PRAC, LAP, UNAFF, MART = 0, 1, 2, 3, 4, 5
STATE_NAMES = {U: "Unexposed", AFF: "Affiliated", PRAC: "Practicing",
               LAP: "Lapsed", UNAFF: "Unaffiliated", MART: "Martyred"}
LIT_STATES = (AFF, PRAC)

ADJACENCY = {
    "Roman/Mediterranean": ["Western Europe", "Eastern Europe & Russia", "Middle East & North Africa"],
    "Western Europe": ["Roman/Mediterranean", "Eastern Europe & Russia", "North America", "Latin America", "Sub-Saharan Africa"],
    "Eastern Europe & Russia": ["Roman/Mediterranean", "Western Europe", "Middle East & North Africa", "East Asia"],
    "Middle East & North Africa": ["Roman/Mediterranean", "Eastern Europe & Russia", "Sub-Saharan Africa", "South Asia"],
    "Sub-Saharan Africa": ["Middle East & North Africa", "Western Europe"],
    "South Asia": ["Middle East & North Africa", "Southeast Asia", "East Asia"],
    "East Asia": ["Eastern Europe & Russia", "South Asia", "Southeast Asia"],
    "Southeast Asia": ["South Asia", "East Asia"],
    "Latin America": ["Western Europe", "North America"],
    "North America": ["Western Europe", "Latin America"],
}
TIER_W = {"Tier 1": 1.0, "Tier 2": 0.62, "Tier 3": 0.4}

# MODELED incumbency resistance: the strength of the entrenched non-Christian religion
# a region's people are already committed to (so most will NOT convert no matter how
# many lit neighbours they have). This is the honest reason Asia stayed a minority while
# Europe did not — it cannot emerge from global rates, so it is supplied as a flagged
# prior (see BLOCKERS, alongside distance_norm and practicing_ratio). 0=open, 1=closed.
# Applied to CONVERSION only — a Christian family still passes on its faith (vertical),
# but growth INTO the incumbent majority is gated. Time-varying handled in code (Islam).
BASE_RESISTANCE = {
    "Roman/Mediterranean": 0.10,         # classical paganism gave way
    "Western Europe": 0.10,
    "Eastern Europe & Russia": 0.15,
    "North America": 0.15,
    "Latin America": 0.28,               # indigenous religions, but colonized & converted
    "Sub-Saharan Africa": 0.38,          # traditional religions; converts strongly in modernity
    "Middle East & North Africa": 0.20,  # rises to ~0.9 after the 7th-c. Islamic conquests
    "South Asia": 0.86,                  # Hinduism entrenched
    "East Asia": 0.80,                   # Confucian / Buddhist
    "Southeast Asia": 0.60,              # mixed: Philippines converts, Islam/Buddhism resist
}
EFFECT_SIGN = {"Strong+": 1.0, "Mild+": 0.5, "Neutral": 0.0, "Mild-": -0.5, "Strong-": -1.0}


@dataclass
class AgentConfig:
    n_lives: int = 120_000
    seed: int = 1729
    k_spatial: int = 9
    data_dir: str = D.DEFAULT_DATA_DIR
    quiet: bool = True


# Global contagion rates (calibrated). Bounds: (low, high, mid).
PARAM_SPEC = {
    "base_conversion": (0.02, 0.55, 0.14),       # internal growth from a beachhead (slow)
    "contagion_threshold": (0.05, 0.7, 0.34),    # complex contagion needs a critical mass
    "practice_rate": (0.05, 0.9, 0.35),
    "secular_term": (0.0, 0.7, 0.20),
    "suppression_severity": (0.0, 1.0, 0.50),
    "return_rate": (0.0, 0.6, 0.15),
    "strand_ignite": (0.0, 0.8, 0.34),           # missions plant the beachhead
    "vertical_transmission": (0.2, 0.98, 0.78),
}
PARAM_NAMES = list(PARAM_SPEC)
DEFAULT_PARAMS = {k: v[2] for k, v in PARAM_SPEC.items()}


def secular_baseline(year):
    return 1.0 / (1.0 + math.exp(-(year - 1880.0) / 30.0))


class AgentField:
    def __init__(self, config: AgentConfig | None = None):
        self.cfg = config or AgentConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.emb = Embedding(self.cfg.data_dir)
        self.tg = Targets(self.cfg.data_dir)
        self.years = self.tg.years
        self.n_steps = len(self.years)
        self.strands = D.load_strands(self.cfg.data_dir)
        self.places = list(self.emb.places.values())
        self.place_index = {p.name: i for i, p in enumerate(self.places)}
        self._sample_lives()
        self._build_fields()
        self._build_network()

    # -- 1. sample lives ------------------------------------------------------------
    def _sample_lives(self) -> None:
        """Allocate lives across (place, birth-decade) ∝ population. Every life is a
        real thread; most will remain dark."""
        cells = []          # (place_idx, decade_idx, weight)
        for pi, p in enumerate(self.places):
            reg = p.parent_macro_region
            if reg not in S.REGIONS:
                continue
            # split the region population across its places (by inverse-distance-ish)
            region_places = [q for q in self.places if q.parent_macro_region == reg]
            share = 1.0 / max(1, len(region_places))
            for di in range(self.n_steps):
                pop = self.tg.population(reg, di) * share
                # Roman/Med is antiquity-only — fade its population after 640.
                yr = self.years[di]
                if reg == "Roman/Mediterranean":
                    pop *= (1.0 if yr <= 500 else max(0.0, 1.0 - (yr - 500) / 250.0))
                if pop > 0:
                    cells.append((pi, di, pop))
        if not cells:
            raise RuntimeError("no population cells — run make_fixtures")
        w = np.array([c[2] for c in cells], dtype=np.float64)
        w = w / w.sum()
        counts = self.rng.multinomial(self.cfg.n_lives, w)

        N = int(counts.sum())
        self.N = N
        self.place_of = np.zeros(N, np.int32)
        self.region_of = np.zeros(N, np.int32)
        self.birth_t = np.zeros(N, np.int32)
        self.death_t = np.zeros(N, np.int32)
        self.x = np.zeros(N, np.float64)
        self.y = np.zeros(N, np.float64)
        self.disp = np.zeros(N, np.float64)
        self.region_names = list(S.REGIONS)
        reg_idx = {r: i for i, r in enumerate(self.region_names)}

        i = 0
        step = self.cfg.step if hasattr(self.cfg, "step") else 10
        for (pi, di), c in zip(((c[0], c[1]) for c in cells), counts):
            if c == 0:
                continue
            p = self.places[pi]
            reg = p.parent_macro_region
            yr = self.years[di]
            sl = slice(i, i + c)
            self.place_of[sl] = pi
            self.region_of[sl] = reg_idx.get(reg, 0)
            self.birth_t[sl] = di
            life_decades = self.rng.integers(6, 10, size=c)   # overlapping generations -> smoother
            self.death_t[sl] = np.minimum(self.n_steps, di + life_decades)
            # x within the birth decade; y on the place band with jitter
            self.x[sl] = np.clip(S.x_of_year(yr) + self.rng.normal(0, 0.004, c), 0, 1)
            base_y = p.base_y
            spread = 0.05 * (0.5 + abs(base_y - 0.5) * 1.4)
            self.y[sl] = np.clip(base_y + self.rng.normal(0, spread, c), 0.002, 0.998)
            # disposition: region/era mix (persecuted & Global-South skew higher)
            mean_disp = self._disp_mean(reg, yr)
            a = mean_disp * 4 + 0.5
            b = (1 - mean_disp) * 4 + 0.5
            self.disp[sl] = self.rng.beta(a, b, c)
            i += c
        self.N = i
        for arr in ("place_of", "region_of", "birth_t", "death_t", "x", "y", "disp"):
            setattr(self, arr, getattr(self, arr)[: self.N])

        # inject the SEED life: Christ, Judaea, decade 0.
        self._seed_idx = self._inject_seed()

    def _disp_mean(self, region, year):
        """Innate religiosity disposition — a stable personal trait, NOT region-tuned
        openness. Roughly neutral everywhere (so an unreached people does not convert
        just by being in an 'early' era); modern secular West a little lower, modern
        Global South a little higher. The historical differences in WHERE the faith
        takes root come from the network + the missions, not from disposition."""
        if year >= 1900 and region in ("Western Europe", "Eastern Europe & Russia", "North America"):
            return 0.42
        if year >= 1900 and region in ("Sub-Saharan Africa", "Latin America", "South Asia",
                                        "East Asia", "Southeast Asia"):
            return 0.56
        return 0.50

    def _inject_seed(self) -> int:
        pi = self.place_index.get("Judaea", 0)
        p = self.places[pi]
        self.place_of = np.append(self.place_of, pi).astype(np.int32)
        self.region_of = np.append(self.region_of, self.region_names.index(p.parent_macro_region) if p.parent_macro_region in self.region_names else 0).astype(np.int32)
        self.birth_t = np.append(self.birth_t, 0).astype(np.int32)
        self.death_t = np.append(self.death_t, 1).astype(np.int32)
        self.x = np.append(self.x, 0.0)
        self.y = np.append(self.y, 0.5)
        self.disp = np.append(self.disp, 1.0)
        self.N += 1
        return self.N - 1

    # -- 2. precompute LOCAL strand igniters + region-level event fields ------------
    def _build_fields(self) -> None:
        """Strands are LOCAL igniters: each works near its own (x,y) — a narrow band in
        y (its place neighbourhood) across its window in time — NOT a whole region at
        once. So Paul (Antioch, y≈0.5) plants the Mediterranean core, while Western
        Europe waits for Patrick/Boniface centuries later, and East Asia for Alopen/
        Xavier — exactly as history runs. Events stay region-level (broad inflections)."""
        R = len(self.region_names)
        T = self.n_steps
        ridx = {r: i for i, r in enumerate(self.region_names)}
        # geographic distance (km) from each place to every place (for LOCAL ignition).
        latlon = [(p.lat, p.lon) for p in self.places]
        # active strands per decade (geographic place-weight kernels)
        self.active_strands: list[list[dict]] = [[] for _ in range(T)]
        self.strand_xy: list[dict] = []
        for st in self.strands:
            ws = st.effect_window_start if st.effect_window_start is not None else st.birth_year
            we = st.effect_window_end if st.effect_window_end is not None else (st.death_year or ws)
            if ws is None:
                continue
            regions = [r for r in st.expanded_regions() if r in ridx] or \
                      [r for r in st.primary_region if r in ridx]
            strength = TIER_W.get(st.depth_tier, 0.4) * (st.strength / 5.0)
            p = self.emb.resolve_place(st.place or None,
                                       (st.primary_region or regions or ["Roman/Mediterranean"])[0])
            sx, sy = S.x_of_year(max(S.TIMELINE_START, ws)), (p.base_y if p else 0.5)
            # GEOGRAPHIC reach: a missionary directly ignites his city/locale — a few
            # hundred km, NOT a whole continent. (At 3000 km Peter would Christianize all
            # Europe from Rome in the 1st c.) The rest spreads later via other strands and
            # slow same-region creep, so the pacing stays historical.
            reach_km = 160.0 + 130.0 * st.strength
            slat, slon = (p.lat, p.lon) if p else (S.JERUSALEM_LAT, S.JERUSALEM_LON)
            pw = np.zeros(len(self.places))
            for j, (la, lo) in enumerate(latlon):
                d = S.haversine_km(slat, slon, la, lo)
                wv = math.exp(-(d / reach_km) ** 2)
                pw[j] = wv if wv > 0.04 else 0.0
            t0 = max(0, int((ws - S.TIMELINE_START) / 10))
            t1 = min(T - 1, int((we - S.TIMELINE_START) / 10))
            rec = {"name": st.name, "x": sx, "y": sy, "pw": pw, "mech": st.mechanism_template,
                   "strength": strength, "t0": t0, "t1": t1, "regions": regions,
                   "sid": len(self.strand_xy),
                   "primary": (st.primary_region or regions or ["Roman/Mediterranean"])[0]}
            self.strand_xy.append(rec)
            for di in range(t0, t1 + 1):
                self.active_strands[di].append(rec)

        # region-level event fields (secular / suppression / mild conv & revival)
        self.f_secular = np.zeros((R, T))
        self.f_suppress = np.zeros((R, T))     # event-driven (region-level)
        self.f_conv_ev = np.zeros((R, T))
        self.f_practice_ev = np.zeros((R, T))
        for ev in D.load_events(self.cfg.data_dir):
            sign = EFFECT_SIGN.get(ev.effect, 0.0)
            # Use the EXPLICITLY listed regions only — do NOT expand "GLOBAL" to all 10.
            # (Pentecost is tagged GLOBAL but must not convert unreached China in AD 33;
            # it ignites its actual place, the Roman/Mediterranean core.)
            regions = [r for r in ev.regions if r in ridx]
            dur = max(20, int(ev.duration_years or 20))
            for di in range(T):
                yr = self.years[di] + 5
                if abs(yr - ev.year_sort) > max(40, dur):
                    continue
                for r in regions:
                    ri = ridx[r]
                    if ev.mechanism == "secularization":
                        self.f_secular[ri, di] += 0.5 * max(0, -sign)
                    elif ev.mechanism == "persecution":
                        self.f_suppress[ri, di] += 0.5 * max(0, -sign)
                    elif ev.mechanism == "conversion":
                        self.f_conv_ev[ri, di] += 0.12 * max(0, sign)
                    elif ev.mechanism == "revival":
                        self.f_practice_ev[ri, di] += 0.18 * max(0, sign)
        # durable rival incumbency (Islam in MENA from ~700; Soviet atheism) — region-level
        self.f_rival = np.zeros((R, T))
        acc = np.zeros(R)
        for di in range(T):
            acc = 0.93 * acc + 0.9 * self.f_suppress[:, di]
            self.f_rival[:, di] = acc

        # modeled incumbency resistance (time-varying: Islam ramps MENA after ~640)
        self.resistance = np.zeros((R, T))
        for ri, r in enumerate(self.region_names):
            base = BASE_RESISTANCE.get(r, 0.3)
            for di in range(T):
                yr = self.years[di]
                res = base
                if r == "Middle East & North Africa":
                    if yr >= 750:
                        res = 0.9
                    elif yr >= 640:
                        res = base + (0.9 - base) * (yr - 640) / 110.0
                self.resistance[ri, di] = res

    def _local_strand_fields(self, t: int):
        """Per-life local strand contributions at decade t (conv/practice/return/
        suppress/martyr), summed over active strands by a y-kernel."""
        N = self.N
        conv = np.zeros(N); prac = np.zeros(N); ret = np.zeros(N)
        sup = np.zeros(N); mart = np.zeros(N)
        for s in self.active_strands[t]:
            # geographic place-weight gathered to each life by its place index
            w = s["strength"] * s["pw"][self.place_of]
            mt = s["mech"]
            if mt in ("APOSTOLIC_PROPAGATION", "SEED"):
                conv += w
            elif mt == "INSTITUTIONAL":
                conv += 0.6 * w; prac += 0.3 * w
            elif mt == "THEOLOGICAL":
                prac += w
            elif mt == "TRANSLATION":
                conv += 0.3 * w; prac += 0.5 * w
            elif mt == "REVIVAL":
                prac += w; ret += w
            elif mt == "SUPPRESSION":
                sup += w
            elif mt == "MARTYRDOM":
                mart += w
        return conv, prac, ret, sup, mart

    # -- 3. build the life network (once) -------------------------------------------
    def _build_network(self) -> None:
        """Sparse adjacency: family (prev-gen same place) + spatial neighbours (same &
        adjacent places, near in time). Symmetric for contagion. Strand bridges are
        handled as the per-region conversion field (local ignition), with transmission
        links assigned to the strand at export time."""
        rng = self.rng
        # bucket lives by (place, birth decade)
        buckets: dict[tuple, list[int]] = {}
        for i in range(self.N):
            buckets.setdefault((int(self.place_of[i]), int(self.birth_t[i])), []).append(i)
        # adjacency place lists per region
        region_places: dict[str, list[int]] = {}
        for pi, p in enumerate(self.places):
            region_places.setdefault(p.parent_macro_region, []).append(pi)

        rows = []; cols = []
        fam_rows = []; fam_cols = []
        K = self.cfg.k_spatial
        # cross-region contact is RARE (a few travelers) so belief creeps slowly between
        # regions over centuries and jumps far mainly via named-strand missions — not in
        # a global cascade. Within a region, ties are dense so a beachhead grows.
        P_CROSS = 0.001     # belief crosses regions almost only via named missions
                            # (strands), not a diffuse traveler cascade — so a far region
                            # stays dark until its missionary actually arrives.
        for (pi, di), members in buckets.items():
            p = self.places[pi]
            reg = p.parent_macro_region
            same = members
            prev = buckets.get((pi, di - 1), [])
            nxt = buckets.get((pi, di + 1), [])
            # SAME-region adjacent places (dense, near in time)
            sameregion_pool = []
            for q in region_places.get(reg, []):
                if q != pi:
                    sameregion_pool += buckets.get((q, di), []) + buckets.get((q, di - 1), [])
            # only the FIRST adjacent region (primary geographic neighbour), sparse
            adjregion_pool = []
            for ar in ADJACENCY.get(reg, [])[:1]:
                for q in region_places.get(ar, []):
                    adjregion_pool += buckets.get((q, di), [])
            local_pool = same + prev + nxt + (sameregion_pool if sameregion_pool else [])
            for i in members:
                if prev:
                    for par in rng.choice(prev, size=min(2, len(prev)), replace=False):
                        fam_rows.append(i); fam_cols.append(int(par))
                cand = local_pool if len(local_pool) <= K else list(rng.choice(local_pool, size=K, replace=False))
                for j in cand:
                    if j != i:
                        rows.append(i); cols.append(int(j))
                # rare cross-region traveler tie
                if adjregion_pool and rng.random() < P_CROSS:
                    j = int(rng.choice(adjregion_pool))
                    rows.append(i); cols.append(j)
        N = self.N
        data = np.ones(len(rows), np.float32)
        A = sparse.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()
        A = A + A.T                          # symmetric ties
        A.data[:] = 1.0
        self.A = A
        self.deg = np.asarray(A.sum(axis=1)).ravel() + 1e-9
        fam = sparse.coo_matrix((np.ones(len(fam_rows), np.float32), (fam_rows, fam_cols)),
                                shape=(N, N)).tocsr()
        self.Fam = fam
        self.fam_deg = np.asarray(fam.sum(axis=1)).ravel() + 1e-9
        if not self.cfg.quiet:
            print(f"[agents] {self.N} lives, {A.nnz} spatial ties, {fam.nnz} family ties")

    # -- 4. contagion (vectorised, re-runnable for calibration) ---------------------
    def run_contagion(self, params: dict | None = None, record: bool = False):
        p = dict(DEFAULT_PARAMS)
        if params:
            p.update(params)
        rng = np.random.default_rng(self.cfg.seed + 1)
        N = self.N
        state = np.zeros(N, np.int8)
        state[self._seed_idx] = PRAC
        born = np.zeros(N, bool)
        born[self.birth_t == 0] = True

        lit_by = np.full(N, -1, np.int64) if record else None
        lit_t = np.full(N, -1, np.int16) if record else None
        transitions = [[] for _ in range(N)] if record else None
        if record:
            transitions[self._seed_idx].append((0, PRAC))
        # aggregate accumulators for calibration: lit & practicing & alive per region×decade
        R = len(self.region_names)
        agg_lit = np.zeros((R, self.n_steps))
        agg_prac = np.zeros((R, self.n_steps))
        agg_alive = np.zeros((R, self.n_steps))

        reg = self.region_of
        for t in range(self.n_steps):
            prev_alive = born & (self.death_t > t)
            litf_all = ((state == AFF) | (state == PRAC) | (state == MART)).astype(np.float32)
            # per-region incumbency CEILING headroom (computed once; gates ALL inflows so
            # the achievable Christian share is capped at 1-resistance — Asia stays a
            # minority even though Christian families keep transmitting within that cap).
            la = prev_alive & ((state == AFF) | (state == PRAC))
            ra_lit = np.bincount(reg[la], minlength=R).astype(np.float64)
            ra_all = np.bincount(reg[prev_alive], minlength=R).astype(np.float64)
            region_frac = ra_lit / np.maximum(ra_all, 1.0)
            ceiling = np.clip(1.0 - self.resistance[:, t], 0.03, 0.97)
            headroom = np.clip((ceiling - region_frac) / np.maximum(ceiling, 1e-6), 0.0, 1.0)
            hr = headroom[reg]
            # newborns this decade inherit faith from BOTH believing family AND a
            # believing community (born into Christendom) — what makes a Christianized
            # region self-sustain across generations instead of flashing out.
            newborn = (self.birth_t == t)
            if newborn.any():
                # normalise by ALIVE neighbours, not total degree (else dead/unborn
                # neighbours dilute the signal ~4x and no Christian community can pass
                # its faith to the next generation -> spurious collapse).
                fam_lit = self.Fam.dot(litf_all) / self.fam_deg
                alive_nbr = np.maximum(self.A.dot(prev_alive.astype(np.float32)), 1.0)
                comm_lit = self.A.dot(litf_all * prev_alive) / alive_nbr
                inherit = np.maximum(fam_lit, 0.85 * comm_lit)
                nb = newborn.nonzero()[0]
                # vertical respects the ceiling (replacement, not unbounded growth)
                become = nb[rng.random(len(nb)) < p["vertical_transmission"] * inherit[nb]
                           * (0.25 + 0.75 * hr[nb])]
                state[become] = AFF
                born[newborn] = True
                if record:
                    for idx in become:
                        lit_t[idx] = t
                        transitions[idx].append((t, AFF))
            alive = born & (self.death_t > t)

            # local strand fields (by y-proximity) + region-level event fields
            loc_conv, loc_prac, loc_ret, loc_sup, loc_mart = self._local_strand_fields(t)
            conv_field = loc_conv + self.f_conv_ev[reg, t]
            practice_field = loc_prac + self.f_practice_ev[reg, t]
            return_field = loc_ret
            mfield = loc_mart
            sup = p["suppression_severity"] * (loc_sup + self.f_suppress[reg, t]
                                               + 0.6 * self.f_rival[reg, t])
            sec = p["secular_term"] * (0.25 * secular_baseline(self.years[t]) + self.f_secular[reg, t])

            litf = ((state == AFF) | (state == PRAC)).astype(np.float32) * alive
            nbr_lit = self.A.dot(litf)
            nbr_alive = self.A.dot(alive.astype(np.float32))
            lit_frac = nbr_lit / np.maximum(nbr_alive, 1.0)

            # --- conversion U->A: complex contagion (needs a lit critical mass) OR a
            # named strand igniting locally (planting a beachhead even with no lit nbrs).
            susc = alive & (state == U)
            thr = p["contagion_threshold"] / (0.4 + 0.9 * self.disp)
            contagion = p["base_conversion"] * _sig((lit_frac - thr) * 9.0)
            ignite = p["strand_ignite"] * conv_field
            # incumbency: (a) resistance slows the RATE of growth into the majority;
            # (b) a per-region CEILING = 1-resistance caps the achievable share (most
            # people stay committed to the incumbent religion). Headroom -> 0 at the
            # ceiling, so Asia saturates low and Europe high — emergent within those caps.
            resist = self.resistance[reg, t]
            pconv = np.clip((contagion * (1.0 - 0.6 * resist) + ignite * (1.0 - 0.5 * resist))
                            * hr * (0.5 + self.disp), 0, 0.95)
            draw = rng.random(N)
            conv = susc & (draw < pconv)
            state[conv] = AFF
            if record:
                ci = conv.nonzero()[0]
                lit_t[ci] = t
                strand_dom = ignite[ci] > contagion[ci]
                self._assign_lit_by(ci, strand_dom, litf, t, lit_by, transitions, reg)

            # --- A->P practicing
            aff = alive & (state == AFF)
            pprac = np.clip(p["practice_rate"] * (0.2 + 0.8 * self.disp)
                            + 0.5 * practice_field, 0, 0.95)
            draw = rng.random(N)
            top = aff & (draw < pprac)
            state[top] = PRAC
            if record:
                for idx in top.nonzero()[0]:
                    transitions[idx].append((t, PRAC))

            # --- P->A relax (small)
            prc = alive & (state == PRAC)
            relax = prc & (rng.random(N) < 0.03)
            state[relax] = AFF

            # --- A/P -> L (secular + suppression), softened by disposition
            litnow = alive & ((state == AFF) | (state == PRAC))
            plapse = np.clip((sec + sup) * (1.1 - 0.6 * self.disp), 0, 0.9)
            draw = rng.random(N)
            lapse = litnow & (draw < plapse)
            state[lapse] = LAP
            if record:
                for idx in lapse.nonzero()[0]:
                    transitions[idx].append((t, LAP))

            # --- L -> N drift; L -> P return via believing family (Lyudmila)
            lapsed = alive & (state == LAP)
            litf2 = ((state == AFF) | (state == PRAC)).astype(np.float32) * alive
            fam_lit = self.Fam.dot(litf2) / self.fam_deg
            preturn = np.clip((p["return_rate"] * (0.3 + fam_lit) + 0.4 * return_field) * hr, 0, 0.8)
            draw = rng.random(N)
            ret = lapsed & (draw < preturn)
            state[ret] = PRAC
            drift = lapsed & ~ret & (rng.random(N) < (0.12 + sec))
            state[drift] = UNAFF
            if record:
                for idx in ret.nonzero()[0]:
                    transitions[idx].append((t, PRAC))
                for idx in drift.nonzero()[0]:
                    transitions[idx].append((t, UNAFF))

            # --- martyrdom near MARTYRDOM strands (local)
            if mfield.any():
                cand = alive & ((state == PRAC) | (state == AFF)) & (mfield > 0)
                mart = cand & (rng.random(N) < np.clip(0.04 * mfield, 0, 0.2))
                state[mart] = MART
                if record:
                    for idx in mart.nonzero()[0]:
                        transitions[idx].append((t, MART))

            # aggregate
            np.add.at(agg_alive[:, t], reg[alive], 1.0)
            litmask = alive & ((state == AFF) | (state == PRAC))
            np.add.at(agg_lit[:, t], reg[litmask], 1.0)
            np.add.at(agg_prac[:, t], reg[alive & (state == PRAC)], 1.0)

        result = {"agg_lit": agg_lit, "agg_prac": agg_prac, "agg_alive": agg_alive}
        if record:
            result.update({"state": state, "lit_by": lit_by, "lit_t": lit_t,
                           "transitions": transitions})
        return result

    def _assign_lit_by(self, ci, strand_dom, litf, t, lit_by, transitions, reg):
        """Record who lit each newly-converted life: a strand (negative-encoded) when
        the strand field dominated, else an actual lit neighbour."""
        actives = self.active_strands[t]
        for k, idx in enumerate(ci):
            transitions[idx].append((t, AFF))
            if strand_dom[k] and actives:
                # the active strand whose local place-weight here is strongest lit it
                pidx = self.place_of[idx]
                best = None; bw = -1.0
                for s in actives:
                    w = s["pw"][pidx] * s["strength"]
                    if w > bw:
                        bw = w; best = s
                lit_by[idx] = -(best["sid"] + 2) if (best is not None and bw > 0) else -1
            else:
                row = self.A.getrow(idx).indices
                lit_nb = [j for j in row if litf[j] > 0]
                if lit_nb:
                    lit_by[idx] = int(self.rng.choice(lit_nb))

    # -- aggregate lit fraction per region×decade -----------------------------------
    def lit_fraction(self, result) -> dict:
        out = {}
        for ri, r in enumerate(self.region_names):
            alive = result["agg_alive"][ri]
            lit = result["agg_lit"][ri]
            out[r] = np.where(alive > 0, lit / np.maximum(alive, 1.0), 0.0)
        return out


def _sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))
