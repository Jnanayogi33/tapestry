"""Micro individual-agent simulation (Mesa + NetworkX) — the micro layer.

1,000-5,000 agents in one or two regions. Each agent has a STABLE innate
``religiosity_disposition`` and a ``belief_state`` that moves through
Unexposed -> Affiliated -> Practicing and back via Lapsed -> Unaffiliated. Transitions
depend on BOTH the agent's disposition AND its neighbors' states (complex contagion)
over a small social network of family / friends / rivals. A society-level secular wave
and a later revival (seeded to echo the macro layer and the lives.csv arcs) drive the
population, so individual stories like the "Lyudmila" arc — affiliated -> unbelieving
-> strongly-practicing, returning late through believing social ties — can EMERGE.

Updates are synchronous (double-buffered): each agent reads neighbors' current states,
computes its next state + the driver of any change; the model commits all at once and
appends to a per-agent state log. ``example_lives.json`` is a genuine dump of that log.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import mesa
import networkx as nx

from sim.mesa_compat import (
    CompatAgent, all_agents, register_agent, seed_model, setup_schedule, step_all,
)

STATES = ["Unexposed", "Affiliated", "Practicing", "Lapsed", "Unaffiliated"]
TIE_WEIGHT = {"family": 1.0, "friend": 0.55, "rival": -0.45}


@dataclass
class MicroConfig:
    region: str = "Eastern Europe & Russia"
    n_agents: int = 2000
    start_year: int = 1900
    end_year: int = 2025
    seed: int = 1729
    # Society timeline (echoes the macro Soviet suppression + post-Soviet revival).
    secular_start: int = 1922
    secular_end: int = 1990
    revival_start: int = 1988
    # Rates (some seeded from the calibrated macro params; see run.py).
    exposure_rate: float = 0.10
    discipleship_rate: float = 0.10
    secular_rate: float = 0.16
    return_rate: float = 0.10
    contagion_threshold: float = 0.18
    # Initial belief mix (a pre-secular, nominally-affiliated society).
    init_mix: tuple = (0.10, 0.66, 0.14, 0.05, 0.05)  # U, A, P, L, N
    quiet: bool = True

    @property
    def years(self) -> list[int]:
        return list(range(self.start_year, self.end_year + 1))


def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


class Person(CompatAgent):
    def __init__(self, model, key: int, disposition: float, state: str):
        super().__init__(model, key=key)
        self.pid = key
        self.disposition = disposition
        self.state = state
        self.next_state = state
        self.next_driver = None
        self.history: list[str] = []
        self.driver_history: list[str | None] = []
        self.field_history: list[float] = []

    # -- social field from neighbors (complex contagion) --------------------------
    def believing_field(self):
        """Return (practicing_field, affiliated_field) — tie-weighted fractions of
        neighbors who are Practicing / Affiliated, with rivals counting negative."""
        nbrs = self.model.graph[self.pid]
        if not nbrs:
            return 0.0, 0.0
        pr = aff = wsum = 0.0
        for j, attrs in nbrs.items():
            w = TIE_WEIGHT.get(attrs.get("tie", "friend"), 0.5)
            wsum += abs(w)
            s = self.model.people[j].state
            if s == "Practicing":
                pr += w
            elif s == "Affiliated":
                aff += w
        if wsum <= 0:
            return 0.0, 0.0
        return max(0.0, pr / wsum), max(0.0, aff / wsum)

    def step(self):
        m = self.model
        cfg = m.config
        d = self.disposition
        pr_field, aff_field = self.believing_field()
        self.field_history.append(pr_field + 0.5 * aff_field)
        sp = m.secular_pressure(m.year)
        rev = m.revival(m.year)
        s = self.state
        rng = m.random
        nxt, driver = s, None

        believe_field = pr_field + 0.5 * aff_field
        # Complex contagion gate: needs a critical mass of believing ties.
        gate = _sigmoid((believe_field - cfg.contagion_threshold) * 8.0)

        if s == "Unexposed":
            p = cfg.exposure_rate * (0.3 + believe_field) * (0.5 + d)
            if rng.random() < p:
                nxt, driver = "Affiliated", "met believers"
        elif s == "Affiliated":
            p_practice = cfg.discipleship_rate * gate * (0.4 + d) * (0.6 + pr_field) * (1 + 1.5 * rev)
            p_lapse = cfg.secular_rate * sp * (1.1 - d) * (1.0 - 0.7 * pr_field)
            r = rng.random()
            if r < p_practice:
                nxt, driver = "Practicing", ("believing friends" if pr_field > 0.15 else "personal conviction")
            elif r < p_practice + p_lapse:
                nxt, driver = "Lapsed", ("secular pressure" if sp > 0.3 else "drifted away")
        elif s == "Practicing":
            p_lapse = cfg.secular_rate * sp * (1.0 - d) * 0.45 * (1.0 - 0.8 * pr_field)
            if rng.random() < p_lapse:
                nxt, driver = "Lapsed", "secular pressure"
        elif s == "Lapsed":
            # THE return mechanism: believing social ties (esp. family) + disposition +
            # revival pull the lapsed back to *practicing* faith. This is the Lyudmila arc.
            p_return = cfg.return_rate * (0.25 + pr_field) * (0.2 + d) * (1 + 2.0 * rev) * gate
            p_drift = (0.04 + 0.25 * sp) * (1.0 - d) * (1.0 - pr_field)
            r = rng.random()
            if r < p_return:
                nxt = "Practicing"
                driver = "believing family" if pr_field > 0.12 else "renewed conviction"
            elif r < p_return + p_drift:
                nxt, driver = "Unaffiliated", "secular pressure"
        elif s == "Unaffiliated":
            p_back = 0.5 * cfg.return_rate * (0.15 + pr_field) * (0.2 + d) * (1 + 2.0 * rev) * gate
            if rng.random() < p_back:
                nxt, driver = "Lapsed", "believing family"
        self.next_state = nxt
        self.next_driver = driver


class MicroModel(mesa.Model):
    def __init__(self, config: MicroConfig | None = None):
        super().__init__()
        self.config = config or MicroConfig()
        setup_schedule(self)
        seed_model(self, self.config.seed)
        self.year = self.config.start_year
        self.tick = 0

        self._build_network()
        self._build_population()

    # -- network: family cliques + small-world friends + a few rivals -------------
    def _build_network(self):
        cfg = self.config
        n = cfg.n_agents
        # Small-world friendship base. Clamp k to a valid even degree (< n) so tiny
        # populations (e.g. the 5-agent smoke test) don't break watts_strogatz.
        k = min(6, n - 1)
        if k % 2 == 1:
            k -= 1
        if n >= 4 and k >= 2:
            g = nx.watts_strogatz_graph(n, k=k, p=0.15, seed=cfg.seed)
        else:
            g = nx.complete_graph(n)
        for _, _, a in g.edges(data=True):
            a["tie"] = "friend"
        # Family cliques of 3-5 consecutive agents.
        rng = __import__("random").Random(cfg.seed)
        i = 0
        while i < n:
            fam = min(rng.randint(3, 5), n - i)
            members = list(range(i, i + fam))
            for a_i in range(len(members)):
                for b_i in range(a_i + 1, len(members)):
                    g.add_edge(members[a_i], members[b_i], tie="family")
            i += fam
        # A few rivals (antagonistic ties).
        for _ in range(n // 12):
            u, v = rng.randrange(n), rng.randrange(n)
            if u != v and not g.has_edge(u, v):
                g.add_edge(u, v, tie="rival")
        self.graph = g

    def _build_population(self):
        cfg = self.config
        rng = self.random
        u, a, p, l, nn = cfg.init_mix
        cum = [u, u + a, u + a + p, u + a + p + l, 1.0]
        # Build a few "anchored faithful" with very high disposition in each family so a
        # believing tie can survive the secular era and later pull others back.
        self.people: dict[int, Person] = {}
        for pid in range(cfg.n_agents):
            # Disposition: Beta-like (skew toward lower-middle), stable for life.
            disp = (rng.betavariate(2.0, 3.0) if hasattr(rng, "betavariate")
                    else rng.random())
            r = rng.random()
            if r < cum[0]:
                s = "Unexposed"
            elif r < cum[1]:
                s = "Affiliated"
            elif r < cum[2]:
                s = "Practicing"
            elif r < cum[3]:
                s = "Lapsed"
            else:
                s = "Unaffiliated"
            # Anchor ~6% of agents as devout (high disposition, practicing) — the
            # praying-grandmother seed that keeps believing ties alive.
            if rng.random() < 0.06:
                disp = 0.85 + 0.15 * rng.random()
                s = "Practicing"
            person = Person(self, pid, disp, s)
            register_agent(self, person)
            self.people[pid] = person

    # -- society timeline --------------------------------------------------------
    def secular_pressure(self, year: float) -> float:
        cfg = self.config
        if year < cfg.secular_start:
            return 0.05
        if year <= cfg.secular_end:
            # Ramp up to a Soviet-era plateau.
            ramp = min(1.0, (year - cfg.secular_start) / 12.0)
            return 0.15 + 0.85 * ramp
        # Post-Soviet relaxation.
        return max(0.1, 1.0 - (year - cfg.secular_end) / 25.0)

    def revival(self, year: float) -> float:
        cfg = self.config
        if year < cfg.revival_start:
            return 0.0
        # A surge after the secular era that fades over ~30 years.
        return max(0.0, 1.0 - (year - cfg.revival_start) / 30.0)

    def step(self):
        # Record current state (state AT self.year) before transitioning.
        for pid, person in self.people.items():
            person.history.append(person.state)
            person.driver_history.append(person.next_driver if self.tick > 0 else "born")
        # Compute next states from current states (synchronous), then commit.
        step_all(self, "step")
        for person in self.people.values():
            person.state = person.next_state
        self.year += 1
        self.tick += 1

    def run(self) -> "MicroModel":
        for _ in range(len(self.config.years)):
            self.step()
        return self
