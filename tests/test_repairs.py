"""Tests for the leftover-card repair issue."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.grocy_pro.const import DOMAIN
from custom_components.grocy_pro.repairs import ISSUE_OLD_CARD, async_check_old_card


class FakeResources:
    """Stand-in for the Lovelace resource collection."""

    def __init__(self, items: list[dict[str, Any]], fail: bool = False) -> None:
        self.items = items
        self.fail = fail

    async def async_get_info(self) -> dict:
        if self.fail:
            raise RuntimeError("storage not ready")
        return {}

    def async_items(self) -> list[dict[str, Any]]:
        return self.items


class FakeLovelace:
    def __init__(self, resources: FakeResources) -> None:
        self.resources = resources


async def test_no_old_card(hass: HomeAssistant, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    await async_check_old_card(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_OLD_CARD) is None


async def test_old_resource_and_file(hass: HomeAssistant, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "www").mkdir()
    (tmp_path / "www" / "grocy-action-card.js").write_text("old")
    hass.data["lovelace"] = FakeLovelace(
        FakeResources(
            [
                {"url": "/local/grocy-action-card.js?v=2", "type": "module"},
                {"url": "/hacsfiles/other-card.js", "type": "module"},
            ]
        )
    )
    await async_check_old_card(hass)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_OLD_CARD)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {
        "found": "/config/www/grocy-action-card.js, /local/grocy-action-card.js?v=2"
    }

    # Cleaned up: the issue goes away.
    (tmp_path / "www" / "grocy-action-card.js").unlink()
    hass.data["lovelace"].resources.items = []
    await async_check_old_card(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_OLD_CARD) is None


async def test_resources_unreadable(hass: HomeAssistant, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    hass.data["lovelace"] = FakeLovelace(FakeResources([], fail=True))
    await async_check_old_card(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_OLD_CARD) is None
