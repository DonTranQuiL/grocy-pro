"""Setup, entities, unload and diagnostics."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.grocy_pro.const import CARD_URL, DOMAIN
from custom_components.grocy_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.grocy_pro.services import SCHEMAS

EXPECTED_STATES = {
    "sensor.grocy_stock": "22",
    "sensor.grocy_chores": "6",
    "sensor.grocy_tasks": "5",
    "sensor.grocy_shopping_list": "2",
    "sensor.grocy_batteries": "4",
    "sensor.grocy_meal_plan": "5",
    "binary_sensor.grocy_expiring_products": "on",
    "binary_sensor.grocy_overdue_products": "on",
    "binary_sensor.grocy_expired_products": "off",
    "binary_sensor.grocy_missing_products": "on",
    "binary_sensor.grocy_overdue_tasks": "on",
    "binary_sensor.grocy_overdue_chores": "off",
    "binary_sensor.grocy_overdue_batteries": "on",
    "todo.grocy_shopping_list": "1",  # one item is already done
}


async def test_setup_creates_entities(hass: HomeAssistant, setup_integration) -> None:
    """All entities are created with the old sensor.grocy_* entity IDs."""
    entry = await setup_integration()
    assert entry.state is ConfigEntryState.LOADED

    for entity_id, state in EXPECTED_STATES.items():
        assert hass.states.get(entity_id) is not None, entity_id
        assert hass.states.get(entity_id).state == state, entity_id

    assert hass.states.get("calendar.grocy_calendar") is not None

    stock = hass.states.get("sensor.grocy_stock")
    assert stock.attributes["count"] == 22
    first = stock.attributes["products"][0]
    assert {"id", "name", "available_amount", "picture_url"} <= set(first)
    pictures = [p["picture_url"] for p in stock.attributes["products"]]
    assert any(
        url and url.startswith("/api/grocy_pro/productpictures/") for url in pictures
    )

    chores = hass.states.get("sensor.grocy_chores").attributes["chores"]
    assert all(chore["name"] for chore in chores)

    meals = hass.states.get("sensor.grocy_meal_plan").attributes["meals"]
    assert meals and any(
        (m["picture_url"] or "").startswith("/api/grocy_pro/recipepictures/")
        for m in meals
    )

    overdue = hass.states.get("binary_sensor.grocy_overdue_batteries")
    assert [b["name"] for b in overdue.attributes["overdue_batteries"]] == ["Battery3"]

    ent_reg = er.async_get(hass)
    reg = ent_reg.async_get("sensor.grocy_stock")
    assert reg.unique_id == f"{entry.entry_id}_stock"
    assert reg.platform == DOMAIN

    device = dr.async_get(hass).async_get(reg.device_id)
    assert (DOMAIN, entry.entry_id) in device.identifiers
    assert device.name == "Grocy"
    assert device.configuration_url == "http://grocy.local:9192"


async def test_services_and_card_registered(
    hass: HomeAssistant, setup_integration
) -> None:
    """Services are registered once and the card is served."""
    await setup_integration()
    assert set(hass.services.async_services()[DOMAIN]) == set(SCHEMAS)
    assert "grocy" not in hass.services.async_services()
    resources = [r.canonical for r in hass.http.app.router.resources()]
    assert CARD_URL in resources


async def test_unload_and_reload(hass: HomeAssistant, setup_integration) -> None:
    """The entry unloads and reloads cleanly (no duplicate registrations)."""
    entry = await setup_integration()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_unreachable(
    hass: HomeAssistant, mock_entry, grocy_server
) -> None:
    """A connection error makes Home Assistant retry later."""
    import requests

    grocy_server.fail = requests.ConnectionError("refused")
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_auth_failure_starts_reauth(
    hass: HomeAssistant, mock_entry, grocy_server
) -> None:
    """A rejected API key starts a reauth flow."""
    grocy_server.fail = 401
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_features_limit_entities(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Disabled Grocy features don't create entities."""
    config = grocy_server.routes["system/config"]
    config["FEATURE_FLAG_BATTERIES"] = False
    config["FEATURE_FLAG_CALENDAR"] = False
    config["FEATURE_FLAG_SHOPPINGLIST"] = False
    await setup_integration()
    assert hass.states.get("sensor.grocy_batteries") is None
    assert hass.states.get("calendar.grocy_calendar") is None
    assert hass.states.get("todo.grocy_shopping_list") is None
    assert hass.states.get("sensor.grocy_stock") is not None
    assert not any(path.startswith("batteries") for _, path, _ in grocy_server.calls)


async def test_diagnostics_redacts(hass: HomeAssistant, setup_integration) -> None:
    """Diagnostics never contain the API key or URL."""
    entry = await setup_integration()
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["api_key"] == "**REDACTED**"
    assert diag["entry"]["url"] == "**REDACTED**"
    assert diag["counts"]["stock"] == 22
    assert diag["stats"]["full_refreshes"] == 1
    assert "secret-key" not in str(diag)


async def test_requests_get_a_timeout(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """grocy-py calls are made with a timeout."""
    await setup_integration()
    assert grocy_server.timeouts
    assert all(t == 20 for t in grocy_server.timeouts)
