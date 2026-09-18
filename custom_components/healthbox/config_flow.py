"""Config flow for Renson Healthbox integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol


from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
from homeassistant.core import HomeAssistant, callback

from homeassistant.const import CONF_HOST, CONF_API_KEY
from pyhealthbox3.healthbox3 import (
    Healthbox3,
    Healthbox3ApiClientAuthenticationError,
    Healthbox3ApiClientCommunicationError,
    Healthbox3ApiClientError,
)

from .const import DOMAIN, LOGGER


async def _async_check_api_key(
    hass: HomeAssistant, host: str, api_key: str
) -> str | None:
    """Try the API key against the device; return an error key, or None if valid."""
    client = Healthbox3(
        host=host,
        api_key=api_key,
        session=async_get_clientsession(hass),
    )
    try:
        await client.async_enable_advanced_api_features()
    except Healthbox3ApiClientAuthenticationError as exception:
        LOGGER.warning(exception)
        return "auth"
    except Healthbox3ApiClientCommunicationError as exception:
        LOGGER.error(exception)
        return "connection"
    except Healthbox3ApiClientError as exception:
        LOGGER.exception(exception)
        return "unknown"
    return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Renson Healthbox."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input[CONF_HOST]}")
            self._abort_if_unique_id_configured()
            try:
                if CONF_API_KEY in user_input:
                    await self._test_credentials(
                        ipaddress=user_input[CONF_HOST],
                        apikey=user_input[CONF_API_KEY],
                    )
                else:
                    await self._test_connectivity(ipaddress=user_input[CONF_HOST])
            except Healthbox3ApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "auth"
            except Healthbox3ApiClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "connection"
            except Healthbox3ApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Optional(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> FlowResult:
        """Start reauthentication after the device rejected the API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a new API key and validate it."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            if error := await _async_check_api_key(
                self.hass, entry.data[CONF_HOST], user_input[CONF_API_KEY]
            ):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )

    async def _test_credentials(self, ipaddress: str, apikey: str) -> None:
        """Validate credentials."""
        client = Healthbox3(
            host=ipaddress,
            api_key=apikey,
            session=async_create_clientsession(self.hass),
        )
        await client.async_enable_advanced_api_features()

    async def _test_connectivity(self, ipaddress: str) -> None:
        """Validate connectivity."""
        client = Healthbox3(
            host=ipaddress,
            api_key=None,
            session=async_create_clientsession(self.hass),
        )
        await client.async_validate_connectivity()


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options Flow for the Config Entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        errors: dict[str, str] = {}
        if user_input is not None:
            api_key: str = user_input[CONF_API_KEY]
            # Validate first; only a working key may be stored.
            if error := await _async_check_api_key(
                self.hass, self.entry.data.get(CONF_HOST, ""), api_key
            ):
                errors["base"] = error
            else:
                # The update listener reloads the entry with the new key.
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, CONF_API_KEY: api_key}
                )
                return self.async_create_entry(
                    title="", data=dict(self.entry.options)
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=(user_input or {}).get(
                            CONF_API_KEY, self.entry.data.get(CONF_API_KEY, "")
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
        )
