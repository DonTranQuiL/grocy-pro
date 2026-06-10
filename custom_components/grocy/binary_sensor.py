"""Binary sensor platform for Grocy."""

from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_EXPIRED_PRODUCTS,
    ATTR_EXPIRING_PRODUCTS,
    ATTR_MISSING_PRODUCTS,
    ATTR_OVERDUE_BATTERIES,
    ATTR_OVERDUE_CHORES,
    ATTR_OVERDUE_PRODUCTS,
    ATTR_OVERDUE_TASKS,
    DOMAIN,
    LOGGER,
)
from .coordinator import GrocyDataUpdateCoordinator
from .entity import GrocyEntity


def _as_dict(obj: Any) -> dict[str, Any]:
    """Safely convert any Grocy object to a dictionary and serialize dates."""
    if hasattr(obj, "as_dict"):
        data = obj.as_dict()
    elif hasattr(obj, "model_dump"):
        data = obj.model_dump()
    elif hasattr(obj, "dict"):
        data = obj.dict()
    else:
        data = vars(obj)

    return {
        k: v.isoformat() if isinstance(v, (datetime.date, datetime.time)) else v
        for k, v in data.items()
    }


@dataclass
class GrocyBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Grocy binary sensor entity description."""

    attributes_fn: Callable[[list[Any]], Mapping[str, Any] | None] = lambda _: None


BINARY_SENSORS: tuple[GrocyBinarySensorEntityDescription, ...] = (
    GrocyBinarySensorEntityDescription(
        key=ATTR_EXPIRED_PRODUCTS,
        name="Expired products",
        icon="mdi:delete-alert-outline",
        attributes_fn=lambda data: {
            "expired_products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_EXPIRING_PRODUCTS,
        name="Expiring products",
        icon="mdi:clock-fast",
        attributes_fn=lambda data: {
            "expiring_products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_PRODUCTS,
        name="Overdue products",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=lambda data: {
            "overdue_products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_MISSING_PRODUCTS,
        name="Missing products",
        icon="mdi:flask-round-bottom-empty-outline",
        attributes_fn=lambda data: {
            "missing_products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_CHORES,
        name="Overdue chores",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=lambda data: {
            "overdue_chores": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_TASKS,
        name="Overdue tasks",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=lambda data: {
            "overdue_tasks": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_BATTERIES,
        name="Overdue batteries",
        icon="mdi:battery-charging-10",
        attributes_fn=lambda data: {
            "overdue_batteries": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: GrocyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for description in BINARY_SENSORS:
        if description.key in coordinator.available_entities:
            entities.append(
                GrocyBinarySensorEntity(coordinator, description, config_entry)
            )
        else:
            LOGGER.debug(
                "Entity '%s' is not available based on Grocy feature flags.",
                description.key,
            )

    async_add_entities(entities)


class GrocyBinarySensorEntity(GrocyEntity, BinarySensorEntity):
    """Grocy binary sensor entity definition."""

    entity_description: GrocyBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        entity_data = self.coordinator.data.get(self.entity_description.key)
        return len(entity_data) > 0 if entity_data else False
