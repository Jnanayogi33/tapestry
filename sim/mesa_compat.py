"""Mesa 2.x / 3.x compatibility shim.

The build spec forbids assuming a Mesa version in prose — we detect the installed
MAJOR version at runtime and route through the right API:

* **3.x**: agents are created with ``Agent(model)`` (auto unique_id, auto-registered
  to ``model.agents``); stepping is ``model.agents.shuffle_do("step")``; there is no
  ``mesa.time``.
* **2.x**: agents are created with ``Agent(unique_id, model)`` and added to a
  ``mesa.time`` scheduler (``model.schedule``); stepping is ``model.schedule.step()``.

All sim code subclasses :class:`CompatAgent` and uses the module helpers so the same
source runs on either major version.
"""
from __future__ import annotations

import itertools
from typing import Iterable

import mesa


def detect_major() -> int:
    import importlib

    v = getattr(mesa, "__version__", None)
    if isinstance(v, str):
        try:
            return int(v.split(".")[0])
        except ValueError:
            pass
    # Capability sniff: mesa.time only exists in 2.x.
    try:
        importlib.import_module("mesa.time")
        return 2
    except Exception:
        return 3


MESA_MAJOR: int = detect_major()


class CompatAgent(mesa.Agent):
    """Base agent that hides the 2.x-vs-3.x constructor difference.

    Subclasses call ``super().__init__(model, key=...)``. ``key`` is our own stable
    semantic identifier (e.g. a region name or a person index); Mesa's ``unique_id``
    is left to Mesa where it manages it (3.x) and is synthesized where it doesn't
    (2.x).
    """

    def __init__(self, model, key=None):
        if MESA_MAJOR >= 3:
            super().__init__(model)
        else:
            uid = getattr(model, "_compat_uid", None)
            if uid is None:
                uid = itertools.count()
                model._compat_uid = uid
            super().__init__(next(uid), model)
        self.key = key


def setup_schedule(model) -> None:
    """Call inside ``Model.__init__`` *after* ``super().__init__()``.

    On 2.x this creates a ``RandomActivation`` scheduler. On 3.x it is a no-op
    (``model.agents`` is managed by Mesa).
    """
    if MESA_MAJOR < 3:
        import mesa.time

        model.schedule = mesa.time.RandomActivation(model)


def register_agent(model, agent) -> None:
    """Register a freshly-created agent. No-op on 3.x (auto-registered)."""
    if MESA_MAJOR < 3:
        model.schedule.add(agent)


def step_all(model, method: str = "step", shuffle: bool = True) -> None:
    """Step every agent once, calling ``method`` on each."""
    if MESA_MAJOR >= 3:
        if shuffle:
            model.agents.shuffle_do(method)
        else:
            model.agents.do(method)
    else:
        # 2.x RandomActivation only steps "step"; for other methods, iterate.
        if method == "step":
            model.schedule.step()
        else:
            for a in list(model.schedule.agents):
                getattr(a, method)()


def all_agents(model) -> list:
    """Return a list of all agents, version-agnostically."""
    if MESA_MAJOR >= 3:
        return list(model.agents)
    return list(model.schedule.agents)


def agents_of_type(model, klass) -> list:
    """Return all agents that are instances of ``klass``."""
    return [a for a in all_agents(model) if isinstance(a, klass)]


def seed_model(model, seed: int) -> None:
    """Seed the model RNG identically across versions (fixed-seed reproducibility)."""
    import random

    model.random = random.Random(seed)
    # Some Mesa versions also expose a numpy Generator as ``model.rng``.
    try:
        import numpy as np

        model.rng = np.random.default_rng(seed)
    except Exception:
        pass


__all__ = [
    "MESA_MAJOR",
    "CompatAgent",
    "setup_schedule",
    "register_agent",
    "step_all",
    "all_agents",
    "agents_of_type",
    "seed_model",
    "detect_major",
]
