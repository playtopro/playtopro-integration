from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.util.network import is_ip_address

from homeassistant.config_entries import ConfigEntry
from .const import CONF_FIRMWARE, CONF_PRIVATE_KEY, CONF_SERIAL_NUMBER
from .P2PDevice import P2PDevice, P2PError, P2PFirmwareResponse


class P2PFlowBase:
    """Common helpers shared by config and options flows."""

    async def _async_validate_input(
        self,
        errors: dict[str, str],
        host: str,
        port: int,
        serial_number: int,
        entries: list[ConfigEntry],
    ) -> bool:
        if is_ip_address(host):
            match: bool = False

            for entry in entries:
                registered_serial_number: int = int(entry.data.get(CONF_SERIAL_NUMBER))

                if registered_serial_number == serial_number:
                    match = True
                    break
            if not match:
                return True
            else:
                errors["base"] = "device_with_serial_number_already_added"
        else:
            errors["base"] = "invalid_ip_address"
        return False

    # -----------------------------------------------------------------------
    # DEVICE VALIDATION (shared by manual + Zeroconf)
    # -----------------------------------------------------------------------
    async def _async_validate_device(
        self,
        errors: dict[str, str],
        host: str,
        port: int,
        serial_number: int,
    ) -> dict[str, Any] | None:
        # The only request that is valid when the serial is passed as the private key
        # is get_firmware. If the device is also in setup mode, the private key will
        # be appended to the end of the packet and will be saved into the configuration.
        hub = P2PDevice(ipv4=host, port=port, private_key=serial_number)

        try:
            firmwareResponse: P2PFirmwareResponse = await hub.async_get_firmware()

            if firmwareResponse.serial_number != serial_number:
                errors["base"] = "serial_number_mismatch"

            elif firmwareResponse.firmware < 28:
                errors["base"] = "firmware_not_supported"

            elif firmwareResponse.mode == 0:
                errors["base"] = "device_must_be_in_setup_mode_to_get_private_key"

            elif firmwareResponse.private_key == 0:
                errors["base"] = "failed_to_get_private_key"

            else:
                try:
                    # Validate private key / connectivity
                    hub = P2PDevice(
                        ipv4=host, port=port, private_key=firmwareResponse.private_key
                    )
                    await hub.async_get_status()

                    return {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SERIAL_NUMBER: serial_number,
                        CONF_PRIVATE_KEY: firmwareResponse.private_key,
                        CONF_FIRMWARE: firmwareResponse.firmware,
                    }
                except P2PError as err:
                    errors["base"] = err.error

        except ConnectionError:
            errors["base"] = "cannot_connect"
        except P2PError as err:
            errors["base"] = err.error

        return None
