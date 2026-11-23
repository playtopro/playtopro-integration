"""Device checks shared by the config, reauth and options flows."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_FIRMWARE, CONF_PRIVATE_KEY, CONF_SERIAL_NUMBER, MIN_FIRMWARE
from .P2PDevice import P2PDevice, P2PError, P2PFirmwareResponse


async def _async_get_firmware(
    errors: dict[str, str], host: str, port: int, serial_number: int
) -> P2PFirmwareResponse | None:
    """Ask the device who it is, and check it is the expected, supported device.

    The device answers this packet to anyone, using the serial number as the key.
    """
    try:
        firmware = await P2PDevice(host, port, serial_number).async_get_firmware()
    except P2PError as err:
        errors["base"] = err.error
        return None

    if firmware.serial_number != serial_number:
        errors["base"] = "serial_number_mismatch"
    elif firmware.firmware < MIN_FIRMWARE:
        errors["base"] = "firmware_not_supported"
    else:
        return firmware
    return None


async def _async_check_key(
    errors: dict[str, str], host: str, port: int, private_key: int
) -> bool:
    """Check that the device accepts a status request with this key."""
    try:
        await P2PDevice(host, port, private_key).async_get_status()
    except P2PError as err:
        errors["base"] = err.error
        return False
    return True


async def async_validate_new_device(
    errors: dict[str, str], host: str, port: int, serial_number: int
) -> dict[str, Any] | None:
    """Fetch the private key from a device in setup mode.

    Used when adding a device and when re-authenticating. Returns the config
    entry data, or None with `errors` filled in.
    """
    firmware = await _async_get_firmware(errors, host, port, serial_number)
    if firmware is None:
        return None
    if firmware.mode == 0:
        errors["base"] = "device_must_be_in_setup_mode_to_get_private_key"
        return None
    if firmware.private_key == 0:
        errors["base"] = "failed_to_get_private_key"
        return None
    if not await _async_check_key(errors, host, port, firmware.private_key):
        return None
    return {
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_SERIAL_NUMBER: serial_number,
        CONF_PRIVATE_KEY: firmware.private_key,
        CONF_FIRMWARE: firmware.firmware,
    }


async def async_validate_connection(
    errors: dict[str, str],
    host: str,
    port: int,
    serial_number: int,
    private_key: int,
) -> dict[str, Any] | None:
    """Check a new host/port for an already-added device.

    Setup mode isn't needed: the saved key is checked instead. If the device
    happens to be in setup mode, its key is refreshed. Returns the data to
    update, or None with `errors` filled in.
    """
    firmware = await _async_get_firmware(errors, host, port, serial_number)
    if firmware is None:
        return None
    if firmware.mode != 0 and firmware.private_key != 0:
        private_key = firmware.private_key
    if not await _async_check_key(errors, host, port, private_key):
        return None
    return {
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_PRIVATE_KEY: private_key,
        CONF_FIRMWARE: firmware.firmware,
    }
