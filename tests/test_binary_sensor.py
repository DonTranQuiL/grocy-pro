import pytest
from unittest.mock import MagicMock
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy.const import DOMAIN, ATTR_EXPIRED_PRODUCTS
from custom_components.grocy.binary_sensor import (
    GrocyBinarySensorEntity,
    GrocyBinarySensorEntityDescription,
)


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.config_entry = MockConfigEntry(domain=DOMAIN, entry_id="test_id")
    coord.available_entities = [ATTR_EXPIRED_PRODUCTS]
    coord.data = {
        ATTR_EXPIRED_PRODUCTS: [{"id": 1, "name": "Milk"}],
    }
    return coord


def test_binary_sensor_properties(mock_coordinator):
    description = GrocyBinarySensorEntityDescription(
        key=ATTR_EXPIRED_PRODUCTS,
        name="Expired products",
        icon="mdi:alert",
        attributes_fn=lambda x: {"count": len(x) if x else 0},
    )

    sensor = GrocyBinarySensorEntity(
        mock_coordinator, description, mock_coordinator.config_entry
    )

    assert sensor.name == "Expired products"
    assert sensor.unique_id == f"test_id_{ATTR_EXPIRED_PRODUCTS}"
    assert sensor.is_on is True
    assert sensor.extra_state_attributes["count"] == 1
    assert sensor.icon == "mdi:alert"

    # Test empty state
    mock_coordinator.data[ATTR_EXPIRED_PRODUCTS] = []
    assert sensor.is_on is False
