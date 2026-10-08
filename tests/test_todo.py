"""The shopping list as a to-do list."""

from __future__ import annotations

import pytest
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

ENTITY = "todo.grocy_shopping_list"


async def test_items(hass: HomeAssistant, setup_integration) -> None:
    """Items show product names, notes and done state."""
    await setup_integration()
    result = await hass.services.async_call(
        TODO_DOMAIN,
        "get_items",
        {"status": ["needs_action", "completed"]},
        target={"entity_id": ENTITY},
        blocking=True,
        return_response=True,
    )
    items = {item["uid"]: item for item in result[ENTITY]["items"]}
    assert items["1"]["summary"] == "Some good snacks"
    assert items["1"]["status"] == "needs_action"
    assert items["3"]["status"] == "completed"
    assert items["3"]["summary"] != "Item 3"
    assert items["3"]["description"].startswith("Amount: 1")


async def test_add_item(hass: HomeAssistant, setup_integration, grocy_server) -> None:
    """Adding an item looks the product up by name."""
    await setup_integration()
    await hass.services.async_call(
        TODO_DOMAIN,
        "add_item",
        {"item": "Cookies"},
        target={"entity_id": ENTITY},
        blocking=True,
    )
    path, body = grocy_server.calls_for("POST")[-1]
    assert path == "stock/shoppinglist/add-product"
    assert body["product_id"] == 1


async def test_add_unknown_item(hass: HomeAssistant, setup_integration) -> None:
    """Unknown products give a clear error."""
    await setup_integration()
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {"item": "Unicorn steak"},
            target={"entity_id": ENTITY},
            blocking=True,
        )
    assert err.value.translation_key == "product_not_found"


async def test_complete_and_delete(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Checking off and removing items."""
    await setup_integration()
    await hass.services.async_call(
        TODO_DOMAIN,
        "update_item",
        {"item": "1", "status": "completed"},
        target={"entity_id": ENTITY},
        blocking=True,
    )
    path, body = grocy_server.calls_for("PUT")[-1]
    assert path == "objects/shopping_list/1"
    assert body == {"done": 1}

    await hass.services.async_call(
        TODO_DOMAIN,
        "remove_item",
        {"item": ["1"]},
        target={"entity_id": ENTITY},
        blocking=True,
    )
    assert grocy_server.calls_for("DELETE")[-1][0] == "objects/shopping_list/1"


async def test_errors_are_translated(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Grocy errors become a readable error."""
    await setup_integration()
    grocy_server.fail = 500
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            TODO_DOMAIN,
            "remove_item",
            {"item": ["1"]},
            target={"entity_id": ENTITY},
            blocking=True,
        )
    assert err.value.translation_key == "grocy_error"


def test_find_product_id() -> None:
    """Exact matches win; a unique partial match is accepted; ambiguity is not."""
    from types import SimpleNamespace as P

    from custom_components.grocy_pro.todo import find_product_id

    products = [
        P(id=1, name="Cookies"),
        P(id=2, name="Chocolate"),
        P(id=3, name="Milk"),
        P(id=4, name="Oat milk"),
        P(id=5, name=None),
    ]
    assert find_product_id(products, " cookies ") == 1
    assert find_product_id(products, "cookie") == 1
    assert find_product_id(products, "Dark chocolate 70%") == 2
    assert find_product_id(products, "milk") == 3
    assert find_product_id(products, "mil") is None  # Milk and Oat milk
    assert find_product_id(products, "") is None
    assert find_product_id(products, "Pizza") is None
