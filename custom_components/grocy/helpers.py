"""Helpers for Grocy."""

from __future__ import annotations

import base64
import datetime
from typing import Any
from urllib.parse import urlparse


def extract_base_url_and_path(url: str) -> tuple[str, str]:
    """Extract the base url and path from a given URL."""
    parsed_url = urlparse(url)
    return (f"{parsed_url.scheme}://{parsed_url.netloc}", parsed_url.path.strip("/"))


def serialize_datetime(obj: Any) -> Any:
    """Convert datetime objects to ISO strings for attributes."""
    if isinstance(obj, (datetime.date, datetime.time)):
        return obj.isoformat()
    return obj


class MealPlanItemWrapper:
    """Wrapper around the pygrocy MealPlanItem."""

    def __init__(self, meal_plan: Any) -> None:
        """Initialize."""
        self._meal_plan = meal_plan

    @property
    def meal_plan(self) -> Any:
        """The pygrocy MealPlanItem."""
        return self._meal_plan

    @property
    def picture_url(self) -> str | None:
        """Proxy URL to the picture."""
        # Dynamically check for recipe to avoid crashes
        recipe = getattr(self.meal_plan, "recipe", None)
        if recipe and getattr(recipe, "picture_file_name", None):
            b64name = base64.b64encode(recipe.picture_file_name.encode("ascii"))
            return f"/api/grocy/recipepictures/{str(b64name, 'utf-8')}"
        return None

    def as_dict(self) -> dict[str, Any]:
        """Return attributes for the pygrocy MealPlanItem object including picture URL."""
        if hasattr(self._meal_plan, "model_dump"):
            props = self._meal_plan.model_dump()
        elif hasattr(self._meal_plan, "as_dict"):
            props = self._meal_plan.as_dict()
        elif hasattr(self._meal_plan, "dict"):
            props = self._meal_plan.dict()
        else:
            props = vars(self._meal_plan)

        props["picture_url"] = self.picture_url
        return {k: serialize_datetime(v) for k, v in props.items()}


class ProductWrapper:
    """Wrapper around the pygrocy CurrentStockResponse."""

    def __init__(self, stock_response: Any) -> None:
        """Initialize."""
        self._stock_response = stock_response
        self._picture_url = self.get_picture_url(stock_response)

    @property
    def product(self) -> Any:
        """The pygrocy CurrentStockResponse."""
        return self._stock_response

    @property
    def picture_url(self) -> str | None:
        """Proxy URL to the picture."""
        return self._picture_url

    def get_picture_url(self, item: Any) -> str | None:
        """Generate Proxy URL to the picture dynamically."""
        picture_file_name = None

        # Handle both nested and flat objects so it never crashes
        if hasattr(item, "product") and hasattr(item.product, "picture_file_name"):
            picture_file_name = item.product.picture_file_name
        elif hasattr(item, "picture_file_name"):
            picture_file_name = item.picture_file_name

        if picture_file_name:
            b64name = base64.b64encode(picture_file_name.encode("ascii"))
            return f"/api/grocy/productpictures/{str(b64name, 'utf-8')}"
        return None

    def as_dict(self) -> dict[str, Any]:
        """Return attributes for the pygrocy Product object including picture URL."""
        if hasattr(self._stock_response, "model_dump"):
            props = self._stock_response.model_dump()
        elif hasattr(self._stock_response, "as_dict"):
            props = self._stock_response.as_dict()
        elif hasattr(self._stock_response, "dict"):
            props = self._stock_response.dict()
        else:
            props = vars(self._stock_response)

        props["picture_url"] = self.picture_url
        return {k: serialize_datetime(v) for k, v in props.items()}
