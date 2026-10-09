"""Constants for Grocy Pro."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

LOGGER = logging.getLogger(__package__)

DOMAIN: Final = "grocy_pro"
NAME: Final = "Grocy Pro"
VERSION: Final = "3.0.0b1"

# The device keeps the plain "Grocy" name so entity IDs stay sensor.grocy_*,
# exactly as with the old `grocy` domain. Dashboards and the card keep working.
DEVICE_NAME: Final = "Grocy"
MANUFACTURER: Final = "Grocy"

# The old domain this integration used before 3.0. Its config entries can be
# moved over from the config flow.
LEGACY_DOMAIN: Final = "grocy"

PLATFORMS: Final = ["binary_sensor", "calendar", "sensor", "todo"]

# Cheap poll of /system/db-changed-time; the full data set is only fetched when
# Grocy reports a change, or at least every FULL_REFRESH_INTERVAL so time-based
# states (overdue, due soon) roll over.
SCAN_INTERVAL: Final = timedelta(seconds=30)
FULL_REFRESH_INTERVAL: Final = timedelta(minutes=5)
CALENDAR_REFRESH_INTERVAL: Final = timedelta(minutes=15)
REQUEST_TIMEOUT: Final = 20

DEFAULT_PORT: Final = 9192
CONF_URL: Final = "url"
CONF_PORT: Final = "port"
CONF_API_KEY: Final = "api_key"
CONF_VERIFY_SSL: Final = "verify_ssl"

PICTURE_URL: Final = f"/api/{DOMAIN}/{{picture_type}}/{{filename}}"
PICTURE_TYPES: Final = ("productpictures", "recipepictures")
CARD_FILENAME: Final = "grocy-action-card.js"
CARD_URL: Final = f"/{DOMAIN}/{CARD_FILENAME}"

# Units
CHORES: Final = "Chore(s)"
MEAL_PLANS: Final = "Meal(s)"
PRODUCTS: Final = "Product(s)"
TASKS: Final = "Task(s)"
ITEMS: Final = "Item(s)"

# Data keys (also the entity description keys and unique ID suffixes)
ATTR_BATTERIES: Final = "batteries"
ATTR_CHORES: Final = "chores"
ATTR_EXPIRED_PRODUCTS: Final = "expired_products"
ATTR_EXPIRING_PRODUCTS: Final = "expiring_products"
ATTR_MEAL_PLAN: Final = "meal_plan"
ATTR_MISSING_PRODUCTS: Final = "missing_products"
ATTR_OVERDUE_BATTERIES: Final = "overdue_batteries"
ATTR_OVERDUE_CHORES: Final = "overdue_chores"
ATTR_OVERDUE_PRODUCTS: Final = "overdue_products"
ATTR_OVERDUE_TASKS: Final = "overdue_tasks"
ATTR_SHOPPING_LIST: Final = "shopping_list"
ATTR_STOCK: Final = "stock"
ATTR_TASKS: Final = "tasks"

FEATURE_ENTITIES: Final = {
    "FEATURE_FLAG_STOCK": (
        ATTR_STOCK,
        ATTR_MISSING_PRODUCTS,
        ATTR_EXPIRED_PRODUCTS,
        ATTR_EXPIRING_PRODUCTS,
        ATTR_OVERDUE_PRODUCTS,
    ),
    "FEATURE_FLAG_SHOPPINGLIST": (ATTR_SHOPPING_LIST,),
    "FEATURE_FLAG_TASKS": (ATTR_TASKS, ATTR_OVERDUE_TASKS),
    "FEATURE_FLAG_CHORES": (ATTR_CHORES, ATTR_OVERDUE_CHORES),
    "FEATURE_FLAG_RECIPES": (ATTR_MEAL_PLAN,),
    "FEATURE_FLAG_BATTERIES": (ATTR_BATTERIES, ATTR_OVERDUE_BATTERIES),
}
