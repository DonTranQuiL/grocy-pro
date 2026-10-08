"""To-do platform for Grocy Pro: the Grocy shopping list."""

from __future__ import annotations

from typing import Any

from grocy import EntityType
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_SHOPPING_LIST, DOMAIN
from .coordinator import (
    GrocyAuthError,
    GrocyConfigEntry,
    GrocyConnectionError,
    GrocyDataUpdateCoordinator,
    call_grocy,
)
from .entity import GrocyEntity


def find_product_id(products: list[Any], name: str) -> int | None:
    """Return the id of the product called `name`.

    An exact (case-insensitive) match wins. Otherwise a single product whose name
    contains the text, or is contained in it ("cookie" -> "Cookies"), is used.
    Ambiguous text matches nothing, so the wrong product is never booked.
    """
    wanted = name.strip().casefold()
    if not wanted:
        return None
    named = [
        (product.id, (getattr(product, "name", None) or "").strip().casefold())
        for product in products
    ]
    for product_id, product_name in named:
        if product_name == wanted:
            return product_id
    partial = [
        product_id
        for product_id, product_name in named
        if product_name and (wanted in product_name or product_name in wanted)
    ]
    return partial[0] if len(partial) == 1 else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrocyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the shopping list when Grocy has shopping lists enabled."""
    coordinator = entry.runtime_data
    if ATTR_SHOPPING_LIST in coordinator.available_entities:
        async_add_entities([GrocyTodoListEntity(coordinator)])


class GrocyTodoListEntity(GrocyEntity, TodoListEntity):
    """The Grocy shopping list as a Home Assistant to-do list."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: GrocyDataUpdateCoordinator) -> None:
        """Initialise."""
        super().__init__(
            coordinator,
            EntityDescription(
                key=ATTR_SHOPPING_LIST, name="Shopping list", icon="mdi:cart-outline"
            ),
        )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the shopping list items."""
        data = self._data
        if data is None:
            return None
        items = []
        for item in data:
            product = getattr(item, "product", None)
            summary = getattr(product, "name", None) or item.note or f"Item {item.id}"
            amount = item.amount if item.amount is not None else 1
            description = f"Amount: {amount:g}"
            if item.note and summary != item.note:
                description += f"\n{item.note}"
            items.append(
                TodoItem(
                    uid=str(item.id),
                    summary=summary,
                    status=(
                        TodoItemStatus.COMPLETED
                        if item.done
                        else TodoItemStatus.NEEDS_ACTION
                    ),
                    description=description,
                )
            )
        return items

    async def _run(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await self.hass.async_add_executor_job(
                lambda: call_grocy(func, *args, **kwargs)
            )
        except (GrocyAuthError, GrocyConnectionError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="grocy_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def _refresh(self) -> None:
        self.coordinator.request_full_refresh()
        await self.coordinator.async_request_refresh()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an existing Grocy product to the shopping list by name."""
        api = self.coordinator.grocy_api
        products = await self._run(api.stock.all_products)
        product_id = find_product_id(products, item.summary or "")
        if product_id is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="product_not_found",
                translation_placeholders={"name": item.summary or ""},
            )
        await self._run(api.shopping_list.add_product, product_id)
        await self._refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Mark a shopping list item done or not done."""
        await self._run(
            self.coordinator.grocy_api.shopping_list.mark_item_done,
            int(item.uid),
            item.status == TodoItemStatus.COMPLETED,
        )
        await self._refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete shopping list items."""
        for uid in uids:
            await self._run(
                self.coordinator.grocy_api.generic.delete,
                EntityType.SHOPPING_LIST,
                int(uid),
            )
        await self._refresh()
