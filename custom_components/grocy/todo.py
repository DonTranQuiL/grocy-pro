"""To-Do platform for Grocy."""

from __future__ import annotations


from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_SHOPPING_LIST, DOMAIN, LOGGER
from .coordinator import GrocyDataUpdateCoordinator
from .entity import GrocyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Grocy To-Do platform."""
    coordinator: GrocyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Only load the To-Do list if Shopping Lists are enabled in Grocy
    if ATTR_SHOPPING_LIST in coordinator.available_entities:
        async_add_entities([GrocyTodoListEntity(coordinator, config_entry)])
    else:
        LOGGER.debug(
            "Shopping List feature is disabled in Grocy. Skipping To-Do entity."
        )


class GrocyTodoListEntity(GrocyEntity, TodoListEntity):
    """Grocy shopping list mapped to a Home Assistant To-Do list."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: GrocyDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the To-Do list."""
        description = EntityDescription(
            key=ATTR_SHOPPING_LIST,
            name="Grocy Shopping List",
            icon="mdi:cart-outline",
        )
        super().__init__(coordinator, description, config_entry)
        self._attr_name = "Grocy Shopping List"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the list of items from Grocy."""
        data = self.coordinator.data.get(ATTR_SHOPPING_LIST)
        if data is None:
            return None

        items = []
        for item in data:
            # Safely extract IDs and names whether Pydantic v1 or v2
            uid = str(getattr(item, "id", getattr(item, "product_id", "unknown")))

            summary = "Unknown Product"
            if hasattr(item, "product") and hasattr(item.product, "name"):
                summary = item.product.name
            elif hasattr(item, "name"):
                summary = item.name

            # Check if Grocy marks the item as 'done'
            status = TodoItemStatus.NEEDS_ACTION
            done_val = getattr(item, "done", getattr(item, "is_done", 0))
            if str(done_val) in ("1", "True", "true"):
                status = TodoItemStatus.COMPLETED

            amount = getattr(item, "amount", 1)

            items.append(
                TodoItem(
                    uid=uid,
                    summary=summary,
                    status=status,
                    description=f"Amount: {amount}",
                )
            )
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the Grocy shopping list."""

        def _add_item():
            # Grocy requires a Product ID to add to the shopping list.
            # We search the Grocy database for a product name that matches what the user typed.
            try:
                all_products = self.coordinator.grocy_api.stock.all_products()
            except Exception as e:
                raise HomeAssistantError(
                    f"Could not fetch Grocy product database: {e}"
                ) from e

            target_id = None
            for p in all_products:
                if getattr(p, "name", "").lower() == item.summary.lower():
                    target_id = getattr(p, "id", None)
                    break

            if not target_id:
                raise ValueError(
                    f"Product '{item.summary}' does not exist in your Grocy database. "
                    "Please spell it exactly as it appears in Grocy."
                )

            # Add it to Grocy!
            self.coordinator.grocy_api.shopping_list.add_product(product_id=target_id)

        await self.hass.async_add_executor_job(_add_item)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a To-Do item (Mark as done or undone)."""

        def _update_item():
            is_done = item.status == TodoItemStatus.COMPLETED
            try:
                item_id = int(item.uid)
                self.coordinator.grocy_api.shopping_list.mark_item_done(
                    item_id, is_done
                )
            except Exception as e:
                LOGGER.error("Failed to update Grocy shopping list item: %s", e)
                raise HomeAssistantError(f"Failed to update item: {e}") from e

        await self.hass.async_add_executor_job(_update_item)
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete To-Do items from the shopping list."""

        def _delete_items():
            data = self.coordinator.data.get(ATTR_SHOPPING_LIST, [])
            for uid in uids:
                # Find the Grocy product ID associated with this To-Do UID
                target = next(
                    (x for x in data if str(getattr(x, "id", "")) == uid), None
                )
                if target:
                    product_id = getattr(target, "product_id", None)
                    amount = getattr(target, "amount", 1)
                    if product_id:
                        self.coordinator.grocy_api.shopping_list.remove_product(
                            product_id, amount=amount
                        )

        await self.hass.async_add_executor_job(_delete_items)
        await self.coordinator.async_request_refresh()
