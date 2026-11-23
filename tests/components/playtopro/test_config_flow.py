"""Tests for the playtopro config flow, including zeroconf discovery."""

from ipaddress import ip_address
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components.playtopro.const import (
    CONF_FIRMWARE,
    CONF_PRIVATE_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from homeassistant.components.playtopro.P2PDevice import P2PError, P2PRequestError
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import FIRMWARE, HOST, PORT, PRIVATE_KEY, SERIAL

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

USER_INPUT = {CONF_HOST: HOST, CONF_PORT: PORT, CONF_SERIAL_NUMBER: SERIAL}

EXPECTED_DATA = {
    CONF_HOST: HOST,
    CONF_PORT: PORT,
    CONF_SERIAL_NUMBER: SERIAL,
    CONF_PRIVATE_KEY: PRIVATE_KEY,
    CONF_FIRMWARE: FIRMWARE,
}


def _zeroconf_info(
    host: str = HOST, port: int = PORT, firmware: int = FIRMWARE
) -> ZeroconfServiceInfo:
    """Build the discovery info a device announces over mDNS."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        port=port,
        hostname="lichen.local.",
        type="_playtopro._tcp.local.",
        name="lichen._playtopro._tcp.local.",
        properties={"serial": str(SERIAL), "firmware": str(firmware)},
    )


# ---------------------------------------------------------------------------
# Manual setup
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mock_device")
async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A valid device creates an entry with the private key it returns."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == EXPECTED_DATA
    assert result["result"].unique_id == str(SERIAL)


@pytest.mark.parametrize(
    ("firmware_response", "firmware_error", "status_error", "expected_error"),
    [
        (None, P2PRequestError("Connection failed"), None, "cannot_connect"),
        (None, P2PRequestError("Timed out"), None, "cannot_connect"),
        (None, P2PError("Unexpected response packet"), None, "unknown"),
        ({"serial_number": 1002}, None, None, "serial_number_mismatch"),
        ({"firmware": 27}, None, None, "firmware_not_supported"),
        (
            {"mode": 0},
            None,
            None,
            "device_must_be_in_setup_mode_to_get_private_key",
        ),
        ({"private_key": 0}, None, None, "failed_to_get_private_key"),
        (None, None, P2PRequestError("No response"), "cannot_connect"),
        (None, None, P2PError("Response too short"), "unknown"),
    ],
)
async def test_user_flow_device_errors(
    hass: HomeAssistant,
    mock_device: MagicMock,
    firmware_response: dict | None,
    firmware_error: Exception | None,
    status_error: Exception | None,
    expected_error: str,
) -> None:
    """Device problems show a translated error, and the flow can recover."""
    if firmware_response:
        for key, value in firmware_response.items():
            setattr(mock_device.async_get_firmware.return_value, key, value)
    if firmware_error:
        mock_device.async_get_firmware.side_effect = firmware_error
    if status_error:
        mock_device.async_get_status.side_effect = status_error

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    # Fix the device and retry on the same flow.
    mock_device.async_get_firmware.side_effect = None
    mock_device.async_get_status.side_effect = None
    mock_device.async_get_firmware.return_value = MagicMock(
        serial_number=SERIAL, firmware=FIRMWARE, mode=1, private_key=PRIVATE_KEY
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == EXPECTED_DATA


async def test_user_flow_invalid_ip(
    hass: HomeAssistant, mock_device: MagicMock
) -> None:
    """A host that is not an IP address is rejected before contacting a device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_HOST: "not-an-ip"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ip_address"}
    mock_device.async_get_firmware.assert_not_called()


async def test_user_flow_duplicate(
    hass: HomeAssistant, mock_device: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Adding a serial number that is already configured is rejected."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "device_with_serial_number_already_added"}
    mock_device.async_get_firmware.assert_not_called()


# ---------------------------------------------------------------------------
# Zeroconf discovery
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mock_device")
async def test_zeroconf_new_device(hass: HomeAssistant) -> None:
    """A newly discovered device asks for confirmation, prefilled, then is added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    defaults = {
        str(key): key.default() for key in result["data_schema"].schema
    }
    assert defaults == USER_INPUT

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == EXPECTED_DATA
    assert result["result"].unique_id == str(SERIAL)


async def test_zeroconf_new_device_not_in_setup_mode(
    hass: HomeAssistant, mock_device: MagicMock
) -> None:
    """Confirming a discovered device that is not in setup mode shows an error."""
    mock_device.async_get_firmware.return_value.mode = 0

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf_info()
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        "base": "device_must_be_in_setup_mode_to_get_private_key"
    }


async def test_zeroconf_known_device_unchanged(
    hass: HomeAssistant, mock_device: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Rediscovering a configured device with the same details just aborts."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data == EXPECTED_DATA
    mock_device.async_get_firmware.assert_not_called()


async def test_zeroconf_known_device_new_details(
    hass: HomeAssistant, mock_device: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """A configured device announcing a new IP, port or firmware updates its entry."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=_zeroconf_info(host="192.168.1.200", port=1240, firmware=30),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data == {
        **EXPECTED_DATA,
        CONF_HOST: "192.168.1.200",
        CONF_PORT: 1240,
        CONF_FIRMWARE: 30,
    }
    # The private key is kept, and the device is not contacted.
    assert mock_config_entry.data[CONF_PRIVATE_KEY] == PRIVATE_KEY
    mock_device.async_get_firmware.assert_not_called()


async def test_zeroconf_only_updates_matching_device(
    hass: HomeAssistant, mock_device: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Discovering a second device leaves the first entry alone and offers setup."""
    mock_config_entry.add_to_hass(hass)

    other = _zeroconf_info(host="192.168.1.50")
    other.properties["serial"] = "2002"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=other
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert mock_config_entry.data == EXPECTED_DATA


async def test_zeroconf_then_user_flow_in_progress(
    hass: HomeAssistant, mock_device: MagicMock, mock_setup_entry: AsyncMock
) -> None:
    """Finishing manual setup while a discovery is pending creates one entry."""
    discovery = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf_info()
    )
    assert discovery["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # The pending discovery flow is cleaned up once the device is configured.
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)
