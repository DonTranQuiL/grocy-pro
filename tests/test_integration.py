# CREATED BY DONTRANQUIL
import pytest
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.grocy.const import (
    DOMAIN,
    CONF_URL,
    CONF_API_KEY,
    CONF_PORT,
    CONF_VERIFY_SSL,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom components during testing."""
    yield


# =========================================================================
# 1. CONFIG FLOW TESTS (Using Native AIOHTTP Mocking)
# =========================================================================


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant, aioclient_mock):
    """Test successful initial config flow entry registration with mocked aiohttp auth."""
    # Mock the exact URL your _test_credentials method builds to check auth
    aioclient_mock.get(
        "https://grocy.mockserver.com:9192/api/system/info?GROCY-API-KEY=mock-secret-key",
        status=200,
        json={"grocy_version": {"Version": "3.3.2"}},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Patch BOTH setup and unload to prevent background booting
    with (
        patch("custom_components.grocy.async_setup_entry", return_value=True),
        patch("custom_components.grocy.async_unload_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://grocy.mockserver.com",
                CONF_API_KEY: "mock-secret-key",
                CONF_PORT: 9192,
                CONF_VERIFY_SSL: False,
            },
        )
        await hass.async_block_till_done()

        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Grocy"
        assert result2["data"][CONF_URL] == "https://grocy.mockserver.com"

        # THE FIX: Tell Home Assistant to delete the test entry BEFORE the patch expires
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
