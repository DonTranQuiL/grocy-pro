"""Grocy services."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import ATTR_CHORES, ATTR_TASKS, DOMAIN
from .coordinator import GrocyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EntityType(str, Enum):
    PRODUCTS = "products"
    CHORES = "chores"
    PRODUCT_BARCODES = "product_barcodes"
    BATTERIES = "batteries"
    LOCATIONS = "locations"
    QUANTITY_UNITS = "quantity_units"
    QUANTITY_UNIT_CONVERSIONS = "quantity_unit_conversions"
    SHOPPING_LIST = "shopping_list"
    SHOPPING_LISTS = "shopping_lists"
    SHOPPING_LOCATIONS = "shopping_locations"
    RECIPES = "recipes"
    RECIPES_POS = "recipes_pos"
    RECIPES_NESTINGS = "recipes_nestings"
    TASKS = "tasks"
    TASK_CATEGORIES = "task_categories"
    PRODUCT_GROUPS = "product_groups"
    EQUIPMENT = "equipment"
    USERFIELDS = "userfields"
    USERENTITIES = "userentities"
    USEROBJECTS = "userobjects"
    MEAL_PLAN = "meal_plan"


class TransactionType(str, Enum):
    CONSUME = "consume"
    PURCHASE = "purchase"
    INVENTORY_CORRECTION = "inventory-correction"
    PRODUCT_OPENED = "product-opened"


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

# --- NEW AI RECEIPT SCANNER SERVICE ---
SERVICE_ADD_PRODUCTS_BY_NAME = "add_products_by_name"

SERVICE_ADD_PRODUCT_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
        vol.Required(SERVICE_AMOUNT): vol.Coerce(float),
        vol.Optional(SERVICE_PRICE): str,
    }
)
SERVICE_OPEN_PRODUCT_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
        vol.Required(SERVICE_AMOUNT): vol.Coerce(float),
        vol.Optional(SERVICE_SUBPRODUCT_SUBSTITUTION): bool,
    }
)
SERVICE_CONSUME_PRODUCT_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
        vol.Required(SERVICE_AMOUNT): vol.Coerce(float),
        vol.Optional(SERVICE_SPOILED): bool,
        vol.Optional(SERVICE_SUBPRODUCT_SUBSTITUTION): bool,
        vol.Optional(SERVICE_TRANSACTION_TYPE): str,
    }
)
SERVICE_EXECUTE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_CHORE_ID): vol.Coerce(int),
        vol.Optional(SERVICE_DONE_BY): vol.Coerce(int),
        vol.Optional(SERVICE_EXECUTION_NOW): bool,
        vol.Optional(SERVICE_SKIPPED): bool,
    }
)
SERVICE_COMPLETE_TASK_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_TASK_ID): vol.Coerce(int),
    }
)
SERVICE_ADD_GENERIC_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_ENTITY_TYPE): str,
        vol.Required(SERVICE_DATA): object,
    }
)
SERVICE_UPDATE_GENERIC_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_ENTITY_TYPE): str,
        vol.Required(SERVICE_OBJECT_ID): vol.Coerce(int),
        vol.Required(SERVICE_DATA): object,
    }
)
SERVICE_DELETE_GENERIC_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_ENTITY_TYPE): str,
        vol.Required(SERVICE_OBJECT_ID): vol.Coerce(int),
    }
)
SERVICE_CONSUME_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_RECIPE_ID): vol.Coerce(int),
    }
)
SERVICE_TRACK_BATTERY_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_BATTERY_ID): vol.Coerce(int),
    }
)
SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST_SCHEMA = vol.Schema(
    {
        vol.Optional(SERVICE_LIST_ID): vol.Coerce(int),
    }
)
SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_PRODUCT_ID): vol.Coerce(int),
        vol.Optional(SERVICE_LIST_ID): vol.Coerce(int),
        vol.Required(SERVICE_AMOUNT): vol.Coerce(float),
    }
)

# --- NEW AI RECEIPT SCANNER SCHEMA ---
SERVICE_ADD_PRODUCTS_BY_NAME_SCHEMA = vol.Schema(
    {
        vol.Required("items"): [
            {
                vol.Required("name"): str,
                vol.Required("amount"): vol.Coerce(float),
                vol.Optional("price"): str,
            }
        ]
    }
)


async def async_setup_services(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    if hass.services.async_services().get(DOMAIN):
        return

    def get_coordinator() -> GrocyDataUpdateCoordinator:
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            raise HomeAssistantError("Grocy integration is not configured.")
        return next(iter(hass.data[DOMAIN].values()))

    async def async_call_grocy_service(service_call: ServiceCall) -> None:
        coordinator = get_coordinator()
        service = service_call.service
        data = service_call.data

        if service == SERVICE_ADD_PRODUCT:
            await async_add_product_service(hass, coordinator, data)
        elif service == SERVICE_OPEN_PRODUCT:
            await async_open_product_service(hass, coordinator, data)
        elif service == SERVICE_CONSUME_PRODUCT:
            await async_consume_product_service(hass, coordinator, data)
        elif service == SERVICE_EXECUTE_CHORE:
            await async_execute_chore_service(hass, coordinator, data)
        elif service == SERVICE_COMPLETE_TASK:
            await async_complete_task_service(hass, coordinator, data)
        elif service == SERVICE_ADD_GENERIC:
            await async_add_generic_service(hass, coordinator, data)
        elif service == SERVICE_UPDATE_GENERIC:
            await async_update_generic_service(hass, coordinator, data)
        elif service == SERVICE_DELETE_GENERIC:
            await async_delete_generic_service(hass, coordinator, data)
        elif service == SERVICE_CONSUME_RECIPE:
            await async_consume_recipe_service(hass, coordinator, data)
        elif service == SERVICE_TRACK_BATTERY:
            await async_track_battery_service(hass, coordinator, data)
        elif service == SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST:
            await async_add_missing_products_to_shopping_list(hass, coordinator, data)
        elif service == SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST:
            await async_remove_product_in_shopping_list_service(hass, coordinator, data)
        elif service == SERVICE_ADD_PRODUCTS_BY_NAME:
            await async_add_products_by_name_service(hass, coordinator, data)

    services_to_register = [
        (SERVICE_ADD_PRODUCT, SERVICE_ADD_PRODUCT_SCHEMA),
        (SERVICE_OPEN_PRODUCT, SERVICE_OPEN_PRODUCT_SCHEMA),
        (SERVICE_CONSUME_PRODUCT, SERVICE_CONSUME_PRODUCT_SCHEMA),
        (SERVICE_EXECUTE_CHORE, SERVICE_EXECUTE_CHORE_SCHEMA),
        (SERVICE_COMPLETE_TASK, SERVICE_COMPLETE_TASK_SCHEMA),
        (SERVICE_ADD_GENERIC, SERVICE_ADD_GENERIC_SCHEMA),
        (SERVICE_UPDATE_GENERIC, SERVICE_UPDATE_GENERIC_SCHEMA),
        (SERVICE_DELETE_GENERIC, SERVICE_DELETE_GENERIC_SCHEMA),
        (SERVICE_CONSUME_RECIPE, SERVICE_CONSUME_RECIPE_SCHEMA),
        (SERVICE_TRACK_BATTERY, SERVICE_TRACK_BATTERY_SCHEMA),
        (
            SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST,
            SERVICE_ADD_MISSING_PRODUCTS_TO_SHOPPING_LIST_SCHEMA,
        ),
        (
            SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST,
            SERVICE_REMOVE_PRODUCT_IN_SHOPPING_LIST_SCHEMA,
        ),
        (SERVICE_ADD_PRODUCTS_BY_NAME, SERVICE_ADD_PRODUCTS_BY_NAME_SCHEMA),
    ]

    for service_name, schema in services_to_register:
        hass.services.async_register(
            DOMAIN, service_name, async_call_grocy_service, schema
        )


async def async_unload_services(hass: HomeAssistant) -> None:
    services = hass.services.async_services().get(DOMAIN)
    if not services:
        return
    for service in list(services.keys()):
        hass.services.async_remove(DOMAIN, service)


# --- EXACT MAPPINGS FROM SOURCE CODE ---


async def async_add_product_service(hass, coordinator, data):
    product_id = data[SERVICE_PRODUCT_ID]
    amount = data[SERVICE_AMOUNT]
    price = data.get(SERVICE_PRICE, "")
    await hass.async_add_executor_job(
        coordinator.grocy_api.stock.add, product_id, amount, price
    )


async def async_open_product_service(hass, coordinator, data):
    product_id = data[SERVICE_PRODUCT_ID]
    amount = data[SERVICE_AMOUNT]
    allow_sub = data.get(SERVICE_SUBPRODUCT_SUBSTITUTION, False)

    def wrapper():
        coordinator.grocy_api.stock.open(
            product_id, amount, allow_subproduct_substitution=allow_sub
        )

    await hass.async_add_executor_job(wrapper)


async def async_consume_product_service(hass, coordinator, data):
    product_id = data[SERVICE_PRODUCT_ID]
    amount = data[SERVICE_AMOUNT]
    spoiled = data.get(SERVICE_SPOILED, False)
    allow_sub = data.get(SERVICE_SUBPRODUCT_SUBSTITUTION, False)
    transaction_type_raw = data.get(SERVICE_TRANSACTION_TYPE)
    transaction_type = (
        TransactionType[transaction_type_raw]
        if transaction_type_raw
        else TransactionType.CONSUME
    )

    def wrapper():
        coordinator.grocy_api.stock.consume(
            product_id,
            amount=amount,
            spoiled=spoiled,
            transaction_type=transaction_type,
            allow_subproduct_substitution=allow_sub,
        )

    await hass.async_add_executor_job(wrapper)


async def async_complete_task_service(hass, coordinator, data):
    task_id = data[SERVICE_TASK_ID]
    await hass.async_add_executor_job(coordinator.grocy_api.tasks.complete, task_id)
    await _async_force_update_entity(coordinator, ATTR_TASKS)


async def async_add_missing_products_to_shopping_list(hass, coordinator, data):
    list_id = data.get(SERVICE_LIST_ID, 1)
    await hass.async_add_executor_job(
        coordinator.grocy_api.shopping_list.add_missing_products, list_id
    )


async def async_remove_product_in_shopping_list_service(hass, coordinator, data):
    product_id = data[SERVICE_PRODUCT_ID]
    list_id = data.get(SERVICE_LIST_ID, 1)
    amount = data[SERVICE_AMOUNT]

    def wrapper():
        coordinator.grocy_api.shopping_list.remove_product(
            product_id, shopping_list_id=list_id, amount=amount
        )

    await hass.async_add_executor_job(wrapper)


# --- AI RECEIPT SCANNER LOGIC ---


async def async_add_products_by_name_service(hass, coordinator, data):
    """Takes a list of string names, finds their Grocy IDs, and adds them to stock."""
    items = data.get("items", [])

    # Grab the full product database to match names to IDs
    def _get_products():
        return coordinator.grocy_api.stock.all_products()

    all_products = await hass.async_add_executor_job(_get_products)

    def _process_items():
        for item in items:
            target_id = None
            search_name = item["name"].strip().lower()

            # Find the matching ID
            for p in all_products:
                if getattr(p, "name", "").strip().lower() == search_name:
                    target_id = getattr(p, "id", None)
                    break

            if target_id:
                # We found a match! Add it to the stock.
                coordinator.grocy_api.stock.add(
                    target_id, item["amount"], item.get("price", "")
                )
            else:
                _LOGGER.warning(
                    "AI Receipt Scanner: Could not find Grocy product matching '%s'",
                    item["name"],
                )

    await hass.async_add_executor_job(_process_items)


# --- FALLBACKS (Smart Execution for unknown managers) ---


def _call_action_safely(manager, preferred_name, fallback_name, *args, **kwargs):
    """Attempt new method name, fallback to old if necessary."""
    if hasattr(manager, preferred_name):
        return getattr(manager, preferred_name)(*args, **kwargs)
    return getattr(manager, fallback_name)(*args, **kwargs)


async def async_execute_chore_service(hass, coordinator, data):
    chore_id = data[SERVICE_CHORE_ID]
    done_by = data.get(SERVICE_DONE_BY, "")
    tracked_time = datetime.now() if data.get(SERVICE_EXECUTION_NOW, False) else None
    skipped = data.get(SERVICE_SKIPPED, False)
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.chores,
        "execute",
        "execute_chore",
        chore_id,
        done_by,
        tracked_time,
        skipped,
    )
    await _async_force_update_entity(coordinator, ATTR_CHORES)


async def async_add_generic_service(hass, coordinator, data):
    entity_type_raw = data.get(SERVICE_ENTITY_TYPE)
    entity_type = EntityType(entity_type_raw) if entity_type_raw else EntityType.TASKS
    payload = data[SERVICE_DATA]
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.system,
        "add",
        "add_generic",
        entity_type,
        payload,
    )
    await post_generic_refresh(coordinator, entity_type)


async def async_update_generic_service(hass, coordinator, data):
    entity_type_raw = data.get(SERVICE_ENTITY_TYPE)
    entity_type = EntityType(entity_type_raw) if entity_type_raw else EntityType.TASKS
    object_id = data[SERVICE_OBJECT_ID]
    payload = data[SERVICE_DATA]
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.system,
        "update",
        "update_generic",
        entity_type,
        object_id,
        payload,
    )
    await post_generic_refresh(coordinator, entity_type)


async def async_delete_generic_service(hass, coordinator, data):
    entity_type_raw = data.get(SERVICE_ENTITY_TYPE)
    entity_type = EntityType(entity_type_raw) if entity_type_raw else EntityType.TASKS
    object_id = data[SERVICE_OBJECT_ID]
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.system,
        "delete",
        "delete_generic",
        entity_type,
        object_id,
    )
    await post_generic_refresh(coordinator, entity_type)


async def post_generic_refresh(coordinator, entity_type):
    if entity_type.value in ("tasks", "chores"):
        await _async_force_update_entity(coordinator, entity_type.value)


async def async_consume_recipe_service(hass, coordinator, data):
    recipe_id = data[SERVICE_RECIPE_ID]
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.recipes,
        "consume",
        "consume_recipe",
        recipe_id,
    )


async def async_track_battery_service(hass, coordinator, data):
    battery_id = data[SERVICE_BATTERY_ID]
    await hass.async_add_executor_job(
        _call_action_safely,
        coordinator.grocy_api.batteries,
        "charge",
        "charge_battery",
        battery_id,
    )


async def _async_force_update_entity(
    coordinator: GrocyDataUpdateCoordinator, entity_key: str
) -> None:
    entity = next(
        (e for e in coordinator.entities if e.entity_description.key == entity_key),
        None,
    )
    if entity:
        await entity.async_update_ha_state(force_refresh=True)
