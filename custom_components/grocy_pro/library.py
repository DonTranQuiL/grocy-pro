"""Check that the grocy-py library actually loaded is the one Grocy Pro needs.

`grocy-py` owns the top-level `grocy` module. Grocy 2.x (domain `grocy`) pinned
grocy-py 0.1.0. When that integration ran earlier in the same Home Assistant
process, 0.1.0 stays in memory: Home Assistant then installs the version from
our manifest on disk, but Python keeps using the old module until a restart.
This module has no Home Assistant imports so it can be checked on its own.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

# Keep in sync with manifest.json (tests/test_manifest.py checks this).
REQUIRED_GROCY_PY = "1.3.0"


def installed_grocy_py() -> str | None:
    """Return the grocy-py version installed on disk."""
    try:
        return version("grocy-py")
    except PackageNotFoundError:
        return None


def library_problem() -> dict[str, str] | None:
    """Return placeholders describing a grocy-py mismatch, or None when fine.

    grocy-py 1.x re-exports `EntityType` from the package root; 0.x doesn't.
    That tells us what is loaded in memory, which can differ from what is
    installed on disk until Home Assistant restarts.
    """
    installed = installed_grocy_py()
    grocy = sys.modules.get("grocy")
    if grocy is None:  # not imported yet: whatever is on disk gets loaded
        import grocy  # noqa: PLC0415

    loaded_ok = hasattr(grocy, "EntityType") and hasattr(grocy, "TransactionType")
    if installed == REQUIRED_GROCY_PY and loaded_ok:
        return None
    return {
        "installed": installed or "not installed",
        "loaded": "current" if loaded_ok else "an older version (0.x)",
        "required": REQUIRED_GROCY_PY,
    }
