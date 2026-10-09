"""Grocy Pro: Grocy for Home Assistant."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILENAME, CARD_URL, DOMAIN, LOGGER, PLATFORMS, VERSION
from .coordinator import GrocyConfigEntry, GrocyDataUpdateCoordinator
from .grocy_data import GrocyPictureView
from .library import library_problem
from .repairs import async_check_old_card
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


ISSUE_RESTART = "restart_required"


def _check_library(hass: HomeAssistant) -> dict[str, str] | None:
    """Raise a repair when an old grocy-py is installed or still in memory."""
    if (problem := library_problem()) is None:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_RESTART)
        return None
    LOGGER.error(
        "Grocy Pro needs grocy-py %s, but grocy-py %s is installed and %s is "
        "loaded (left over from the old Grocy integration). Restart Home "
        "Assistant to load the right version",
        problem["required"],
        problem["installed"],
        problem["loaded"],
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_RESTART,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_RESTART,
        translation_placeholders=problem,
    )
    return problem


def _file_digest(path: Path) -> str:
    """Return a short hash of a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services, the picture proxy and the dashboard card once."""
    _check_library(hass)
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
    if (problem := _check_library(hass)) is not None:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key=ISSUE_RESTART,
            translation_placeholders=problem,
        )
    coordinator = GrocyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_at_started(hass, async_check_old_card))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrocyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
