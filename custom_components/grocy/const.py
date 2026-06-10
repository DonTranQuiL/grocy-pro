"""Constants for Grocy."""

from datetime import timedelta
import logging
from typing import Final

LOGGER = logging.getLogger(__package__)

NAME: Final = "Grocy"
DOMAIN: Final = "grocy"
VERSION: Final = "2.0.0"

ISSUE_URL: Final = "https://github.com/DonTranquiL/grocy/issues"

PLATFORMS: Final = ["binary_sensor", "sensor", "todo"]
SCAN_INTERVAL: Final = timedelta(seconds=30)

DEFAULT_PORT: Final = 9192
CONF_URL: Final = "url"
CONF_PORT: Final = "port"
CONF_API_KEY: Final = "api_key"
CONF_VERIFY_SSL: Final = "verify_ssl"

# Units
CHORES: Final = "Chore(s)"
MEAL_PLANS: Final = "Meal(s)"
PRODUCTS: Final = "Product(s)"
TASKS: Final = "Task(s)"
ITEMS: Final = "Item(s)"

# Attributes/Keys
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
