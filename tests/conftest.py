"""Shared fixtures: a fake Grocy server replaying recorded demo.grocy.info data."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import requests
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grocy_pro.const import DOMAIN

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "demo_api.json").read_text("utf-8")
)
# Responses recorded from https://demo.grocy.info (Grocy 4.7.1) on 2026-10-08.
FROZEN_TIME = "2026-10-08 08:38:00"

ENTRY_DATA = {
    "url": "http://grocy.local",
    "api_key": "secret-key",
    "port": 9192,
    "verify_ssl": False,
}
API_URL = "http://grocy.local:9192/api"


class FakeResponse:
    """Just enough of requests.Response for grocy-py."""

    def __init__(self, status: int = 200, payload: Any = None, text: str | None = None):
        self.status_code = status
        if text is None:
            text = "" if payload is None else json.dumps(payload)
        self.text = text
        self.content = text.encode()

    def json(self) -> Any:
        return json.loads(self.text)


class FakeGrocyServer:
    """Route grocy-py's requests calls to recorded responses."""

    def __init__(self) -> None:
        self.routes: dict[str, Any] = json.loads(json.dumps(FIXTURE))
        self.calls: list[tuple[str, str, Any]] = []
        self.fail: int | Exception | None = None
        self.timeouts: list[Any] = []

    def calls_for(self, method: str) -> list[tuple[str, Any]]:
        return [(path, body) for m, path, body in self.calls if m == method]

    def handle(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        path = urlparse(url).path.split("/api/", 1)[1]
        self.timeouts.append(kwargs.get("timeout"))
        body = kwargs.get("json")
        if body is None and kwargs.get("data") is not None:
            body = json.loads(kwargs["data"])
        self.calls.append((method, path, body))
        if isinstance(self.fail, Exception):
            raise self.fail
        if self.fail is not None:
            return FakeResponse(self.fail, {"error_message": "boom"})
        if method != "GET":
            return FakeResponse(204)
        if path not in self.routes:
            return FakeResponse(404, {"error_message": f"{path} not found"})
        value = self.routes[path]
        if isinstance(value, dict) and set(value) == {"text"}:
            return FakeResponse(text=value["text"])
        return FakeResponse(payload=value)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations automatically for all tests."""
    return


@pytest.fixture
def grocy_server(monkeypatch: pytest.MonkeyPatch) -> FakeGrocyServer:
    """Patch requests so grocy-py talks to the fake server."""
    server = FakeGrocyServer()
    for method in ("get", "post", "put", "delete"):

        def _call(url: str, *args: Any, _m: str = method, **kwargs: Any):
            return server.handle(_m.upper(), url, **kwargs)

        monkeypatch.setattr(requests, method, _call)
    return server


@pytest.fixture
def frozen(freezer):
    """Freeze time at the moment the fixture data was recorded."""
    freezer.move_to(FROZEN_TIME)
    return freezer


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """A Grocy Pro config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Grocy Pro",
        data=dict(ENTRY_DATA),
        entry_id="grocy_entry",
    )


@pytest.fixture
def setup_integration(hass, mock_entry, grocy_server, frozen) -> Callable[[], Any]:
    """Return a coroutine function that sets up the integration."""

    async def _setup() -> MockConfigEntry:
        mock_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()
        return mock_entry

    return _setup
