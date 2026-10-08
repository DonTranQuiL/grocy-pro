"""Config flow: manual setup, legacy import, reauth and reconfigure."""

from __future__ import annotations

import pytest
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy_pro.const import DOMAIN, LEGACY_DOMAIN

from .conftest import API_URL, ENTRY_DATA, FIXTURE

INFO = FIXTURE["system/info"]
USER_INPUT = {
    "url": " http://grocy.local ",
    "api_key": " secret-key ",
    "port": 9192.0,
    "verify_ssl": False,
}


@pytest.fixture(autouse=True)
def _no_setup(monkeypatch):
    """Don't set the entry up after the flow; that's tested elsewhere."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        "custom_components.grocy_pro.async_setup_entry", AsyncMock(return_value=True)
    )


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_manual_setup(hass: HomeAssistant, aioclient_mock) -> None:
    """A working connection creates a clean entry."""
    aioclient_mock.get(f"{API_URL}/system/info", json=INFO)
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Grocy Pro"
    assert result["data"] == ENTRY_DATA
    assert isinstance(result["data"]["port"], int)
    request_headers = aioclient_mock.mock_calls[0][3]
    assert request_headers["GROCY-API-KEY"] == "secret-key"


async def test_port_in_url_wins(hass: HomeAssistant, aioclient_mock) -> None:
    """A port typed into the URL is used instead of the port field."""
    aioclient_mock.get("https://grocy.example.com:443/sub/api/system/info", json=INFO)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, "url": "https://grocy.example.com:443/sub/"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("mock_kwargs", "error"),
    [
        ({"status": 401}, "invalid_auth"),
        ({"status": 404, "text": "<html>"}, "invalid_url"),
        ({"text": "<html>not json</html>"}, "invalid_url"),
        ({"json": {"something": "else"}}, "invalid_url"),
        ({"exc": ClientError()}, "cannot_connect"),
        ({"exc": TimeoutError()}, "cannot_connect"),
    ],
)
async def test_manual_errors(
    hass: HomeAssistant, aioclient_mock, mock_kwargs, error
) -> None:
    """Connection problems show a helpful error and keep the input."""
    aioclient_mock.get(f"{API_URL}/system/info", **mock_kwargs)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_single_instance(hass: HomeAssistant, mock_entry) -> None:
    """Only one Grocy Pro entry is allowed."""
    mock_entry.add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


def _legacy(hass: HomeAssistant) -> MockConfigEntry:
    legacy = MockConfigEntry(
        domain=LEGACY_DOMAIN,
        title="Grocy",
        data={**ENTRY_DATA, "url": "http://grocy.local:9192"},
        entry_id="legacy_entry",
    )
    legacy.add_to_hass(hass)
    return legacy


async def test_legacy_import(hass: HomeAssistant, aioclient_mock) -> None:
    """The old grocy entry is moved over and removed, freeing its entity IDs."""
    aioclient_mock.get(f"{API_URL}/system/info", json=INFO)
    legacy = _legacy(hass)
    ent_reg = er.async_get(hass)
    old = ent_reg.async_get_or_create(
        "sensor",
        LEGACY_DOMAIN,
        "legacy_entry_stock",
        suggested_object_id="grocy_stock",
        config_entry=legacy,
    )
    assert old.entity_id == "sensor.grocy_stock"

    result = await _start(hass)
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["import_legacy", "manual"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "import_legacy"
    assert result["description_placeholders"] == {"url": "http://grocy.local:9192"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["api_key"] == "secret-key"
    assert hass.config_entries.async_get_entry("legacy_entry") is None
    assert ent_reg.async_get("sensor.grocy_stock") is None


async def test_legacy_import_failure_falls_back_to_form(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """If the old settings no longer work, the manual form is shown, filled in."""
    aioclient_mock.get(f"{API_URL}/system/info", status=401)
    _legacy(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "invalid_auth"}
    assert hass.config_entries.async_get_entry("legacy_entry") is not None


async def test_manual_with_legacy_suggests_values(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Choosing manual setup pre-fills the old connection settings."""
    _legacy(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["step_id"] == "manual"
    schema = result["data_schema"].schema
    suggested = {
        str(key): key.description["suggested_value"]
        for key in schema
        if key.description and "suggested_value" in key.description
    }
    assert suggested["url"] == "http://grocy.local:9192"


async def test_import_legacy_without_entry_aborts(hass: HomeAssistant) -> None:
    """The import step aborts if the old entry vanished meanwhile."""
    legacy = _legacy(hass)
    result = await _start(hass)
    await hass.config_entries.async_remove(legacy.entry_id)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_legacy_entry"


async def test_reauth(hass: HomeAssistant, aioclient_mock, mock_entry) -> None:
    """A new API key can be entered when the old one is rejected."""
    mock_entry.add_to_hass(hass)
    aioclient_mock.get(f"{API_URL}/system/info", status=401)
    result = await mock_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{API_URL}/system/info", json=INFO)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data["api_key"] == "new-key"
    assert mock_entry.data["url"] == ENTRY_DATA["url"]


async def test_reconfigure(hass: HomeAssistant, aioclient_mock, mock_entry) -> None:
    """The connection can be changed without removing the entry."""
    mock_entry.add_to_hass(hass)
    aioclient_mock.get("http://grocy2.local:80/api/system/info", exc=ClientError())
    result = await mock_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    new = {**USER_INPUT, "url": "http://grocy2.local", "port": 80}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], new)
    assert result["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    aioclient_mock.get("http://grocy2.local:80/api/system/info", json=INFO)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], new)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_entry.data["url"] == "http://grocy2.local"
    assert mock_entry.data["port"] == 80
