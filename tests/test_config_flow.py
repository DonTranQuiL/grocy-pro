import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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
    yield


@pytest.mark.asyncio
async def test_form_user_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch(
        "custom_components.grocy.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_get_session.return_value = mock_session

        with patch("custom_components.grocy.async_setup_entry", return_value=True):
            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_URL: "https://grocy.example.com",
                    CONF_API_KEY: "secret_token",
                    CONF_PORT: 9192,
                    CONF_VERIFY_SSL: False,
                },
            )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_URL] == "https://grocy.example.com"


@pytest.mark.asyncio
async def test_form_user_auth_failed(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="Unauthorized")

    with patch(
        "custom_components.grocy.config_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_get_session.return_value = mock_session

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_URL: "https://grocy.example.com", CONF_API_KEY: "wrong_token"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}
