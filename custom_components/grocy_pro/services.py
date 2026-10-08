"""Services for Grocy Pro."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import voluptuous as vol
from grocy import EntityType, TransactionType
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import (
    GrocyAuthError,
    GrocyConnectionError,
    GrocyDataUpdateCoordinator,
    call_grocy,
)
from .todo import find_product_id

SERVICE_PRODUCT_ID = "product_id"
SERVICE_AMOUNT = "amount"
SERVICE_PRICE = "price"
SERVICE_SPOILED = "spoiled"
SERVICE_SUBPRODUCT_SUBSTITUTION = "allow_subproduct_substitution"
SERVICE_TRANSACTION_TYPE = "transaction_type"
SERVICE_CHORE_ID = "chore_id"
SERVICE_DONE_BY = "done_by"
SERVICE_EXECUTION_NOW = "track_execution_now"
SERVICE_SKIPPED = "skipped"
SERVICE_TASK_ID = "task_id"
SERVICE_ENTITY_TYPE = "entity_type"
SERVICE_DATA = "data"
SERVICE_RECIPE_ID = "recipe_id"
SERVICE_BATTERY_ID = "battery_id"
SERVICE_OBJECT_ID = "object_id"
SERVICE_LIST_ID = "list_id"
SERVICE_ITEMS = "items"

SERVICE_ADD_PRODUCT = "add_product_to_stock"
SERVICE_OPEN_PRODUCT = "open_product"
SERVICE_CONSUME_PRODUCT = "consume_product_from_stock"
SERVICE_EXECUTE_CHORE = "execute_chore"
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_ADD_GENERIC = "add_generic"
SERVICE_UPDATE_GENERIC = "update_generic"
SERVICE_DELETE_GENERIC = "delete_generic"
SERVICE_CONSUME_RECIPE = "consume_recipe"
SERVICE_TRACK_BATTERY = "track_battery"
SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST = "add_missing_products_to_shopping_list"
SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST = "remove_product_in_shopping_list"
SERVICE_ADD_PRODUCTS_BY_NAME = "add_products_by_name"

# Accept both the enum names used in 2.x (CONSUME) and Grocy's values (consume).
TRANSACTION_TYPES = {t.name: t for t in TransactionType} | {
    t.value: t for t in TransactionType
}
ENTITY_TYPES = [t.value for t in EntityType]

_amount = vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False))

SCHEMAS: dict[str, vol.Schema] = {
    SERVICE_ADD_PRODUCT: vol.Schema(
        {
            vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
            vol.Required(SERVICE_AMOUNT): _amount,
            vol.Optional(SERVICE_PRICE): vol.Any(None, "", vol.Coerce(float)),
        }
    ),
    SERVICE_OPEN_PRODUCT: vol.Schema(
        {
            vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
            vol.Optional(SERVICE_AMOUNT, default=1): _amount,
            vol.Optional(SERVICE_SUBPRODUCT_SUBSTITUTION, default=False): cv.boolean,
        }
    ),
    SERVICE_CONSUME_PRODUCT: vol.Schema(
        {
            vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
            vol.Optional(SERVICE_AMOUNT, default=1): _amount,
            vol.Optional(SERVICE_SPOILED, default=False): cv.boolean,
            vol.Optional(SERVICE_SUBPRODUCT_SUBSTITUTION, default=False): cv.boolean,
            vol.Optional(SERVICE_TRANSACTION_TYPE, default="consume"): vol.In(
                TRANSACTION_TYPES
            ),
        }
    ),
    SERVICE_EXECUTE_CHORE: vol.Schema(
        {
            vol.Required(SERVICE_CHORE_ID): vol.Coerce(int),
            vol.Optional(SERVICE_DONE_BY): vol.Coerce(int),
            vol.Optional(SERVICE_EXECUTION_NOW, default=False): cv.boolean,
            vol.Optional(SERVICE_SKIPPED, default=False): cv.boolean,
        }
    ),
    SERVICE_COMPLETE_TASK: vol.Schema({vol.Required(SERVICE_TASK_ID): vol.Coerce(int)}),
    SERVICE_ADD_GENERIC: vol.Schema(
        {
            vol.Required(SERVICE_ENTITY_TYPE): vol.In(ENTITY_TYPES),
            vol.Required(SERVICE_DATA): dict,
        }
    ),
    SERVICE_UPDATE_GENERIC: vol.Schema(
        {
            vol.Required(SERVICE_ENTITY_TYPE): vol.In(ENTITY_TYPES),
            vol.Required(SERVICE_OBJECT_ID): vol.Coerce(int),
            vol.Required(SERVICE_DATA): dict,
        }
    ),
    SERVICE_DELETE_GENERIC: vol.Schema(
        {
            vol.Required(SERVICE_ENTITY_TYPE): vol.In(ENTITY_TYPES),
            vol.Required(SERVICE_OBJECT_ID): vol.Coerce(int),
        }
    ),
    SERVICE_CONSUME_RECIPE: vol.Schema(
        {vol.Required(SERVICE_RECIPE_ID): vol.Coerce(int)}
    ),
    SERVICE_TRACK_BATTERY: vol.Schema(
        {vol.Required(SERVICE_BATTERY_ID): vol.Coerce(int)}
    ),
    SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST: vol.Schema(
        {vol.Optional(SERVICE_LIST_ID, default=1): vol.Coerce(int)}
    ),
    SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST: vol.Schema(
        {
            vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
            vol.Optional(SERVICE_LIST_ID, default=1): vol.Coerce(int),
            vol.Optional(SERVICE_AMOUNT, default=1): _amount,
        }
    ),
    SERVICE_ADD_PRODUCTS_BY_NAME: vol.Schema(
        {
            vol.Required(SERVICE_ITEMS): [
                vol.Schema(
                    {
                        vol.Required("name"): cv.string,
                        vol.Optional(SERVICE_AMOUNT, default=1): _amount,
                        vol.Optional(SERVICE_PRICE): vol.Any(
                            None, "", vol.Coerce(float)
                        ),
                    },
                    extra=vol.ALLOW_EXTRA,
                )
            ]
        },
        extra=vol.ALLOW_EXTRA,
    ),
}


def _price(value: Any) -> float | None:
    return None if value in (None, "") else float(value)


def _add_product(api: Any, data: dict[str, Any]) -> None:
    api.stock.add(
        data[SERVICE_PRODUCT_ID], data[SERVICE_AMOUNT], _price(data.get(SERVICE_PRICE))
    )


def _open_product(api: Any, data: dict[str, Any]) -> None:
    api.stock.open(
        data[SERVICE_PRODUCT_ID],
        data[SERVICE_AMOUNT],
        allow_subproduct_substitution=data[SERVICE_SUBPRODUCT_SUBSTITUTION],
    )


def _consume_product(api: Any, data: dict[str, Any]) -> None:
    api.stock.consume(
        data[SERVICE_PRODUCT_ID],
        amount=data[SERVICE_AMOUNT],
        spoiled=data[SERVICE_SPOILED],
        transaction_type=TRANSACTION_TYPES[data[SERVICE_TRANSACTION_TYPE]],
        allow_subproduct_substitution=data[SERVICE_SUBPRODUCT_SUBSTITUTION],
    )


def _execute_chore(api: Any, data: dict[str, Any]) -> None:
    chore_id = data[SERVICE_CHORE_ID]
    tracked_time: datetime | None = None
    if not data[SERVICE_EXECUTION_NOW]:
        # Track at the scheduled time, like the original integration did.
        tracked_time = api.chores.get(chore_id).next_estimated_execution_time
    api.chores.execute(
        chore_id,
        done_by=data.get(SERVICE_DONE_BY),
        tracked_time=tracked_time,
        skipped=data[SERVICE_SKIPPED],
    )


def _complete_task(api: Any, data: dict[str, Any]) -> None:
    api.tasks.complete(data[SERVICE_TASK_ID])


def _add_generic(api: Any, data: dict[str, Any]) -> None:
    api.generic.create(EntityType(data[SERVICE_ENTITY_TYPE]), data[SERVICE_DATA])


def _update_generic(api: Any, data: dict[str, Any]) -> None:
    api.generic.update(
        EntityType(data[SERVICE_ENTITY_TYPE]),
        data[SERVICE_OBJECT_ID],
        data[SERVICE_DATA],
    )


def _delete_generic(api: Any, data: dict[str, Any]) -> None:
    api.generic.delete(EntityType(data[SERVICE_ENTITY_TYPE]), data[SERVICE_OBJECT_ID])


def _consume_recipe(api: Any, data: dict[str, Any]) -> None:
    api.recipes.consume(data[SERVICE_RECIPE_ID])


def _track_battery(api: Any, data: dict[str, Any]) -> None:
    api.batteries.charge(data[SERVICE_BATTERY_ID])


def _add_missing_products(api: Any, data: dict[str, Any]) -> None:
    api.shopping_list.add_missing_products(data[SERVICE_LIST_ID])


def _remove_from_shopping_list(api: Any, data: dict[str, Any]) -> None:
    api.shopping_list.remove_product(
        data[SERVICE_PRODUCT_ID],
        shopping_list_id=data[SERVICE_LIST_ID],
        amount=data[SERVICE_AMOUNT],
    )


def _add_products_by_name(api: Any, data: dict[str, Any]) -> list[str]:
    products = api.stock.all_products()
    not_found: list[str] = []
    for item in data[SERVICE_ITEMS]:
        product_id = find_product_id(products, item["name"])
        if product_id is None:
            not_found.append(item["name"])
            continue
        api.stock.add(product_id, item[SERVICE_AMOUNT], _price(item.get(SERVICE_PRICE)))
    return not_found


HANDLERS: dict[str, Callable[[Any, dict[str, Any]], Any]] = {
    SERVICE_ADD_PRODUCT: _add_product,
    SERVICE_OPEN_PRODUCT: _open_product,
    SERVICE_CONSUME_PRODUCT: _consume_product,
    SERVICE_EXECUTE_CHORE: _execute_chore,
    SERVICE_COMPLETE_TASK: _complete_task,
    SERVICE_ADD_GENERIC: _add_generic,
    SERVICE_UPDATE_GENERIC: _update_generic,
    SERVICE_DELETE_GENERIC: _delete_generic,
    SERVICE_CONSUME_RECIPE: _consume_recipe,
    SERVICE_TRACK_BATTERY: _track_battery,
    SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST: _add_missing_products,
    SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST: _remove_from_shopping_list,
    SERVICE_ADD_PRODUCTS_BY_NAME: _add_products_by_name,
}


def _get_coordinator(hass: HomeAssistant) -> GrocyDataUpdateCoordinator:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="not_loaded"
        )
    return entries[0].runtime_data


def _make_handler(
    hass: HomeAssistant, service: str
) -> Callable[[ServiceCall], Awaitable[None]]:
    handler = HANDLERS[service]

    async def _async_handle(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        data = dict(call.data)
        try:
            result = await hass.async_add_executor_job(
                call_grocy, handler, coordinator.grocy_api, data
            )
        except (GrocyAuthError, GrocyConnectionError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="grocy_error",
                translation_placeholders={"error": str(err)},
            ) from err
        coordinator.request_full_refresh()
        await coordinator.async_request_refresh()
        if service == SERVICE_ADD_PRODUCTS_BY_NAME and result:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="products_not_found",
                translation_placeholders={"names": ", ".join(result)},
            )

    return _async_handle


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Grocy Pro services (once, from async_setup)."""
    for service, schema in SCHEMAS.items():
        hass.services.async_register(
            DOMAIN, service, _make_handler(hass, service), schema=schema
        )
