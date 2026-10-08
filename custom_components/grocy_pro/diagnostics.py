"""Diagnostics for Grocy Pro."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_URL
from .coordinator import GrocyConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_URL}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GrocyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with the API key and URL redacted."""
    coordinator = entry.runtime_data
    stats = asdict(coordinator.stats)
    for key in ("last_full_refresh", "last_db_changed"):
        if stats[key] is not None:
            stats[key] = stats[key].isoformat()
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "available_entities": coordinator.available_entities,
        "stats": stats,
        "counts": {
            key: len(value or []) for key, value in (coordinator.data or {}).items()
        },
        "last_update_success": coordinator.last_update_success,
    }
