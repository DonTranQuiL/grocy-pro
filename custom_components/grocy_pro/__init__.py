"""Grocy Pro: Grocy for Home Assistant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILENAME, CARD_URL, DOMAIN, LOGGER, PLATFORMS, VERSION
from .coordinator import GrocyConfigEntry, GrocyDataUpdateCoordinator
from .grocy_data import GrocyPictureView
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services, the picture proxy and the dashboard card once."""
    async_setup_services(hass)
    hass.http.register_view(GrocyPictureView(hass))

    card = Path(__file__).parent / "frontend" / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), True)]
    )
    if "frontend" in hass.config.components:
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    else:  # pragma: no cover - frontend is always loaded in a real install
        LOGGER.debug("Frontend not loaded, the Grocy card is not registered")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GrocyConfigEntry) -> bool:
    """Set up Grocy Pro from a config entry."""
    coordinator = GrocyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrocyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
