"""Warn about a leftover copy of the old dashboard card."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CARD_FILENAME, DOMAIN, LOGGER

ISSUE_OLD_CARD = "old_card"


def _old_card_file(hass: HomeAssistant) -> str | None:
    """Return the path of an old copy of the card in /config/www, if any."""
    path = Path(hass.config.path("www", CARD_FILENAME))
    return f"/config/www/{CARD_FILENAME}" if path.is_file() else None


async def _old_card_resources(hass: HomeAssistant) -> list[str]:
    """Return dashboard resources that load another copy of the card."""
    lovelace: Any = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return []
    try:
        await resources.async_get_info()  # loads storage-mode resources
        items = resources.async_items() or []
    except Exception as err:  # internal API, never let it break setup
        LOGGER.debug("Could not read dashboard resources: %s", err)
        return []
    return [
        str(item.get("url", ""))
        for item in items
        if CARD_FILENAME in str(item.get("url", ""))
    ]


async def async_check_old_card(hass: HomeAssistant) -> None:
    """Create (or clear) a repair issue for an old card resource or file.

    2.x asked users to copy the card to /config/www and add it as a dashboard
    resource. That copy is defined first and wins over the card bundled with
    the integration, so the user keeps seeing the old card and its bugs.
    """
    found = await _old_card_resources(hass)
    if old_file := await hass.async_add_executor_job(_old_card_file, hass):
        found.append(old_file)
    if not found:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_OLD_CARD)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_OLD_CARD,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_OLD_CARD,
        translation_placeholders={"found": ", ".join(sorted(set(found)))},
    )
