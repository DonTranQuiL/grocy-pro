import pytest
from unittest.mock import MagicMock
from homeassistant.components.sensor import SensorStateClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy.const import DOMAIN
from custom_components.grocy.sensor import (
    GrocySensorEntity,
    GrocySensorEntityDescription,
)


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.config_entry = MockConfigEntry(domain=DOMAIN, entry_id="test_id")
    coord.available_entities = ["stock", "chores"]
    coord.data = {"stock": [{"id": 1, "name": "Apple"}], "chores": []}
    return coord


def test_sensor_properties(mock_coordinator):
    description = GrocySensorEntityDescription(
        key="stock",
        name="Stock",
        icon="mdi:cart",
        native_unit_of_measurement="Product(s)",
        state_class=SensorStateClass.MEASUREMENT,
        attributes_fn=lambda x: {"count": len(x) if x else 0},
    )

    sensor = GrocySensorEntity(
        mock_coordinator, description, mock_coordinator.config_entry
    )

    assert sensor.name == "Stock"
    assert sensor.unique_id == "test_id_stock"
    assert sensor.native_value == 1
    assert sensor.extra_state_attributes["count"] == 1
    assert sensor.icon == "mdi:cart"
