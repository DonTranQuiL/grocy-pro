"""Coordinator: change detection, refresh rules and error mapping."""

from __future__ import annotations

from datetime import timedelta

import pytest
import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.grocy_pro.coordinator import (
    GrocyAuthError,
    GrocyConnectionError,
    call_grocy,
)


def _full_fetches(server) -> int:
    return sum(1 for m, path, _ in server.calls if m == "GET" and path == "stock")


async def test_skips_fetch_without_db_change(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Without a database change only db-changed-time is polled."""
    entry = await setup_integration()
    coordinator = entry.runtime_data
    assert _full_fetches(grocy_server) == 1

    await coordinator.async_refresh()
    assert _full_fetches(grocy_server) == 1
    assert coordinator.stats.skipped_refreshes == 1


async def test_fetches_after_db_change(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """A new db-changed-time triggers a full fetch."""
    entry = await setup_integration()
    grocy_server.routes["system/db-changed-time"] = {
        "changed_time": "2026-10-08 10:40:00"
    }
    await entry.runtime_data.async_refresh()
    assert _full_fetches(grocy_server) == 2


async def test_full_refresh_when_stale(
    hass: HomeAssistant, setup_integration, grocy_server, frozen
) -> None:
    """Every five minutes everything is fetched so due dates roll over."""
    entry = await setup_integration()
    frozen.tick(timedelta(minutes=6))
    await entry.runtime_data.async_refresh()
    assert _full_fetches(grocy_server) == 2


async def test_request_full_refresh(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Actions force the next refresh to fetch everything."""
    entry = await setup_integration()
    entry.runtime_data.request_full_refresh()
    await entry.runtime_data.async_refresh()
    assert _full_fetches(grocy_server) == 2


async def test_update_errors(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Errors during updates mark entities unavailable, auth errors reauth."""
    entry = await setup_integration()
    coordinator = entry.runtime_data

    grocy_server.fail = requests.Timeout("slow")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    grocy_server.fail = 500
    with pytest.raises(UpdateFailed, match="HTTP 500"):
        await coordinator._async_update_data()

    grocy_server.fail = 401
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    grocy_server.fail = None
    grocy_server.fail = 503
    await coordinator.async_refresh()
    assert hass.states.get("sensor.grocy_stock").state == "unavailable"
    grocy_server.fail = None
    coordinator.request_full_refresh()
    await coordinator.async_refresh()
    assert hass.states.get("sensor.grocy_stock").state == "22"


class _Resp:
    def __init__(self, status: int, text: str) -> None:
        self.status_code = status
        self.text = text
        self.content = text.encode()

    def json(self):
        import json

        return json.loads(self.text)


def test_call_grocy_error_mapping() -> None:
    """grocy-py errors become our two error types."""
    from custom_components.grocy_pro.vendor.grocy.errors import GrocyError

    def raise_(exc):
        def _f():
            raise exc

        return _f

    with pytest.raises(GrocyAuthError):
        call_grocy(raise_(GrocyError(_Resp(403, '{"error_message": "no"}'))))
    with pytest.raises(GrocyConnectionError, match="HTTP 404"):
        call_grocy(raise_(GrocyError(_Resp(404, '{"error_message": "x"}'))))
    with pytest.raises(GrocyConnectionError, match="Unexpected response"):
        call_grocy(raise_(ValueError("<html>")))
    with pytest.raises(GrocyConnectionError, match="Cannot reach"):
        call_grocy(raise_(requests.ConnectionError("down")))
    assert call_grocy(lambda a, b=0: a + b, 1, b=2) == 3
