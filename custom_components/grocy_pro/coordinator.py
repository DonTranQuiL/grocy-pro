"""Data update coordinator for Grocy Pro."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    FEATURE_ENTITIES,
    FULL_REFRESH_INTERVAL,
    LOGGER,
    SCAN_INTERVAL,
)
from .grocy_data import fetch_grocy_data
from .helpers import GrocyConnection, connection_from_data, ensure_request_timeout
from .vendor.grocy.errors import GrocyError
from .vendor.grocy.grocy import Grocy

type GrocyConfigEntry = ConfigEntry[GrocyDataUpdateCoordinator]


class GrocyAuthError(Exception):
    """Grocy rejected the API key."""


class GrocyConnectionError(Exception):
    """Grocy could not be reached or answered with an error."""


def call_grocy(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Call grocy-py and translate its errors (runs in the executor)."""
    try:
        return func(*args, **kwargs)
    except GrocyError as err:
        if err.status_code in (401, 403):
            raise GrocyAuthError(str(err.message or err.status_code)) from err
        raise GrocyConnectionError(
            f"Grocy answered HTTP {err.status_code}: {err.message}"
        ) from err
    except ValueError as err:  # non-JSON error page (proxy, wrong path)
        raise GrocyConnectionError(f"Unexpected response from Grocy: {err}") from err
    except requests.RequestException as err:
        raise GrocyConnectionError(f"Cannot reach Grocy: {err}") from err


@dataclass
class UpdateStats:
    """Bookkeeping for diagnostics."""

    last_full_refresh: datetime | None = None
    last_db_changed: datetime | None = None
    full_refreshes: int = 0
    skipped_refreshes: int = 0
    feature_flags: list[str] = field(default_factory=list)


class GrocyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Grocy data, but only when Grocy says something changed."""

    config_entry: GrocyConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GrocyConfigEntry) -> None:
        """Initialise."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.connection: GrocyConnection = connection_from_data(dict(entry.data))
        ensure_request_timeout()
        self.grocy_api = Grocy(
            self.connection.base_url,
            self.connection.api_key,
            port=self.connection.port,
            path=self.connection.path or None,
            verify_ssl=self.connection.verify_ssl,
        )
        self.available_entities: list[str] = []
        self.stats = UpdateStats()
        self._force_full = True

    async def _async_setup(self) -> None:
        """Read Grocy's feature flags once (called by the first refresh)."""
        try:
            config = await self.hass.async_add_executor_job(
                call_grocy, self.grocy_api.system.config
            )
        except GrocyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GrocyConnectionError as err:
            raise UpdateFailed(str(err)) from err

        if config is None:
            LOGGER.warning("Grocy returned no configuration, enabling all features")
            features = list(FEATURE_ENTITIES)
        else:
            features = list(config.enabled_features)
        self.stats.feature_flags = features
        self.available_entities = [
            key
            for flag, keys in FEATURE_ENTITIES.items()
            if flag in features
            for key in keys
        ]

    def request_full_refresh(self) -> None:
        """Make the next update fetch everything, even without a DB change."""
        self._force_full = True

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Grocy."""
        try:
            changed = await self.hass.async_add_executor_job(
                call_grocy, self.grocy_api.system.db_changed_time
            )
            now = dt_util.utcnow()
            stale = (
                self.stats.last_full_refresh is None
                or now - self.stats.last_full_refresh >= FULL_REFRESH_INTERVAL
            )
            if (
                self.data is not None
                and not self._force_full
                and not stale
                and changed is not None
                and changed == self.stats.last_db_changed
            ):
                self.stats.skipped_refreshes += 1
                return self.data

            data = await self.hass.async_add_executor_job(
                call_grocy, fetch_grocy_data, self.grocy_api, self.available_entities
            )
        except GrocyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GrocyConnectionError as err:
            raise UpdateFailed(str(err)) from err

        self._force_full = False
        self.stats.last_db_changed = changed
        self.stats.last_full_refresh = now
        self.stats.full_refreshes += 1
        return data
