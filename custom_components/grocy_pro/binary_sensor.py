"""Binary sensor platform for Grocy Pro."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_EXPIRED_PRODUCTS,
    ATTR_EXPIRING_PRODUCTS,
    ATTR_MISSING_PRODUCTS,
    ATTR_OVERDUE_BATTERIES,
    ATTR_OVERDUE_CHORES,
    ATTR_OVERDUE_PRODUCTS,
    ATTR_OVERDUE_TASKS,
)
from .coordinator import GrocyConfigEntry
from .entity import GrocyEntity, GrocyEntityDescriptionMixin, list_attributes


@dataclass(frozen=True, kw_only=True)
class GrocyBinarySensorEntityDescription(
    GrocyEntityDescriptionMixin, BinarySensorEntityDescription
):
    """Grocy binary sensor description."""


BINARY_SENSORS: tuple[GrocyBinarySensorEntityDescription, ...] = (
    GrocyBinarySensorEntityDescription(
        key=ATTR_EXPIRED_PRODUCTS,
        name="Expired products",
        icon="mdi:delete-alert-outline",
        attributes_fn=list_attributes("expired_products"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_EXPIRING_PRODUCTS,
        name="Expiring products",
        icon="mdi:clock-fast",
        attributes_fn=list_attributes("expiring_products"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_PRODUCTS,
        name="Overdue products",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=list_attributes("overdue_products"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_MISSING_PRODUCTS,
        name="Missing products",
        icon="mdi:flask-round-bottom-empty-outline",
        attributes_fn=list_attributes("missing_products"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_CHORES,
        name="Overdue chores",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=list_attributes("overdue_chores"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_TASKS,
        name="Overdue tasks",
        icon="mdi:alert-circle-check-outline",
        attributes_fn=list_attributes("overdue_tasks"),
    ),
    GrocyBinarySensorEntityDescription(
        key=ATTR_OVERDUE_BATTERIES,
        name="Overdue batteries",
        icon="mdi:battery-charging-10",
        attributes_fn=list_attributes("overdue_batteries"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrocyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors for the enabled Grocy features."""
    coordinator = entry.runtime_data
    async_add_entities(
        GrocyBinarySensorEntity(coordinator, description)
        for description in BINARY_SENSORS
        if description.key in coordinator.available_entities
    )


class GrocyBinarySensorEntity(GrocyEntity, BinarySensorEntity):
    """On when the Grocy list has items."""

    entity_description: GrocyBinarySensorEntityDescription
    _unrecorded_attributes = frozenset(
        {
            "expired_products",
            "expiring_products",
            "overdue_products",
            "missing_products",
            "overdue_chores",
            "overdue_tasks",
            "overdue_batteries",
        }
    )

    @property
    def is_on(self) -> bool:
        """Return True when the list is not empty."""
        return bool(self._data)
