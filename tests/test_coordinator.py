import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy.const import DOMAIN, CONF_URL, CONF_API_KEY, CONF_PORT
from custom_components.grocy.coordinator import GrocyDataUpdateCoordinator


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.mark.asyncio
async def test_coordinator_successful_setup(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_URL: "http://test", CONF_API_KEY: "key", CONF_PORT: 9192},
    )

    with patch("custom_components.grocy.coordinator.GrocyData") as mock_grocy_data:
        mock_data_inst = MagicMock()
        mock_config = MagicMock()
        mock_config.enabled_features = ["FEATURE_FLAG_STOCK"]
        mock_data_inst.async_get_config = AsyncMock(return_value=mock_config)
        mock_data_inst.async_update_data = AsyncMock(return_value={"some": "data"})
        mock_grocy_data.return_value = mock_data_inst

        # FIX: Initialize the coordinator inside the patch block!
        coord = GrocyDataUpdateCoordinator(hass, entry)
        await coord.async_setup()
        assert "stock" in coord.available_entities

        result = await coord._async_update_data()
        assert "stock" in result


@pytest.mark.asyncio
async def test_coordinator_update_failed(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_URL: "http://test", CONF_API_KEY: "key", CONF_PORT: 9192},
    )

    with patch("custom_components.grocy.coordinator.GrocyData") as mock_grocy_data:
        mock_data_inst = MagicMock()
        mock_data_inst.async_update_data.side_effect = Exception("API Error")
        mock_grocy_data.return_value = mock_data_inst

        coord = GrocyDataUpdateCoordinator(hass, entry)
        coord.available_entities = ["stock"]

        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
