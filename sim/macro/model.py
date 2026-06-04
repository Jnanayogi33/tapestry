"""Macro cohort simulation (Mesa).

Each region is a meta-agent cohort whose belief is a multi-state distribution that
evolves on decadal timesteps as RATE EQUATIONS (no NDlib):

    Unexposed -> Affiliated -> Practicing
         (back) <- Lapsed <- (Practicing/Affiliated under secular/suppression pressure)
    Lapsed -> Unaffiliated  (and Lapsed -> Practicing on revival/return)

Spread happens within a region (complex contagion past a threshold) and BETWEEN
regions over time-varying contact edges seeded from events.csv. Named individuals
(strands.csv) bend the curve by their mechanism_template, scaled by `strength` and
spread across [effect_window_start, effect_window_end] over regions_affected
(GLOBAL = all 10). Eight global parameters govern the whole system; the random seed
is fixed.

The model is config-driven: the SAME code runs the tiny smoke slice (1 region, 3
steps, 10 strands) and the full run (10 regions, AD 30 -> 2030, ~100 strands).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import mesa

from pipeline import schema as S
from sim import data as D
from sim.mesa_compat import (
    CompatAgent, all_agents, register_agent, seed_model, setup_schedule, step_all,
)

# --- The 8 global parameters: (low, high, midpoint) -------------------------------
PARAM_SPEC: dict[str, tuple[float, float, float]] = {
    "base_conversion_rate":        (0.02, 0.80, 0.25),
    "complex_contagion_threshold": (0.00, 0.40, 0.06),
    "secularization_term":         (0.00, 0.60, 0.12),
    "persecution_severity":        (0.00, 1.00, 0.30),
    "inter_region_decay":          (0.00, 0.95, 0.55),
    "fertility_adv":               (0.00, 0.12, 0.02),
    "martyrdom_amplification":     (0.00, 4.00, 1.50),
    "nominal_to_practicing_ratio": (0.02, 0.90, 0.30),
}
PARAM_NAMES = list(PARAM_SPEC.keys())
DEFAULT_PARAMS = {k: spec[2] for k, spec in PARAM_SPEC.items()}

BELIEF_STATES = ["U", "A", "P", "L", "N"]  # Unexposed, Affiliated, Practicing, Lapsed, uNaffiliated

TIER_WEIGHT = {"Tier 1": 1.0, "Tier 2": 0.6, "Tier 3": 0.35}
EFFECT_SIGN = {"Strong+": 1.0, "Mild+": 0.5, "Neutral": 0.0, "Mild-": -0.5, "Strong-": -1.0}

# Channel scale constants (tuned so the midpoint run is non-degenerate: a slow
# antiquity rise, a medieval plateau, a modern Western decline). Calibration then
# fits the 8 params around these. They keep conversion sub-saturating — a region's
# Christian level tracks its cumulative external push (heavy in the West, light in
# Asia) rather than every region running away to ~100%.
CONV_DRIVE = 0.16          # damping on gated internal+contact conversion
APOSTOLIC_PUSH = 0.028     # apostolic/positive-event conversion step-up per intensity
INSTITUTIONAL_PUSH = 0.022 # institutional top-down conversion step-up
INSTITUTIONAL_DIRECT = 0.02
THEO_AP = 0.10             # THEOLOGICAL -> affiliated->practicing
REVIVAL_AP = 0.16          # REVIVAL -> affiliated->practicing surge
REVIVAL_RETURN = 0.12      # REVIVAL -> lapsed->practicing return
MARTYR_SCALE = 0.15
SUPPRESS_SCALE = 0.14

# Capacity-relaxation dynamics. Conversion closes the gap to a per-region, per-time
# CAPACITY K(drive) that is a saturating function of the local Christian "drive"
# (internal prevalence + neighbor contact + strand push). This is what prevents every
# seeded region from running away to ~100%: low-drive regions (much of Asia) settle
# low, high-drive regions (the West, Latin America) settle high, and modern secular
# outflow plus a collapsing drive produce the Western decline.
# Bistable complex-contagion capacity. The drive is dominated by INTERNAL prevalence
# (so an established church self-sustains) but a region only crosses from the low state
# (~0) to the high state if it gets PUSHED past a critical mass by Christian neighbors
# and/or sustained strands. A Hill function makes the capacity sharply S-shaped: small
# drives -> small capacity (a lone mission stays a few %), large sustained drive -> high
# capacity (Europe locks in). This reproduces the historical pattern — the faith takes
# root and self-sustains where it reaches critical mass, stays a minority where it does
# not — with NO per-region constants; only geography (the contact graph) and the strands.
K_MAX = 0.97
K_HALFSAT = 0.55      # Hill half-saturation drive
K_HILL_N = 2          # Hill exponent (critical-mass threshold: strongly & durably driven
                      # regions cross into the high self-sustaining state, isolated ones
                      # stay a minority). A symmetric 8-global-parameter model cannot
                      # perfectly separate every region (e.g. settler-colonial vs
                      # mission-field Christianization); residuals are reported honestly.
DRIVE_INTERNAL = 1.5  # strong: established faith self-transmits generationally
DRIVE_APOSTOLIC = 0.10     # missionaries add some capacity drive while present...
APOSTOLIC_PLANT = 0.012    # ...and directly PLANT a small church (U->A), the spark that
                           # can cross the critical-mass threshold (kept small so a lone
                           # mission field stays a minority unless reinforced)
DRIVE_INSTITUTIONAL = 1.2  # institutions AMPLIFY the existing church (× inst_factor)
INST_FACTOR_HALF = 0.12    # prevalence at which institutional effect is half-strength
CONTACT_SCALE = 1.0   # neighbor contact contribution to drive
FADE_REL = 0.30       # downward relaxation when drive is insufficient (faith fades)
RIVAL_DECAY = 0.93    # per-decade persistence of rival incumbency (slow fade)
RIVAL_GAIN = 0.9      # how strongly suppression builds durable rival incumbency
RIVAL_CAP_MAX = 0.92  # max fractional capacity reduction a rival can impose

ORIGIN_REGION = "Roman/Mediterranean"

# Static inter-region adjacency (geographic/cultural proximity), symmetric.
ADJACENCY: dict[str, list[str]] = {
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


@dataclass
class MacroConfig:
    regions: list[str] = field(default_factory=lambda: list(S.REGIONS))
    start_year: int = 30
    end_year: int = 2030
    step: int = 10
    params: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_PARAMS))
    seed: int = 1729
    data_dir: str = D.DEFAULT_DATA_DIR
    max_strands: int | None = None   # smoke test caps this
    quiet: bool = True

    @property
    def years(self) -> list[int]:
        ys = list(range(self.start_year, self.end_year + 1, self.step))
        if ys[-1] < self.end_year:
            ys.append(self.end_year)
        return ys


def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def secular_baseline(year: float) -> float:
    """Ambient modern secularizing drift: ~0 before 1700, ~1 by ~2000."""
    return _sigmoid((year - 1860.0) / 35.0)


class RegionCohort(CompatAgent):
    """A region's belief-state distribution (fractions summing to 1)."""

    def __init__(self, model, region: str):
        super().__init__(model, key=region)
        self.region = region
        self.state = {"U": 1.0, "A": 0.0, "P": 0.0, "L": 0.0, "N": 0.0}
        self.barrier_reduction = 0.0  # durable, from TRANSLATION strands

    @property
    def prevalence(self) -> float:
        return self.state["A"] + self.state["P"]

    def normalize(self) -> None:
        for k in BELIEF_STATES:
            if self.state[k] < 0:
                self.state[k] = 0.0
        tot = sum(self.state.values())
        if tot <= 0:
            self.state = {"U": 1.0, "A": 0.0, "P": 0.0, "L": 0.0, "N": 0.0}
        else:
            for k in BELIEF_STATES:
                self.state[k] /= tot


class MacroModel(mesa.Model):
    def __init__(self, config: MacroConfig | None = None):
        super().__init__()
        self.config = config or MacroConfig()
        setup_schedule(self)
        seed_model(self, self.config.seed)

        self.regions = list(self.config.regions)
        self.region_set = set(self.regions)
        self.params = dict(DEFAULT_PARAMS)
        self.params.update(self.config.params)

        # Data.
        self.anchors = D.load_anchors(self.config.data_dir)
        self.events = D.load_events(self.config.data_dir)
        strands = D.load_strands(self.config.data_dir)
        if self.config.max_strands is not None:
            # Keep SEED + highest-tier/strength first so the smoke slice is meaningful.
            strands = sorted(strands, key=lambda s: (s.mechanism_template != "SEED",
                                                     TIER_WEIGHT.get(s.depth_tier, 0.3) * -1,
                                                     -s.strength))[: self.config.max_strands]
        self.strands = strands

        # Cohort agents.
        self.cohorts: dict[str, RegionCohort] = {}
        for r in self.regions:
            c = RegionCohort(self, r)
            register_agent(self, c)
            self.cohorts[r] = c

        # Precompute the per-step driver schedule (independent of the 8 params).
        self.years = self.config.years
        self._build_schedule()

        # History: region -> state-key -> list over years; plus pct/counts.
        self.history: dict[str, dict[str, list[float]]] = {
            r: {k: [] for k in BELIEF_STATES} for r in self.regions
        }
        self.tick = 0

    # -- schedule precompute ---------------------------------------------------------
    def _step_overlaps(self, ws, we, y0, y1) -> bool:
        if ws is None or we is None:
            return False
        return not (we < y0 or ws >= y1)

    def _ramp(self, ws, we, ymid) -> float:
        if we is None or ws is None:
            return 1.0
        if we <= ws:
            return 1.0
        return max(0.0, min(1.0, (ymid - ws) / (we - ws)))

    def _event_range(self, ev) -> tuple[float, float]:
        """Parse a year range from an event's display `year` text (e.g. "634–750",
        "1792–1910", "1960–present"). Falls back to year_sort ± one step."""
        import re as _re
        text = (ev.year_text or "").replace("–", "-").replace("—", "-")
        nums = _re.findall(r"-?\d{1,4}", text)
        if "present" in text.lower() and nums:
            return float(nums[0]), float(self.config.end_year)
        if len(nums) >= 2:
            a, b = float(nums[0]), float(nums[1])
            if b >= a:
                return a, b
        return ev.year_sort - self.config.step, ev.year_sort + self.config.step

    def _build_schedule(self) -> None:
        n = len(self.years)
        step = self.config.step
        empty = lambda: {r: 0.0 for r in self.regions}
        self.sched = [{
            "conv_seed": empty(), "institutional": empty(), "institutional_global": empty(),
            "theological": empty(), "translation": empty(), "revival": empty(),
            "martyrdom": empty(), "suppression": empty(), "secular": empty(),
            "seed": empty(), "contact": {},
        } for _ in range(n)]

        for idx, y in enumerate(self.years):
            y0, y1 = y, y + step
            ymid = y + step / 2.0
            slot = self.sched[idx]

            # --- strands ---
            for st in self.strands:
                if not self._step_overlaps(st.effect_window_start, st.effect_window_end, y0, y1):
                    # MARTYRDOM/short windows handled via overlap above; nothing here.
                    continue
                # SEED instantiates the ORIGIN only (Jesus' regions_affected is GLOBAL
                # for the other mechanisms' sake, but the seed is anchored at AD 30 in
                # Roman/Mediterranean — the spread outward is carried by apostolic
                # strands and inter-region contact, not by SEED itself).
                if st.mechanism_template == "SEED":
                    regions = [ORIGIN_REGION] if ORIGIN_REGION in self.region_set else (
                        [self.regions[0]] if self.regions else [])
                else:
                    regions = [r for r in st.expanded_regions() if r in self.region_set]
                if not regions:
                    continue
                base = TIER_WEIGHT.get(st.depth_tier, 0.3) * (st.strength / 5.0)
                ramp = self._ramp(st.effect_window_start, st.effect_window_end, ymid)
                inten = base * (0.35 + 0.65 * ramp)
                mt = st.mechanism_template
                for r in regions:
                    if mt == "SEED":
                        slot["seed"][r] += base
                    elif mt == "APOSTOLIC_PROPAGATION":
                        slot["conv_seed"][r] += inten
                    elif mt == "INSTITUTIONAL":
                        # GLOBAL institutional figures (John Paul II, Mother Teresa,
                        # Ignatius) work through the EXISTING church -> amplify channel
                        # (modulated by prevalence). Regionally-targeted rulers
                        # (Constantine, Vladimir, Charlemagne) impose top-down on their
                        # realm -> full channel (works even at ~0 prevalence).
                        is_global = ("GLOBAL" in st.regions_affected) or len(regions) >= 8
                        if is_global:
                            slot["institutional_global"][r] += inten
                        else:
                            slot["institutional"][r] += inten
                            slot["conv_seed"][r] += 0.4 * inten
                    elif mt == "THEOLOGICAL":
                        slot["theological"][r] += inten
                    elif mt == "TRANSLATION":
                        slot["translation"][r] += inten
                        slot["theological"][r] += 0.3 * inten
                    elif mt == "REVIVAL":
                        slot["revival"][r] += inten
                    elif mt == "MARTYRDOM":
                        # Short sharp local amplification near death_year in primary_region.
                        prim = [p for p in (st.primary_region or regions) if p in self.region_set] or regions
                        for pr in prim:
                            slot["martyrdom"][pr] += base
                    elif mt == "SUPPRESSION":
                        slot["suppression"][r] += inten

            # --- events ---
            for ev in self.events:
                ev_regions = [r for r in S.expand_regions_affected(ev.regions) if r in self.region_set]
                rs, re = self._event_range(ev)        # multi-year events span many steps
                near = not (re < y0 or rs >= y1) or abs(ev.year_sort - ymid) <= step
                sign = EFFECT_SIGN.get(ev.effect, 0.0)
                # Contact edges among all region pairs in the event, active near it.
                if near and len(ev_regions) >= 2:
                    w = 0.5 + 0.5 * abs(sign)
                    for i in range(len(ev_regions)):
                        for j in range(i + 1, len(ev_regions)):
                            key = tuple(sorted((ev_regions[i], ev_regions[j])))
                            slot["contact"][key] = slot["contact"].get(key, 0.0) + w
                # Ambient pressure / boosts in the event's regions.
                if near:
                    for r in ev_regions:
                        if ev.mechanism == "secularization":
                            slot["secular"][r] += 0.6 * max(0.0, -sign) + 0.2
                        elif ev.mechanism == "persecution":
                            slot["suppression"][r] += 0.5 * max(0.0, -sign)
                        elif ev.mechanism in ("conversion",):
                            slot["conv_seed"][r] += 0.12 * max(0.0, sign)
                        elif ev.mechanism == "revival":
                            slot["revival"][r] += 0.25 * max(0.0, sign)
                        elif ev.mechanism == "translation":
                            slot["translation"][r] += 0.2 * max(0.0, sign)
                        elif ev.mechanism == "schism":
                            slot["secular"][r] += 0.1 * max(0.0, -sign)

        # Durable barrier reduction from TRANSLATION: cumulative across steps.
        cum = {r: 0.0 for r in self.regions}
        self.durable_barrier = []
        for idx in range(n):
            for r in self.regions:
                cum[r] = max(cum[r], self.sched[idx]["translation"][r])
            self.durable_barrier.append(dict(cum))

        # Durable RIVAL incumbency: suppression/persecution by a competing faith or
        # ideology (Islam in MENA from ~700; Soviet atheism in Eastern Europe 1917-91)
        # persistently lowers Christian capacity and decays only slowly. Combined with
        # bistability, a region pushed below critical mass stays low even after the
        # rival fades — the historical pattern of the Christian East becoming Muslim.
        rival = {r: 0.0 for r in self.regions}
        self.durable_rival = []
        for idx in range(n):
            for r in self.regions:
                rival[r] = RIVAL_DECAY * rival[r] + RIVAL_GAIN * self.sched[idx]["suppression"][r]
            self.durable_rival.append(dict(rival))

    # -- neighbor pull ---------------------------------------------------------------
    def _inter_region_pull(self, region: str, idx: int) -> float:
        decay = self.params["inter_region_decay"]
        weights: dict[str, float] = {}
        for n in ADJACENCY.get(region, []):
            if n in self.region_set:
                weights[n] = weights.get(n, 0.0) + 1.0
        for (a, b), w in self.sched[idx]["contact"].items():
            if a == region and b in self.region_set:
                weights[b] = weights.get(b, 0.0) + w
            elif b == region and a in self.region_set:
                weights[a] = weights.get(a, 0.0) + w
        if not weights:
            return 0.0
        total_w = sum(weights.values())
        pull = sum(w * self.cohorts[n].prevalence for n, w in weights.items()) / total_w
        return (1.0 - decay) * pull

    # -- one decadal step ------------------------------------------------------------
    def step(self) -> None:
        idx = self.tick
        if idx >= len(self.years):
            return
        y = self.years[idx]
        p = self.params
        slot = self.sched[idx]

        # Record current state BEFORE updating (state at year y).
        for r in self.regions:
            c = self.cohorts[r]
            for k in BELIEF_STATES:
                self.history[r][k].append(c.state[k])

        # Compute next state for every region from current states (synchronous).
        new_states: dict[str, dict[str, float]] = {}
        for r in self.regions:
            c = self.cohorts[r]
            st = dict(c.state)
            U, A, P, L, N = (st["U"], st["A"], st["P"], st["L"], st["N"])

            # One-time SEED ignition.
            seed_amt = slot["seed"][r]
            if seed_amt > 0 and (A + P) < 1e-6:
                ignite = min(U, 0.002 * seed_amt + 0.0008)
                U -= ignite
                A += ignite * 0.6
                P += ignite * 0.4

            prevalence = A + P
            external = self._inter_region_pull(r, idx)   # neighbor spread via contact

            # Martyrdom: short sharp LOCAL amplification (blood as seed).
            mart = 1.0 + p["martyrdom_amplification"] * slot["martyrdom"][r] * MARTYR_SCALE

            # --- Christian "drive": internal complex contagion + neighbors + strands.
            # Internal weight is deliberately weak so a region cannot self-sustain on
            # prevalence alone; it needs ongoing strands and/or Christian neighbors.
            # APOSTOLIC drive CREATES (works in low-prevalence mission fields);
            # INSTITUTIONAL drive AMPLIFIES — it is modulated by existing prevalence, so
            # a GLOBAL institutional figure (e.g. John Paul II) strengthens the church
            # where it already exists rather than mass-converting non-Christian regions.
            inst_factor = prevalence / (prevalence + INST_FACTOR_HALF)
            drive = (DRIVE_INTERNAL * prevalence + CONTACT_SCALE * external
                     + DRIVE_APOSTOLIC * slot["conv_seed"][r]
                     + DRIVE_INSTITUTIONAL * slot["institutional"][r]
                     + DRIVE_INSTITUTIONAL * slot["institutional_global"][r] * inst_factor) * mart
            # Complex-contagion gate: TRANSLATION durably lowers the threshold/barrier.
            threshold = max(0.0, p["complex_contagion_threshold"]
                            - 0.6 * c.barrier_reduction - 0.4 * self.durable_barrier[idx][r])
            gate = _sigmoid((drive - threshold) * 12.0)
            eff = (drive * gate) ** K_HILL_N
            # Saturating, sharply S-shaped capacity (the max Christian fraction reachable
            # now). Small drives -> small capacity; large sustained drive -> high.
            capacity = K_MAX * eff / (eff + K_HALFSAT ** K_HILL_N)
            # A durable rival faith/ideology (Islam in MENA, Soviet atheism in the East)
            # claims the population niche, lowering Christian capacity for centuries.
            rival = min(RIVAL_CAP_MAX, self.durable_rival[idx][r])
            capacity *= (1.0 - rival)

            # --- Apostolic PLANTING: a missionary directly converts a small slice of the
            # Unexposed, the spark that can push a region past critical mass.
            plant = min(U, APOSTOLIC_PLANT * slot["conv_seed"][r])
            U -= plant
            A += plant
            prevalence = A + P

            # --- Bidirectional relaxation toward capacity. Above capacity, faith no
            # longer sustained by strands/neighbors fades (endogenous decline); below it,
            # conversion fills the gap. This keeps isolated mission fields low and
            # networked regions high with no per-region constants.
            gap = capacity - prevalence
            if gap >= 0:
                inflow = min(p["base_conversion_rate"] * gap, 0.6)
                pool = U + 0.5 * N + 1e-12
                f_UA = inflow * (U / pool)
                f_NA = inflow * (0.5 * N / pool)
                U -= f_UA
                N -= f_NA
                A += f_UA + f_NA
            else:
                fade = min(-gap * p["base_conversion_rate"] * FADE_REL, prevalence * 0.5)
                if prevalence > 1e-9:
                    A -= fade * (A / prevalence)
                    P -= fade * (P / prevalence)
                    L += fade

            # --- Affiliated <-> Practicing. nominal_to_practicing_ratio sets the
            # target practicing SHARE of Christians; THEOLOGICAL/REVIVAL raise it.
            prevc = A + P
            if prevc > 1e-9:
                target_p_share = min(0.95, p["nominal_to_practicing_ratio"]
                                     + 0.4 * slot["theological"][r] + 0.5 * slot["revival"][r])
                desired_P = target_p_share * prevc
                rate = min(0.6, 0.18 + REVIVAL_AP * slot["revival"][r]
                           + THEO_AP * slot["theological"][r]) * mart
                move = (desired_P - P) * rate
                move = max(-P * 0.5, min(move, A * 0.7))
                A -= move
                P += move

            # Revival also returns the Lapsed straight to Practicing (macro echo of
            # the Lyudmila arc).
            f_LP = L * min(0.015 + REVIVAL_RETURN * slot["revival"][r], 0.5)
            L -= f_LP
            P += f_LP

            # --- Secular & suppression outflow (Affiliated/Practicing -> Lapsed -> N).
            # Decline is EVENT-DRIVEN (Western secularization hits Western Europe & North
            # America; Soviet atheism hits Eastern Europe) — there is no global secular
            # baseline, so Latin America / Sub-Saharan Africa are not over-secularized
            # (they keep rising, as in the data). A faint baseline only bites once a
            # region is already strongly secularizing.
            secular = 0.04 * secular_baseline(y) + slot["secular"][r]
            suppression = p["persecution_severity"] * min(slot["suppression"][r], 4.0) * SUPPRESS_SCALE
            f_AL = A * min(p["secularization_term"] * secular + suppression, 0.7)
            f_PL = P * min(0.5 * p["secularization_term"] * secular + 0.7 * suppression, 0.6)
            A -= f_AL
            P -= f_PL
            L += f_AL + f_PL
            f_LN = L * min(0.12 + 0.5 * p["secularization_term"] * secular + 0.4 * suppression, 0.7)
            L -= f_LN
            N += f_LN

            # --- Fertility advantage: Christian cohorts grow their share slightly.
            prev2 = A + P
            fert = p["fertility_adv"] * prev2 * (1.0 - prev2)
            pool2 = U + N
            if pool2 > 1e-9 and fert > 0:
                A += fert
                U -= fert * (U / pool2)
                N -= fert * (N / pool2)

            new = {"U": U, "A": A, "P": P, "L": L, "N": N}
            # Persist durable barrier reduction from TRANSLATION.
            c._pending_barrier = max(c.barrier_reduction, slot["translation"][r])
            new_states[r] = new

        # Commit synchronously.
        for r in self.regions:
            c = self.cohorts[r]
            c.state = new_states[r]
            c.barrier_reduction = getattr(c, "_pending_barrier", c.barrier_reduction)
            c.normalize()

        self.tick += 1

    def run(self) -> "MacroModel":
        for _ in range(len(self.years)):
            self.step()
        return self

    # -- extraction ------------------------------------------------------------------
    def christian_pct_series(self, region: str) -> list[float]:
        h = self.history[region]
        return [100.0 * (a + pp) for a, pp in zip(h["A"], h["P"])]

    def practicing_pct_series(self, region: str) -> list[float]:
        return [100.0 * v for v in self.history[region]["P"]]

    def simulated_pct_at(self, region: str, year: int) -> float | None:
        """Christian% for a region interpolated to an arbitrary year."""
        if region not in self.history:
            return None
        series = self.christian_pct_series(region)
        pts = list(zip(self.years, series))
        return D._interp(pts, year)
