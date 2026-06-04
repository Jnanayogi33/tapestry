"""Import smoke test. Prints the resolved version of every core dependency and
detects the installed Mesa MAJOR version at runtime (the model code branches on
this — we never assume a Mesa version in prose). Exit non-zero only if a core
package cannot be imported at all.

Run: python pipeline/smoke_imports.py
"""
from __future__ import annotations

import importlib
import sys

# (import name, friendly label). pandas/numpy/scipy/networkx are hard requirements;
# mesa is required for the sim; notion-client is optional (sync only).
CORE = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("scipy", "scipy"),
    ("networkx", "networkx"),
    ("mesa", "mesa"),
]
OPTIONAL = [
    ("notion_client", "notion-client"),
]


def _version(mod) -> str:
    for attr in ("__version__", "version", "VERSION"):
        v = getattr(mod, attr, None)
        if isinstance(v, str):
            return v
    return "unknown"


def detect_mesa_major() -> int | None:
    """Return the Mesa MAJOR version (2 or 3), or None if Mesa is unavailable.

    We sniff capabilities rather than trust the string: Mesa 3.x exposes
    ``model.agents`` / ``AgentSet`` and drops ``mesa.time``; Mesa 2.x has
    ``mesa.time`` schedulers and ``model.schedule``.
    """
    try:
        mesa = importlib.import_module("mesa")
    except Exception:
        return None
    ver = _version(mesa)
    if ver and ver != "unknown":
        try:
            return int(ver.split(".")[0])
        except ValueError:
            pass
    # Capability sniff fallback.
    try:
        importlib.import_module("mesa.time")
        return 2
    except Exception:
        return 3


def main() -> int:
    ok = True
    print("=== Tapestry import smoke test ===")
    print(f"python {sys.version.split()[0]}")
    for import_name, label in CORE:
        try:
            mod = importlib.import_module(import_name)
            print(f"  [ok]   {label:14s} {_version(mod)}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"  [FAIL] {label:14s} {exc}")
    for import_name, label in OPTIONAL:
        try:
            mod = importlib.import_module(import_name)
            print(f"  [ok]   {label:14s} {_version(mod)} (optional)")
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] {label:14s} not installed (optional): {exc}")

    major = detect_mesa_major()
    print(f"  Mesa MAJOR version detected: {major}")
    if major not in (2, 3):
        print("  [FAIL] Could not determine a usable Mesa major version.")
        ok = False

    print("=== smoke", "OK" if ok else "FAILED", "===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
