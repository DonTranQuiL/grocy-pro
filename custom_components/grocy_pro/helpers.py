"""Helpers for Grocy Pro."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .const import (
    CONF_API_KEY,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    PICTURE_URL,
    REQUEST_TIMEOUT,
)


@dataclass(frozen=True)
class GrocyConnection:
    """Normalised connection settings for a Grocy server."""

    base_url: str  # scheme://host, without port or path
    port: int
    path: str  # optional sub path, without slashes
    api_key: str
    verify_ssl: bool

    @property
    def root_url(self) -> str:
        """Return scheme://host:port[/path]."""
        root = f"{self.base_url}:{self.port}"
        return f"{root}/{self.path}" if self.path else root

    @property
    def api_url(self) -> str:
        """Return the REST API root, ending in /api."""
        return f"{self.root_url}/api"

    @property
    def headers(self) -> dict[str, str]:
        """Return the headers Grocy expects."""
        return {"GROCY-API-KEY": self.api_key, "accept": "application/json"}


def extract_base_url_and_path(url: str) -> tuple[str, str]:
    """Split a URL into scheme://host and the path (without port)."""
    if "://" not in url:
        url = f"http://{url}"
    parsed = urlparse(url.strip())
    host = parsed.hostname or ""
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    return f"{parsed.scheme}://{host}", parsed.path.strip("/")


def connection_from_data(data: dict[str, Any]) -> GrocyConnection:
    """Build normalised connection settings from config entry data.

    A port typed into the URL wins over the separate port field. Older setups
    that did this ended up with a doubled port (host:9192:9192) in API calls.
    """
    raw_url = str(data.get(CONF_URL, "")).strip()
    if "://" not in raw_url:
        raw_url = f"http://{raw_url}"
    parsed = urlparse(raw_url)
    try:
        url_port = parsed.port
    except ValueError:
        url_port = None
    base_url, path = extract_base_url_and_path(raw_url)
    port = url_port or int(data.get(CONF_PORT) or DEFAULT_PORT)
    return GrocyConnection(
        base_url=base_url,
        port=port,
        path=path,
        api_key=str(data.get(CONF_API_KEY, "")).strip(),
        verify_ssl=bool(data.get(CONF_VERIFY_SSL, False)),
    )


def picture_path(picture_type: str, file_name: str | None) -> str | None:
    """Return the Home Assistant proxy path for a Grocy picture."""
    if not file_name:
        return None
    encoded = base64.b64encode(file_name.encode("utf-8")).decode("ascii")
    return PICTURE_URL.format(picture_type=picture_type, filename=encoded)


def as_attribute(obj: Any) -> Any:
    """Convert a grocy-py model (or wrapper) into JSON-safe attribute data."""
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", warnings=False)
    if isinstance(obj, dict):
        return obj
    return vars(obj)


class ProductWrapper:
    """A stock product plus the proxied picture URL."""

    def __init__(self, product: Any, picture_file_name: str | None = None) -> None:
        """Initialise."""
        self.product = product
        self.picture_url = picture_path(
            "productpictures",
            picture_file_name or getattr(product, "picture_file_name", None),
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the wrapped product."""
        return getattr(self.product, name)

    def as_dict(self) -> dict[str, Any]:
        """Return attribute data including the picture URL."""
        props = self.product.model_dump(mode="json", warnings=False)
        props["picture_url"] = self.picture_url
        return props


class MealPlanItemWrapper:
    """A meal plan item plus the proxied recipe picture URL."""

    def __init__(self, meal_plan: Any) -> None:
        """Initialise."""
        self.meal_plan = meal_plan
        recipe = getattr(meal_plan, "recipe", None)
        self.picture_url = picture_path(
            "recipepictures", getattr(recipe, "picture_file_name", None)
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the wrapped item."""
        return getattr(self.meal_plan, name)

    def as_dict(self) -> dict[str, Any]:
        """Return attribute data including the picture URL."""
        props = self.meal_plan.model_dump(mode="json", warnings=False)
        props["picture_url"] = self.picture_url
        return props


class _RequestsWithTimeout:
    """`requests` stand-in for grocy-py that adds a default timeout.

    grocy-py calls requests.get/post/put/delete without a timeout, so a Grocy
    server that accepts the connection but never answers would block an
    executor thread (and every later update) forever.
    """

    def __init__(self, module: Any, timeout: float) -> None:
        """Wrap the real requests module."""
        self._module = module
        self._timeout = timeout

    def __getattr__(self, name: str) -> Any:
        """Pass everything else through (exceptions, Session, ...)."""
        attr = getattr(self._module, name)
        if name in ("get", "post", "put", "delete"):

            def call(*args: Any, **kwargs: Any) -> Any:
                kwargs.setdefault("timeout", self._timeout)
                return attr(*args, **kwargs)

            return call
        return attr


def ensure_request_timeout() -> None:
    """Give grocy-py's HTTP calls a timeout (idempotent)."""
    from grocy import grocy_api_client  # noqa: PLC0415

    if not isinstance(grocy_api_client.requests, _RequestsWithTimeout):
        grocy_api_client.requests = _RequestsWithTimeout(
            grocy_api_client.requests, REQUEST_TIMEOUT
        )
