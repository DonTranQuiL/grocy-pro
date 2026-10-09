"""Grocy Pro: Grocy for Home Assistant."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILENAME, CARD_URL, DOMAIN, LOGGER, PLATFORMS, VERSION
from .coordinator import GrocyConfigEntry, GrocyDataUpdateCoordinator
from .grocy_data import GrocyPictureView
from .repairs import async_check_old_card
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _file_digest(path: Path) -> str:
    """Return a short hash of a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services, the picture proxy and the dashboard card once."""
    # 3.0.1 raised this repair; it no longer applies.
    ir.async_delete_issue(hass, DOMAIN, "restart_required")
    async_setup_services(hass)
    hass.http.register_view(GrocyPictureView(hass))

    card = Path(__file__).parent / "frontend" / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), True)]
    )
    if "frontend" in hass.config.components:
        # Version plus a content hash, so browsers pick up every card change.
        digest = await hass.async_add_executor_job(_file_digest, card)
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}-{digest}")
    else:  # pragma: no cover - frontend is always loaded in a real install
        LOGGER.debug("Frontend not loaded, the Grocy card is not registered")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GrocyConfigEntry) -> bool:
    """Set up Grocy Pro from a config entry."""
    coordinator = GrocyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_at_started(hass, async_check_old_card))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrocyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
