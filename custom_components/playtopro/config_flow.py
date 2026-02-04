"""Config flow for the Lichen PlayToPro integration."""

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
from homeassistant.util.network import is_ip_address

from .const import CONF_FIRMWARE, CONF_SERIAL, CONF_PRIVATE_KEY, DOMAIN
from .P2PDevice import P2PDevice, P2PError, P2PFirmwareResponse

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 1233

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SERIAL): int,
    }
)


# ---------------------------------------------------------------------------
# CONFIG FLOW
# ---------------------------------------------------------------------------


class P2PConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lichen PlayToPro."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return P2POptionsFlowHandler(config_entry)

    # -----------------------------------------------------------------------
    # MANUAL SETUP
    # -----------------------------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            serial = user_input[CONF_SERIAL]

            if not is_ip_address(host):
                errors["base"] = "invalid_ip_address"
            else:
                # Use serial as the unique ID
                await self.async_set_unique_id(str(serial))
                self._abort_if_unique_id_configured()

                result = await self._async_validate_device(host, port, serial)
                if isinstance(result, dict):
                    return self.async_create_entry(
                        title=f"Lichen {serial}",
                        data=result,
                    )
                errors["base"] = result

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=host): str,
                        vol.Required(CONF_PORT, default=port): int,
                        vol.Required(CONF_SERIAL, default=serial): int,
                    }
                ),
                errors=errors,
            )

        return self.async_show_form(step_id="user", data_schema=OPTIONS_SCHEMA)

    # -----------------------------------------------------------------------
    # ZEROCONF DISCOVERY
    # -----------------------------------------------------------------------
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        _LOGGER.debug("Zeroconf discovery received: %s", discovery_info)

        host = discovery_info.host
        port = discovery_info.port
        properties = discovery_info.properties or {}

        # Normalize TXT values
        try:
            serial = int(properties.get("serial"))
        except (TypeError, ValueError):
            return self.async_abort(reason="invalid_serial")

        try:
            firmware = int(properties.get("firmware"))
        except (TypeError, ValueError):
            firmware = None

        # Unique ID = serial
        await self.async_set_unique_id(str(serial))

        # ---------------------------------------------------------
        # If device already exists, update IP and reload integration
        # ---------------------------------------------------------
        for entry in self._async_current_entries():
            old_host = entry.data.get(CONF_HOST)

            if old_host != host:
                _LOGGER.warning(
                    "PlayToPro device %s IP changed: %s → %s", serial, old_host, host
                )

                new_data = {**entry.data, CONF_HOST: host}
                self.hass.config_entries.async_update_entry(entry, data=new_data)

                await self.hass.config_entries.async_reload(entry.entry_id)

            # Always abort for existing devices
            return self.async_abort(reason="already_configured")

        # ---------------------------------------------------------
        # New device → continue to confirmation
        # ---------------------------------------------------------
        self._discovered_info = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SERIAL: serial,
            CONF_FIRMWARE: firmware,
        }

        return await self.async_step_confirm()

    # -----------------------------------------------------------------------
    # CONFIRMATION STEP (shared by Zeroconf)
    # -----------------------------------------------------------------------
    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            host = self._discovered_info[CONF_HOST]
            port = self._discovered_info[CONF_PORT]
            serial = self._discovered_info[CONF_SERIAL]

            result = await self._async_validate_device(host, port, serial)
            if isinstance(result, dict):
                return self.async_create_entry(
                    title=f"Lichen {serial}",
                    data=result,
                )
            return self.async_abort(reason=result)

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "host": self._discovered_info[CONF_HOST],
                "serial": self._discovered_info[CONF_SERIAL],
            },
        )

    # -----------------------------------------------------------------------
    # DEVICE VALIDATION (shared by manual + Zeroconf)
    # -----------------------------------------------------------------------
    async def _async_validate_device(
        self, host: str, port: int, serial: int
    ) -> dict[str, Any] | str:
        # The only request that is valid when the serial is passed as the private key
        # is get_firmware. If the device is also in setup mode, the private key will
        # be appended to the end of the packet and will be saved into the configuration.
        hub = P2PDevice(ipv4=host, port=port, private_key=serial)

        try:
            firmwareResponse: P2PFirmwareResponse = await hub.async_get_firmware()

            if firmwareResponse.firmware < 26:
                return "firmware_not_supported"

            if firmwareResponse.mode == 0:
                return "device_must_be_in_setup_mode_to_get_private_key"

            # Validate private key / connectivity
            await hub.async_get_status()

            return {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_SERIAL: serial,
                CONF_PRIVATE_KEY: firmwareResponse.private_key,
                CONF_FIRMWARE: firmwareResponse.firmware,
            }

        except ConnectionError:
            return "cannot_connect"
        except P2PError as err:
            return err.error


# ---------------------------------------------------------------------------
# OPTIONS FLOW
# ---------------------------------------------------------------------------


class P2POptionsFlowHandler(OptionsFlow):
    """Handle PlayToPro options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Update entry data
            new_data = {
                CONF_HOST: self.entry.data[CONF_HOST],
                **user_input,
            }

            self.hass.config_entries.async_update_entry(
                entry=self.entry,
                data=new_data,
            )

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default=self.entry.data[CONF_PORT]): int,
                    vol.Required(
                        CONF_SERIAL, default=self.entry.data[CONF_SERIAL]
                    ): int,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
