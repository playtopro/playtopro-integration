"""Config flow for the playtopro integration."""

from __future__ import annotations

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
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_FIRMWARE, CONF_SERIAL_NUMBER, CONF_PRIVATE_KEY, DOMAIN
from .P2PFlowBase import P2PFlowBase

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 1233

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SERIAL_NUMBER): int,
    }
)


# ---------------------------------------------------------------------------
# CONFIG FLOW
# ---------------------------------------------------------------------------


class P2PConfigFlow(ConfigFlow, P2PFlowBase, domain=DOMAIN):
    """Handle a config flow for Lichen PlayToPro."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return P2POptionsFlowHandler(config_entry)

    # -----------------------------------------------------------------------
    # ZEROCONF DISCOVERY
    # -----------------------------------------------------------------------
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        _LOGGER.debug("Zeroconf discovery received: %s", discovery_info)

        host: str = discovery_info.host
        port: int = int(discovery_info.port)
        serial_number: int = int(discovery_info.properties.get("serial"))
        firmware: int = int(discovery_info.properties.get("firmware"))

        # ---------------------------------------------------------
        # If device already exists, update IP and reload integration
        # ---------------------------------------------------------
        for entry in self._async_current_entries():
            registered_serial_number: int = int(entry.data.get(CONF_SERIAL_NUMBER))

            if registered_serial_number == serial_number:
                registered_host: str = entry.data.get(CONF_HOST)

                if registered_host != host:
                    _LOGGER.warning(
                        "Playtopro device %d IP changed: %s → %s",
                        serial_number,
                        registered_host,
                        host,
                    )

                    new_data = {**entry.data, CONF_HOST: host, CONF_FIRMWARE: firmware}
                    self.hass.config_entries.async_update_entry(entry, data=new_data)

                    await self.hass.config_entries.async_reload(entry.entry_id)

                    # Always abort for existing devices
                    return self.async_abort(
                        reason="device_already_added_details_updated"
                    )

                # Always abort for existing devices
                return self.async_abort(reason="device_already_added")

        # ---------------------------------------------------------
        # New device → continue to confirmation
        # ---------------------------------------------------------
        self._discovered_info = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SERIAL_NUMBER: serial_number,
            CONF_FIRMWARE: firmware,
        }

        return await self.async_step_confirm()

    # -----------------------------------------------------------------------
    # CONFIRMATION STEP (shared by Zeroconf)
    # -----------------------------------------------------------------------
    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = int(user_input[CONF_PORT])
            serial_number: int = int(user_input[CONF_SERIAL_NUMBER])

            if await self._async_validate_input(
                errors, host, port, serial_number, self._async_current_entries()
            ):
                data: dict[str, Any] | None = await self._async_validate_device(
                    errors, host, port, serial_number
                )

                if data is not None:
                    return self.async_create_entry(
                        title=f"Lichen play {serial_number}",
                        data=data,
                    )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self._discovered_info[CONF_HOST]
                    ): str,
                    vol.Required(
                        CONF_PORT, default=int(self._discovered_info[CONF_PORT])
                    ): int,
                    vol.Required(
                        CONF_SERIAL_NUMBER,
                        default=int(self._discovered_info[CONF_SERIAL_NUMBER]),
                    ): int,
                }
            ),
            errors=errors,
        )

    # -----------------------------------------------------------------------
    # MANUAL SETUP
    # -----------------------------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = int(user_input[CONF_PORT])
            serial_number: int = int(user_input[CONF_SERIAL_NUMBER])

            if await self._async_validate_input(
                errors, host, port, serial_number, self._async_current_entries()
            ):
                data: dict[str, Any] | None = await self._async_validate_device(
                    errors, host, int(port), int(serial_number)
                )

                if data is not None:
                    return self.async_create_entry(
                        title=f"Lichen {serial_number}",
                        data=data,
                    )

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=host): str,
                        vol.Required(CONF_PORT, default=port): int,
                        vol.Required(CONF_SERIAL_NUMBER, default=serial_number): int,
                    }
                ),
                errors=errors,
            )

        return self.async_show_form(step_id="user", data_schema=OPTIONS_SCHEMA)


# ---------------------------------------------------------------------------
# OPTIONS FLOW
# ---------------------------------------------------------------------------


class P2POptionsFlowHandler(OptionsFlow, P2PFlowBase):
    """Handle PlayToPro options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = int(user_input[CONF_PORT])
            serial_number: int = int(self.entry.data[CONF_SERIAL_NUMBER])

            data: dict[str, Any] | None = await self._async_validate_device(
                errors, host, port, serial_number
            )

            if data is not None:
                # Update
                self.hass.config_entries.async_update_entry(
                    entry=self.entry,
                    data=data,
                )

                # Reload
                await self.hass.config_entries.async_reload(self.entry.entry_id)

                # Return
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.entry.data[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=self.entry.data[CONF_PORT]): int,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
