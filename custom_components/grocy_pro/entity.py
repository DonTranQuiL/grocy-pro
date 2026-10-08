"""Base entity for Grocy Pro."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, VERSION
from .coordinator import GrocyDataUpdateCoordinator
from .helpers import as_attribute


def list_attributes(name: str) -> Callable[[list[Any]], dict[str, Any]]:
    """Build an attributes function: the items under `name` plus a count."""

    def _attributes(data: list[Any]) -> dict[str, Any]:
        items = list(data or [])
        return {name: [as_attribute(item) for item in items], "count": len(items)}

    return _attributes


@dataclass(frozen=True, kw_only=True)
class GrocyEntityDescriptionMixin:
    """Shared description fields."""

    attributes_fn: Callable[[list[Any]], Mapping[str, Any] | None] = lambda _: None


class GrocyEntity(CoordinatorEntity[GrocyDataUpdateCoordinator]):
    """Grocy base entity.

    Unique IDs keep the 2.x format ({entry_id}_{key}) and the device keeps the
    name "Grocy", so new installs get the same entity IDs (sensor.grocy_stock, ...)
    the old `grocy` domain created.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GrocyDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key.lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model="Grocy Pro",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.connection.root_url,
        )

    @property
    def _data(self) -> list[Any] | None:
        """Return this entity's slice of the coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the item list as attributes."""
        attributes_fn = getattr(self.entity_description, "attributes_fn", None)
        if attributes_fn is None or self._data is None:
            return None
        return attributes_fn(self._data)
