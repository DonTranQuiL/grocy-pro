"""Grocy Pro actions."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.grocy_pro.const import DOMAIN


async def _call(hass: HomeAssistant, service: str, data: dict) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)


@pytest.mark.parametrize(
    ("service", "data", "method", "path", "body"),
    [
        (
            "add_product_to_stock",
            {"product_id": 3, "amount": 2, "price": "1.5"},
            "POST",
            "stock/products/3/add",
            {"amount": 2.0, "transaction_type": "purchase", "price": 1.5},
        ),
        (
            "add_product_to_stock",
            {"product_id": "3", "amount": 1, "price": ""},
            "POST",
            "stock/products/3/add",
            {"amount": 1.0, "transaction_type": "purchase", "price": None},
        ),
        (
            "open_product",
            {"product_id": 3, "amount": 0.5},
            "POST",
            "stock/products/3/open",
            {"amount": 0.5, "allow_subproduct_substitution": False},
        ),
        (
            "consume_product_from_stock",
            {"product_id": 3, "spoiled": True, "transaction_type": "CONSUME"},
            "POST",
            "stock/products/3/consume",
            {
                "amount": 1.0,
                "spoiled": True,
                "transaction_type": "consume",
                "allow_subproduct_substitution": False,
            },
        ),
        ("complete_task", {"task_id": 4}, "POST", "tasks/4/complete", None),
        ("consume_recipe", {"recipe_id": 2}, "POST", "recipes/2/consume", None),
        ("track_battery", {"battery_id": 1}, "POST", "batteries/1/charge", None),
        (
            "add_missing_products_to_shopping_list",
            {},
            "POST",
            "stock/shoppinglist/add-missing-products",
            {"list_id": 1},
        ),
        (
            "remove_product_in_shopping_list",
            {"product_id": 17, "amount": 2},
            "POST",
            "stock/shoppinglist/remove-product",
            {"product_id": 17, "list_id": 1, "product_amount": 2.0},
        ),
        (
            "add_generic",
            {"entity_type": "tasks", "data": {"name": "Buy milk"}},
            "POST",
            "objects/tasks",
            {"name": "Buy milk"},
        ),
        (
            "update_generic",
            {"entity_type": "tasks", "object_id": 2, "data": {"name": "New"}},
            "PUT",
            "objects/tasks/2",
            {"name": "New"},
        ),
        (
            "delete_generic",
            {"entity_type": "chores", "object_id": 2},
            "DELETE",
            "objects/chores/2",
            None,
        ),
    ],
)
async def test_services_call_grocy(
    hass: HomeAssistant,
    setup_integration,
    grocy_server,
    service,
    data,
    method,
    path,
    body,
) -> None:
    """Each action sends the right request and refreshes the data."""
    entry = await setup_integration()
    before = entry.runtime_data.stats.full_refreshes
    await _call(hass, service, data)
    sent = [(p, b) for p, b in grocy_server.calls_for(method) if p == path]
    assert sent, grocy_server.calls[-3:]
    if body is not None:
        sent_body = sent[-1][1]
        for key, value in body.items():
            assert sent_body[key] == value, key
    await hass.async_block_till_done()
    assert entry.runtime_data.stats.full_refreshes > before


async def test_execute_chore(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Chores are tracked at their scheduled time unless 'track now' is set."""
    await setup_integration()
    await _call(hass, "execute_chore", {"chore_id": 1, "done_by": 1})
    path, body = grocy_server.calls_for("POST")[-1]
    assert path == "chores/1/execute"
    assert body["done_by"] == 1
    assert body["skipped"] is False
    scheduled = grocy_server.routes["chores/1"]["next_estimated_execution_time"]
    assert body["tracked_time"].startswith(scheduled[:10])

    await _call(hass, "execute_chore", {"chore_id": 1, "track_execution_now": True})
    _, body = grocy_server.calls_for("POST")[-1]
    assert body["tracked_time"].startswith("2026-10-08")
    assert "done_by" not in body


async def test_add_products_by_name(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Known names are added; unknown names are reported."""
    await setup_integration()
    with pytest.raises(ServiceValidationError) as err:
        await _call(
            hass,
            "add_products_by_name",
            {
                "items": [
                    {"name": " cookies ", "amount": 2, "price": 1.29},
                    {"name": "Unicorn steak"},
                ]
            },
        )
    assert err.value.translation_key == "products_not_found"
    assert err.value.translation_placeholders == {"names": "Unicorn steak"}
    adds = [(p, b) for p, b in grocy_server.calls_for("POST") if p.endswith("/add")]
    assert adds == [
        (
            "stock/products/1/add",
            {"amount": 2.0, "transaction_type": "purchase", "price": 1.29},
        )
    ]


async def test_service_error_is_translated(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Grocy errors surface as a translated HomeAssistantError."""
    await setup_integration()
    grocy_server.fail = 400
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, "complete_task", {"task_id": 99})
    assert err.value.translation_key == "grocy_error"
    assert "HTTP 400" in err.value.translation_placeholders["error"]


async def test_service_validation(hass: HomeAssistant, setup_integration) -> None:
    """Bad input is rejected before anything is sent."""
    import voluptuous as vol

    await setup_integration()
    with pytest.raises(vol.Invalid):
        await _call(hass, "add_product_to_stock", {"product_id": 1, "amount": 0})
    with pytest.raises(vol.Invalid):
        await _call(hass, "add_generic", {"entity_type": "nope", "data": {}})
    with pytest.raises(vol.Invalid):
        await _call(
            hass,
            "consume_product_from_stock",
            {"product_id": 1, "transaction_type": "x"},
        )


async def test_service_when_not_loaded(hass: HomeAssistant, setup_integration) -> None:
    """Actions explain that the integration isn't loaded."""
    entry = await setup_integration()
    await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "complete_task", {"task_id": 1})
    assert err.value.translation_key == "not_loaded"
