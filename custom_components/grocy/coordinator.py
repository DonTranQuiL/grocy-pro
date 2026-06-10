"""Data update coordinator for Grocy."""

from __future__ import annotations

from typing import Any
from grocy.grocy import Grocy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_BATTERIES,
    ATTR_CHORES,
    ATTR_EXPIRED_PRODUCTS,
    ATTR_EXPIRING_PRODUCTS,
    ATTR_MEAL_PLAN,
    ATTR_MISSING_PRODUCTS,
    ATTR_OVERDUE_BATTERIES,
    ATTR_OVERDUE_CHORES,
    ATTR_OVERDUE_PRODUCTS,
    ATTR_OVERDUE_TASKS,
    ATTR_SHOPPING_LIST,
    ATTR_STOCK,
    ATTR_TASKS,
    CONF_API_KEY,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL,
)
from .grocy_data import GrocyData
from .helpers import extract_base_url_and_path


class GrocyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Grocy data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.config_entry = entry

        url = entry.data[CONF_URL]
        api_key = entry.data[CONF_API_KEY]
        port = entry.data.get(CONF_PORT, 9192)
        verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)

        base_url, path = extract_base_url_and_path(url)

        self.grocy_api = Grocy(
            base_url, api_key, path=path, port=port, verify_ssl=verify_ssl
        )
        self.grocy_data = GrocyData(hass, self.grocy_api)
        self.available_entities: list[str] = []
        self.entities = []

    async def async_setup(self) -> None:
        """Perform initial setup and feature flag fetching."""
        self.available_entities = await self._async_get_available_entities()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Grocy."""
        data: dict[str, Any] = {}

        for entity_key in self.available_entities:
            try:
                data[entity_key] = await self.grocy_data.async_update_data(entity_key)
            except Exception as error:
                raise UpdateFailed(
                    f"Update failed for {entity_key}: {error}"
                ) from error

        return data

    async def _async_get_available_entities(self) -> list[str]:
        """Return a list of available entities based on enabled Grocy features."""
        available_entities = []
        grocy_config = await self.grocy_data.async_get_config()

        if grocy_config:
            features = grocy_config.enabled_features

            if "FEATURE_FLAG_STOCK" in features:
                available_entities.extend(
                    [
                        ATTR_STOCK,
                        ATTR_MISSING_PRODUCTS,
                        ATTR_EXPIRED_PRODUCTS,
                        ATTR_EXPIRING_PRODUCTS,
                        ATTR_OVERDUE_PRODUCTS,
                    ]
                )
            if "FEATURE_FLAG_SHOPPINGLIST" in features:
                available_entities.append(ATTR_SHOPPING_LIST)
            if "FEATURE_FLAG_TASKS" in features:
                available_entities.extend([ATTR_TASKS, ATTR_OVERDUE_TASKS])
            if "FEATURE_FLAG_CHORES" in features:
                available_entities.extend([ATTR_CHORES, ATTR_OVERDUE_CHORES])
            if "FEATURE_FLAG_RECIPES" in features:
                available_entities.append(ATTR_MEAL_PLAN)
            if "FEATURE_FLAG_BATTERIES" in features:
                available_entities.extend([ATTR_BATTERIES, ATTR_OVERDUE_BATTERIES])

        return available_entities
