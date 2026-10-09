"""Config flow for Grocy Pro."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_API_KEY,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DOMAIN,
    LEGACY_DOMAIN,
    LOGGER,
    NAME,
    REQUEST_TIMEOUT,
)
from .helpers import connection_from_data

CONNECTION_KEYS = (CONF_URL, CONF_API_KEY, CONF_PORT, CONF_VERIFY_SSL)


def _schema(include_key: bool = True) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(CONF_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
    if include_key:
        fields[vol.Required(CONF_API_KEY)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    fields[vol.Optional(CONF_PORT, default=DEFAULT_PORT)] = NumberSelector(
        NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_VERIFY_SSL, default=False)] = bool
    return vol.Schema(fields)


def _clean(data: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the connection fields, with sane types."""
    return {
        CONF_URL: str(data.get(CONF_URL, "")).strip(),
        CONF_API_KEY: str(data.get(CONF_API_KEY, "")).strip(),
        CONF_PORT: int(data.get(CONF_PORT) or DEFAULT_PORT),
        CONF_VERIFY_SSL: bool(data.get(CONF_VERIFY_SSL, False)),
    }


class GrocyFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Grocy Pro."""

    VERSION = 1

    async def _async_validate(self, data: Mapping[str, Any]) -> str | None:
        """Check the connection. Return an error key, or None when it works."""
        connection = connection_from_data(dict(data))
        session = async_get_clientsession(self.hass, verify_ssl=connection.verify_ssl)
        try:
            async with session.get(
                f"{connection.api_url}/system/info",
                headers=connection.headers,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    return "invalid_auth"
                if response.status != 200:
                    LOGGER.debug("Grocy answered HTTP %s", response.status)
                    return "invalid_url"
                info = await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            LOGGER.debug("Cannot connect to Grocy: %s", err)
            return "cannot_connect"
        except ValueError:
            return "invalid_url"
        if not isinstance(info, dict) or "grocy_version" not in info:
            return "invalid_url"
        return None

    def _legacy_entry(self) -> ConfigEntry | None:
        """Return a config entry of the old `grocy` integration, if any."""
        for entry in self.hass.config_entries.async_entries(LEGACY_DOMAIN):
            if entry.data.get(CONF_URL) and entry.data.get(CONF_API_KEY):
                return entry
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start: offer to move an old Grocy setup over, or set up manually."""
        if user_input is None and self._legacy_entry() is not None:
            return self.async_show_menu(
                step_id="user", menu_options=["import_legacy", "manual"]
            )
        return await self.async_step_manual(user_input)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter the Grocy connection details."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            if not (error := await self._async_validate(data)):
                return self.async_create_entry(title=NAME, data=data)
            errors["base"] = error
        suggested: Mapping[str, Any] = user_input or {}
        if not suggested and (legacy := self._legacy_entry()):
            suggested = {k: v for k, v in legacy.data.items() if k in CONNECTION_KEYS}
        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(_schema(), suggested),
            errors=errors,
        )

    async def async_step_import_legacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Move the old `grocy` entry over and remove it."""
        legacy = self._legacy_entry()
        if legacy is None:
            return self.async_abort(reason="no_legacy_entry")
        data = _clean(legacy.data)
        if user_input is None:
            return self.async_show_form(
                step_id="import_legacy",
                description_placeholders={"url": data[CONF_URL]},
            )
        if error := await self._async_validate(data):
            return self.async_show_form(
                step_id="manual",
                data_schema=self.add_suggested_values_to_schema(_schema(), data),
                errors={"base": error},
            )
        # Removing the old entry first frees its entity IDs, so the new
        # entities come back as sensor.grocy_* with their history intact.
        await self.hass.config_entries.async_remove(legacy.entry_id)
        return self.async_create_entry(title=NAME, data=data)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Grocy rejected the API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean({**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]})
            if not (error := await self._async_validate(data)):
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={"url": entry.data.get(CONF_URL, "")},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the URL, port, SSL check or API key."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            if not (error := await self._async_validate(data)):
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _schema(), user_input or entry.data
            ),
            errors=errors,
        )
