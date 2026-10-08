"""Sensor platform for Grocy Pro."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_BATTERIES,
    ATTR_CHORES,
    ATTR_MEAL_PLAN,
    ATTR_SHOPPING_LIST,
    ATTR_STOCK,
    ATTR_TASKS,
    CHORES,
    ITEMS,
    MEAL_PLANS,
    PRODUCTS,
    TASKS,
)
from .coordinator import GrocyConfigEntry
from .entity import GrocyEntity, GrocyEntityDescriptionMixin, list_attributes


@dataclass(frozen=True, kw_only=True)
class GrocySensorEntityDescription(
    GrocyEntityDescriptionMixin, SensorEntityDescription
):
    """Grocy sensor description."""


# Names stay English on purpose: entity IDs are generated from them, and the
# card and existing dashboards rely on sensor.grocy_<key>.
SENSORS: tuple[GrocySensorEntityDescription, ...] = (
    GrocySensorEntityDescription(
        key=ATTR_CHORES,
        name="Chores",
        native_unit_of_measurement=CHORES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:broom",
        attributes_fn=list_attributes("chores"),
    ),
    GrocySensorEntityDescription(
        key=ATTR_MEAL_PLAN,
        name="Meal plan",
        native_unit_of_measurement=MEAL_PLANS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:silverware-variant",
        attributes_fn=list_attributes("meals"),
    ),
    GrocySensorEntityDescription(
        key=ATTR_SHOPPING_LIST,
        name="Shopping list",
        native_unit_of_measurement=PRODUCTS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cart-outline",
        attributes_fn=list_attributes("products"),
    ),
    GrocySensorEntityDescription(
        key=ATTR_STOCK,
        name="Stock",
        native_unit_of_measurement=PRODUCTS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fridge-outline",
        attributes_fn=list_attributes("products"),
    ),
    GrocySensorEntityDescription(
        key=ATTR_TASKS,
        name="Tasks",
        native_unit_of_measurement=TASKS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:checkbox-marked-circle-outline",
        attributes_fn=list_attributes("tasks"),
    ),
    GrocySensorEntityDescription(
        key=ATTR_BATTERIES,
        name="Batteries",
        native_unit_of_measurement=ITEMS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        attributes_fn=list_attributes("batteries"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrocyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors for the enabled Grocy features."""
    coordinator = entry.runtime_data
    async_add_entities(
        GrocySensorEntity(coordinator, description)
        for description in SENSORS
        if description.key in coordinator.available_entities
    )


class GrocySensorEntity(GrocyEntity, SensorEntity):
    """A Grocy count sensor with the items as attributes."""

    entity_description: GrocySensorEntityDescription
    # The item lists can be large; keep them out of the recorder database.
    _unrecorded_attributes = frozenset(
        {"chores", "meals", "products", "tasks", "batteries"}
    )

    @property
    def native_value(self) -> StateType:
        """Return the number of items."""
        return len(self._data or [])
