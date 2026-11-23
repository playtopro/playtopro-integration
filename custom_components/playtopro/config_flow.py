"""Config flow for the playtopro integration."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.util.network import is_ip_address

from .const import (
    CONF_FIRMWARE,
    CONF_PRIVATE_KEY,
    CONF_SERIAL_NUMBER,
    DEFAULT_PORT,
    DOMAIN,
)
from .P2PFlowBase import async_validate_connection, async_validate_new_device

_LOGGER = logging.getLogger(__name__)

PORT_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))
SERIAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=1, max=0xFFFFFFFF))

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): PORT_VALIDATOR,
        vol.Required(CONF_SERIAL_NUMBER): SERIAL_VALIDATOR,
    }
)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): PORT_VALIDATOR,
    }
)


def _entry_title(serial_number: int) -> str:
    return f"Lichen {serial_number}"


class P2PConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lichen PlayToPro."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> P2POptionsFlowHandler:
        """Get the options flow for this handler."""
        return P2POptionsFlowHandler()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery of a Lichen PlayToPro device."""
        _LOGGER.debug("Zeroconf discovery received: %s", discovery_info)

        if discovery_info.ip_address.version != 4:
            return self.async_abort(reason="not_ipv4_address")

        try:
            serial_number = int(discovery_info.properties["serial"])
        except (KeyError, TypeError, ValueError):
            return self.async_abort(reason="invalid_discovery_info")

        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        updates: dict[str, Any] = {CONF_HOST: host, CONF_PORT: port}
        with suppress(KeyError, TypeError, ValueError):
            updates[CONF_FIRMWARE] = int(discovery_info.properties["firmware"])

        # Known device: keep its address up to date (reloads only if changed).
        await self.async_set_unique_id(str(serial_number))
        self._abort_if_unique_id_configured(updates=updates)

        # New device: ask the user to confirm.
        self._discovered = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SERIAL_NUMBER: serial_number,
        }
        self.context["title_placeholders"] = {"name": _entry_title(serial_number)}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        return await self._async_step_add_device("confirm", user_input, self._discovered)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a device manually."""
        return await self._async_step_add_device("user", user_input, {})

    async def _async_step_add_device(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        defaults: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Validate the device details and fetch its private key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            serial_number = user_input[CONF_SERIAL_NUMBER]

            if not is_ip_address(host):
                errors["base"] = "invalid_ip_address"
            else:
                await self.async_set_unique_id(str(serial_number))
                self._abort_if_unique_id_configured()

                data = await async_validate_new_device(errors, host, port, serial_number)
                if data is not None:
                    return self.async_create_entry(
                        title=_entry_title(serial_number), data=data
                    )
            defaults = user_input

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(DEVICE_SCHEMA, defaults),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the device rejected the saved key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fetch a new private key from the device in setup mode."""
        entry = self._get_reauth_entry()
        serial_number = int(entry.data[CONF_SERIAL_NUMBER])
        errors: dict[str, str] = {}

        if user_input is not None:
            data = await async_validate_new_device(
                errors, entry.data[CONF_HOST], int(entry.data[CONF_PORT]), serial_number
            )
            if data is not None:
                return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            description_placeholders={"name": _entry_title(serial_number)},
        )


class P2POptionsFlowHandler(OptionsFlow):
    """Change the host and port of an added device."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options step for a Lichen PlayToPro device."""
        entry = self.config_entry
        errors: dict[str, str] = {}
        defaults: Mapping[str, Any] = entry.data

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            if not is_ip_address(host):
                errors["base"] = "invalid_ip_address"
            else:
                updates = await async_validate_connection(
                    errors,
                    host,
                    port,
                    int(entry.data[CONF_SERIAL_NUMBER]),
                    int(entry.data[CONF_PRIVATE_KEY]),
                )
                if updates is not None:
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, **updates}
                    )
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)
                    return self.async_create_entry(data={})
            defaults = user_input

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(CONNECTION_SCHEMA, defaults),
            errors=errors,
        )
