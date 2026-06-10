"""Communication with Grocy API."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aiohttp import hdrs, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from grocy.grocy import Grocy

from .const import (
    ATTR_BATTERIES,
    ATTR_CHORES,
    ATTR_EXPIRED_PRODUCTS,
    ATTR_EXPIRING_PRODUCTS,
    ATTR_MEAL_PLAN,
    ATTR_MISSING_PRODUCTS,
    ATTR_OVERDUE_BATTERIES,
    ATTR_OVERDUE_CHORES,
    ATTR_OVERDUE_PRODUCTS,
    ATTR_OVERDUE_TASKS,
    ATTR_SHOPPING_LIST,
    ATTR_STOCK,
    ATTR_TASKS,
    CONF_API_KEY,
    CONF_PORT,
    CONF_URL,
    LOGGER,
)
from .helpers import MealPlanItemWrapper, ProductWrapper, extract_base_url_and_path


class GrocyData:
    """Handles communication and gets the data."""

    def __init__(self, hass: HomeAssistant, api: Grocy) -> None:
        """Initialize Grocy data."""
        self.hass = hass
        self.api = api

    def _safe_get(self, manager: Any, **kwargs) -> Any:
        """Fallback adapter for undocumented endpoints like chores/batteries."""
        probe_methods = (
            "current",
            "items",
            "all",
            "get_all",
            "list",
            "tasks",
            "chores",
        )
        for method_name in probe_methods:
            if hasattr(manager, method_name):
                method = getattr(manager, method_name)
                if callable(method):
                    try:
                        return method(**kwargs)
                    except TypeError as err:
                        if "positional argument" in str(err) or "required" in str(err):
                            continue
                        raise
        if callable(manager):
            try:
                return manager(**kwargs)
            except TypeError as err:
                if "positional argument" not in str(err) and "required" not in str(err):
                    raise
        return []

    async def async_update_data(self, entity_key: str) -> Any:
        """Update data by routing to the correct method."""
        update_methods = {
            ATTR_STOCK: self.async_update_stock,
            ATTR_CHORES: self.async_update_chores,
            ATTR_TASKS: self.async_update_tasks,
            ATTR_SHOPPING_LIST: self.async_update_shopping_list,
            ATTR_EXPIRING_PRODUCTS: self.async_update_expiring_products,
            ATTR_EXPIRED_PRODUCTS: self.async_update_expired_products,
            ATTR_OVERDUE_PRODUCTS: self.async_update_overdue_products,
            ATTR_MISSING_PRODUCTS: self.async_update_missing_products,
            ATTR_MEAL_PLAN: self.async_update_meal_plan,
            ATTR_OVERDUE_CHORES: self.async_update_overdue_chores,
            ATTR_OVERDUE_TASKS: self.async_update_overdue_tasks,
            ATTR_BATTERIES: self.async_update_batteries,
            ATTR_OVERDUE_BATTERIES: self.async_update_overdue_batteries,
        }

        if entity_key in update_methods:
            return await update_methods[entity_key]()

    # --- EXACT MAPPINGS FROM SOURCE CODE ---

    async def async_update_stock(self) -> list[ProductWrapper]:
        def wrapper() -> list[ProductWrapper]:
            return [ProductWrapper(item) for item in self.api.stock.current()]

        return await self.hass.async_add_executor_job(wrapper)

    async def async_update_tasks(self) -> Any:
        return await self.hass.async_add_executor_job(lambda: self.api.tasks.list())

    async def async_update_overdue_tasks(self) -> Any:
        and_query_filter = [
            f"due_date<{datetime.now().date()}",
            "due_date\u00a7.*\\S.*",
        ]
        return await self.hass.async_add_executor_job(
            lambda: self.api.tasks.list(query_filters=and_query_filter)
        )

    async def async_update_shopping_list(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self.api.shopping_list.items(get_details=True)
        )

    # Note: get_details is forced to False here to bypass Pydantic null-unit crashes
    async def async_update_expiring_products(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self.api.stock.due_products(get_details=False)
        )

    async def async_update_expired_products(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self.api.stock.expired_products(get_details=False)
        )

    async def async_update_overdue_products(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self.api.stock.overdue_products(get_details=False)
        )

    async def async_update_missing_products(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self.api.stock.missing_products(get_details=False)
        )

    # --- FALLBACKS ---

    async def async_update_chores(self) -> Any:
        return await self.hass.async_add_executor_job(
            lambda: self._safe_get(self.api.chores, get_details=True)
        )

    async def async_update_overdue_chores(self) -> Any:
        query_filter = [f"next_estimated_execution_time<{datetime.now()}"]
        return await self.hass.async_add_executor_job(
            lambda: self._safe_get(
                self.api.chores, get_details=True, query_filters=query_filter
            )
        )

    async def async_get_config(self) -> Any:
        def wrapper():
            try:
                config = self.api.system.config()
                # If it successfully grabbed the config AND it has features, use it!
                if config and hasattr(config, "enabled_features"):
                    return config
            except Exception as err:
                LOGGER.warning("Grocy config check exception: %s", err)

            # If the library returned 'None' (due to the non-JSON bug) or crashed, use the fallback!
            LOGGER.warning(
                "Grocy config returned empty. Assuming all features are enabled."
            )

            class FallbackConfig:
                enabled_features = [
                    "FEATURE_FLAG_STOCK",
                    "FEATURE_FLAG_SHOPPINGLIST",
                    "FEATURE_FLAG_TASKS",
                    "FEATURE_FLAG_CHORES",
                    "FEATURE_FLAG_RECIPES",
                    "FEATURE_FLAG_BATTERIES",
                ]

            return FallbackConfig()

        return await self.hass.async_add_executor_job(wrapper)

    async def async_update_meal_plan(self) -> list[MealPlanItemWrapper]:
        yesterday = datetime.now() - timedelta(1)
        query_filter = [f"day>{yesterday.date()}"]

        def wrapper() -> list[MealPlanItemWrapper]:
            meal_plan = self._safe_get(
                self.api.meal_plan, get_details=True, query_filters=query_filter
            )
            plan = [MealPlanItemWrapper(item) for item in meal_plan]
            return sorted(
                plan,
                key=lambda item: (
                    getattr(item.meal_plan, "day", datetime.min)
                    if hasattr(item, "meal_plan")
                    else datetime.min
                ),
            )

        return await self.hass.async_add_executor_job(wrapper)

    async def async_update_batteries(self) -> list[Any]:
        return await self.hass.async_add_executor_job(
            lambda: self._safe_get(self.api.batteries, get_details=True)
        )

    async def async_update_overdue_batteries(self) -> list[Any]:
        filter_query = [f"next_estimated_charge_time<{datetime.now()}"]
        return await self.hass.async_add_executor_job(
            lambda: self._safe_get(
                self.api.batteries, query_filters=filter_query, get_details=True
            )
        )


async def async_setup_endpoint_for_image_proxy(
    hass: HomeAssistant, config_entry_data: dict[str, Any]
) -> None:
    session = async_get_clientsession(hass)
    url = config_entry_data.get(CONF_URL, "")
    grocy_base_url, grocy_path = extract_base_url_and_path(url)
    api_key = config_entry_data.get(CONF_API_KEY, "")
    port_number = config_entry_data.get(CONF_PORT, 9192)

    grocy_full_url = f"{grocy_base_url}:{port_number}"
    if grocy_path:
        grocy_full_url += f"/{grocy_path}"

    LOGGER.debug("Generated image api url to grocy: '%s'", grocy_full_url)
    hass.http.register_view(GrocyPictureView(session, grocy_full_url, api_key))


class GrocyPictureView(HomeAssistantView):
    requires_auth = False
    url = "/api/grocy/{picture_type}/{filename}"
    name = "api:grocy:picture"

    def __init__(self, session, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url
        self._api_key = api_key

    async def get(
        self, request: web.Request, picture_type: str, filename: str
    ) -> web.Response:
        width = request.query.get("width", "400")
        url = f"{self._base_url}/api/files/{picture_type}/{filename}?force_serve_as=picture&best_fit_width={width}"
        headers = {"GROCY-API-KEY": self._api_key, "accept": "*/*"}

        async with self._session.get(url, headers=headers) as resp:
            resp.raise_for_status()

            response_headers = {}
            for name, value in resp.headers.items():
                if name in (
                    hdrs.CACHE_CONTROL,
                    hdrs.CONTENT_DISPOSITION,
                    hdrs.CONTENT_LENGTH,
                    hdrs.CONTENT_TYPE,
                    hdrs.CONTENT_ENCODING,
                ):
                    response_headers[name] = value

            body = await resp.read()
            return web.Response(body=body, headers=response_headers)
