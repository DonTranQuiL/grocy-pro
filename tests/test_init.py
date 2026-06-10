import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy.const import DOMAIN, PLATFORMS
from custom_components.grocy import async_setup_entry, async_unload_entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom components during testing."""
    yield


@pytest.mark.asyncio
async def test_setup_and_unload_entry(hass: HomeAssistant):
    """Test full integration loading and clean tear downs."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"url": "test", "api_key": "key", "port": 9192}
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.grocy.GrocyDataUpdateCoordinator") as mock_coord_cls,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ) as mock_forward,
        patch("custom_components.grocy.async_setup_services", return_value=True),
        patch(
            "custom_components.grocy.async_setup_endpoint_for_image_proxy",
            return_value=True,
        ),
    ):
        mock_coord = MagicMock()
        mock_coord.async_setup = AsyncMock()
        mock_coord.async_config_entry_first_refresh = AsyncMock()
        mock_coord_cls.return_value = mock_coord

        assert await async_setup_entry(hass, entry) is True
        mock_forward.assert_called_once_with(entry, PLATFORMS)
        assert DOMAIN in hass.data

        # Ensure the domain data is set properly for the unload phase
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = mock_coord

    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ) as mock_unload,
        patch("custom_components.grocy.async_unload_services", return_value=True),
    ):
        assert await async_unload_entry(hass, entry) is True
        # Ruff is happy now because we actively verify the expected call arguments here:
        mock_unload.assert_called_once_with(entry, PLATFORMS)
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_setup_entry_failure(hass: HomeAssistant):
    """Test unhandled exceptions throw ConfigEntryNotReady safely."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"url": "test", "api_key": "key", "port": 9192}
    )
    entry.add_to_hass(hass)

    with patch("custom_components.grocy.GrocyDataUpdateCoordinator") as mock_coord_cls:
        mock_coord = MagicMock()
        mock_coord.async_setup = AsyncMock(side_effect=Exception("API Down"))
        mock_coord_cls.return_value = mock_coord

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)
