"""Fetching data from Grocy and proxying its pictures."""

from __future__ import annotations

import base64
import binascii
from datetime import date, datetime
from typing import Any

from aiohttp import ClientError, ClientTimeout, hdrs, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DOMAIN,
    LOGGER,
    PICTURE_TYPES,
    PICTURE_URL,
    REQUEST_TIMEOUT,
)
from .helpers import MealPlanItemWrapper, ProductWrapper
from .vendor.grocy.data_models.generic import EntityType
from .vendor.grocy.data_models.product import Product
from .vendor.grocy.grocy import Grocy


def _is_past(value: Any, now: datetime) -> bool:
    """Return True if a Grocy date/datetime lies before `now` (local, naive)."""
    if value is None:
        return False
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value < now
    if isinstance(value, date):
        return value < now.date()
    return False


def fetch_grocy_data(api: Grocy, keys: list[str]) -> dict[str, Any]:
    """Fetch everything the enabled entities need (runs in the executor).

    Uses one /stock/volatile call for the four product buckets and derives the
    overdue chores, tasks and batteries locally instead of asking Grocy twice.
    """
    wanted = set(keys)
    now = datetime.now()
    data: dict[str, Any] = {}

    if ATTR_STOCK in wanted:
        # grocy-py's Product models drop picture_file_name, so read the raw
        # product objects (the same single /objects/products call).
        pictures = {
            int(product["id"]): product["picture_file_name"]
            for product in api.generic.list(EntityType.PRODUCTS) or []
            if product.get("picture_file_name")
        }
        data[ATTR_STOCK] = [
            ProductWrapper(item, pictures.get(item.id)) for item in api.stock.current()
        ]

    if wanted & {
        ATTR_EXPIRING_PRODUCTS,
        ATTR_EXPIRED_PRODUCTS,
        ATTR_OVERDUE_PRODUCTS,
        ATTR_MISSING_PRODUCTS,
    }:
        volatile = api.stock.volatile()
        data[ATTR_EXPIRING_PRODUCTS] = [
            Product.from_stock_response(r) for r in volatile.due_products or []
        ]
        data[ATTR_OVERDUE_PRODUCTS] = [
            Product.from_stock_response(r) for r in volatile.overdue_products or []
        ]
        data[ATTR_EXPIRED_PRODUCTS] = [
            Product.from_stock_response(r) for r in volatile.expired_products or []
        ]
        data[ATTR_MISSING_PRODUCTS] = [
            Product.from_missing_response(r) for r in volatile.missing_products or []
        ]

    if ATTR_SHOPPING_LIST in wanted:
        data[ATTR_SHOPPING_LIST] = api.shopping_list.items(get_details=True)

    if wanted & {ATTR_TASKS, ATTR_OVERDUE_TASKS}:
        tasks = [task for task in api.tasks.list() if not task.done]
        data[ATTR_TASKS] = tasks
        data[ATTR_OVERDUE_TASKS] = [t for t in tasks if _is_past(t.due_date, now)]

    if wanted & {ATTR_CHORES, ATTR_OVERDUE_CHORES}:
        chores = api.chores.list(get_details=True)
        data[ATTR_CHORES] = chores
        data[ATTR_OVERDUE_CHORES] = [
            c for c in chores if _is_past(c.next_estimated_execution_time, now)
        ]

    if ATTR_MEAL_PLAN in wanted:
        items = api.meal_plan.items(
            get_details=True, query_filters=[f"day>={now.date().isoformat()}"]
        )
        data[ATTR_MEAL_PLAN] = sorted(
            (MealPlanItemWrapper(item) for item in items),
            key=lambda item: item.meal_plan.day or date.max,
        )

    if wanted & {ATTR_BATTERIES, ATTR_OVERDUE_BATTERIES}:
        batteries = api.batteries.list(get_details=True)
        data[ATTR_BATTERIES] = batteries
        data[ATTR_OVERDUE_BATTERIES] = [
            b for b in batteries if _is_past(b.next_estimated_charge_time, now)
        ]

    return {key: value for key, value in data.items() if key in wanted}


class GrocyPictureView(HomeAssistantView):
    """Proxy product and recipe pictures from Grocy.

    Unauthenticated so <img> tags in dashboards work, but limited to the two
    picture folders and to base64 file names, so it cannot be used to read other
    Grocy files.
    """

    requires_auth = False
    url = PICTURE_URL
    name = f"api:{DOMAIN}:picture"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        self.hass = hass

    async def get(
        self, request: web.Request, picture_type: str, filename: str
    ) -> web.StreamResponse:
        """Return the picture."""
        if picture_type not in PICTURE_TYPES:
            return web.Response(status=404)
        try:
            base64.b64decode(filename, validate=True)
        except (binascii.Error, ValueError):
            return web.Response(status=400)
        try:
            width = max(16, min(int(request.query.get("width", "400")), 2000))
        except ValueError:
            width = 400

        entries = self.hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            return web.Response(status=503)
        connection = entries[0].runtime_data.connection

        url = f"{connection.api_url}/files/{picture_type}/{filename}"
        params = {"force_serve_as": "picture", "best_fit_width": str(width)}
        session = async_get_clientsession(self.hass, verify_ssl=connection.verify_ssl)
        try:
            async with session.get(
                url,
                params=params,
                headers={**connection.headers, "accept": "*/*"},
                timeout=ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    return web.Response(status=resp.status)
                # No Content-Length/-Encoding: aiohttp already decompressed
                # the body, so passing them on would corrupt the image.
                headers = {
                    name: resp.headers[name]
                    for name in (hdrs.CACHE_CONTROL, hdrs.CONTENT_TYPE)
                    if name in resp.headers
                }
                return web.Response(body=await resp.read(), headers=headers)
        except (ClientError, TimeoutError) as err:
            LOGGER.debug("Could not fetch Grocy picture: %s", err)
            return web.Response(status=502)
