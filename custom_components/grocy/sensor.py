"""Sensor platform for Grocy."""

from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_BATTERIES,
    ATTR_CHORES,
    ATTR_MEAL_PLAN,
    ATTR_SHOPPING_LIST,
    ATTR_STOCK,
    ATTR_TASKS,
    CHORES,
    DOMAIN,
    ITEMS,
    LOGGER,
    MEAL_PLANS,
    PRODUCTS,
    TASKS,
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
class GrocySensorEntityDescription(SensorEntityDescription):
    """Grocy sensor entity description."""

    attributes_fn: Callable[[list[Any]], Mapping[str, Any] | None] = lambda _: None


SENSORS: tuple[GrocySensorEntityDescription, ...] = (
    GrocySensorEntityDescription(
        key=ATTR_CHORES,
        name="Chores",
        native_unit_of_measurement=CHORES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:broom",
        attributes_fn=lambda data: {
            "chores": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocySensorEntityDescription(
        key=ATTR_MEAL_PLAN,
        name="Meal plan",
        native_unit_of_measurement=MEAL_PLANS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:silverware-variant",
        attributes_fn=lambda data: {
            "meals": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocySensorEntityDescription(
        key=ATTR_SHOPPING_LIST,
        name="Shopping list",
        native_unit_of_measurement=PRODUCTS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cart-outline",
        attributes_fn=lambda data: {
            "products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocySensorEntityDescription(
        key=ATTR_STOCK,
        name="Stock",
        native_unit_of_measurement=PRODUCTS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fridge-outline",
        attributes_fn=lambda data: {
            "products": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocySensorEntityDescription(
        key=ATTR_TASKS,
        name="Tasks",
        native_unit_of_measurement=TASKS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:checkbox-marked-circle-outline",
        attributes_fn=lambda data: {
            "tasks": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
    GrocySensorEntityDescription(
        key=ATTR_BATTERIES,
        name="Batteries",
        native_unit_of_measurement=ITEMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        attributes_fn=lambda data: {
            "batteries": [_as_dict(x) for x in data] if data else [],
            "count": len(data) if data else 0,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: GrocyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for description in SENSORS:
        if description.key in coordinator.available_entities:
            entities.append(GrocySensorEntity(coordinator, description, config_entry))
        else:
            LOGGER.debug(
                "Entity '%s' is not available based on Grocy feature flags.",
                description.key,
            )

    async_add_entities(entities)


class GrocySensorEntity(GrocyEntity, SensorEntity):
    """Grocy sensor entity definition."""

    entity_description: GrocySensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        entity_data = self.coordinator.data.get(self.entity_description.key)
        return len(entity_data) if entity_data else 0
