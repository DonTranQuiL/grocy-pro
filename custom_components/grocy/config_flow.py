"""Adds config flow for Grocy."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DOMAIN,
    LOGGER,
    NAME,
)
from .helpers import extract_base_url_and_path


class GrocyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Grocy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_URL],
                user_input[CONF_API_KEY],
                user_input.get(CONF_PORT, DEFAULT_PORT),
                user_input.get(CONF_VERIFY_SSL, False),
            )

            if valid:
                return self.async_create_entry(title=NAME, data=user_input)

            self._errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=self._errors,
        )

    def _get_schema(self) -> vol.Schema:
        """Return the schema for the config flow."""
        return vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_VERIFY_SSL, default=False): bool,
            }
        )

    async def _test_credentials(
        self, url: str, api_key: str, port: int, verify_ssl: bool
    ) -> bool:
        """Return true if credentials are valid using Native REST bypass."""
        try:
            base_url, path = extract_base_url_and_path(url)
            # 1. Strip any invisible trailing spaces/newlines from copy-pasting
            clean_api_key = api_key.strip()

            # Construct the raw API URL manually
            # Safety check: Prevent duplicating the port if it was typed into the URL field
            if str(port) not in base_url:
                api_url = f"{base_url}:{port}"
            else:
                api_url = base_url

            if path:
                api_url += f"/{path}"

            # 2. Pass the key as a query parameter to bypass strict proxy header stripping
            api_url += f"/api/system/info?GROCY-API-KEY={clean_api_key}"

            headers = {"GROCY-API-KEY": clean_api_key, "accept": "application/json"}

            session = async_get_clientsession(self.hass)

            async with session.get(
                api_url, headers=headers, ssl=verify_ssl
            ) as response:
                if response.status == 200:
                    return True

                # 3. Read the EXACT error message from Grocy so we know why it's failing
                error_text = await response.text()
                LOGGER.error(
                    "Grocy native auth failed. URL: %s | Status: %s | Response: %s",
                    api_url,
                    response.status,
                    error_text,
                )
                return False

        except Exception as error:
            LOGGER.error("Failed to authenticate with Grocy natively: %s", error)
            return False
