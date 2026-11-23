"""Tests for the config, reauth and options flows."""

from __future__ import annotations

from ipaddress import ip_address

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.playtopro.const import (
    CONF_FIRMWARE,
    CONF_PRIVATE_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import HOST, KEY, PORT, SERIAL, FakeLichen

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

USER_INPUT = {CONF_HOST: HOST, CONF_PORT: PORT, CONF_SERIAL_NUMBER: SERIAL}


def _zeroconf(serial: int | str = SERIAL, host: str = HOST, firmware: str = "28"):
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="lichen.local.",
        name="lichen._playtopro._tcp.local.",
        port=PORT,
        type="_playtopro._tcp.local.",
        properties={"serial": str(serial), "firmware": firmware},
    )


async def test_user_flow(hass: HomeAssistant, lichen: FakeLichen) -> None:
    """Manual setup stores the full 4-byte key."""
    lichen.setup_mode = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Lichen {SERIAL}"
    assert result["result"].unique_id == str(SERIAL)
    assert result["data"] == {
        CONF_HOST: HOST,
        CONF_PORT: PORT,
        CONF_SERIAL_NUMBER: SERIAL,
        CONF_PRIVATE_KEY: KEY,
        CONF_FIRMWARE: 28,
    }


@pytest.mark.parametrize(
    ("setup", "user_input", "error"),
    [
        (lambda d: None, USER_INPUT, "device_must_be_in_setup_mode_to_get_private_key"),
        (lambda d: setattr(d, "reachable", False), USER_INPUT, "cannot_connect"),
        (lambda d: setattr(d, "firmware", 27), USER_INPUT, "firmware_not_supported"),
        (lambda d: None, {**USER_INPUT, CONF_SERIAL_NUMBER: 123}, "serial_number_mismatch"),
        (lambda d: None, {**USER_INPUT, CONF_HOST: "lichen"}, "invalid_ip_address"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, lichen: FakeLichen, setup, user_input, error
) -> None:
    """Errors are translation keys, and the user can retry."""
    setup(lichen)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    lichen.reachable = True
    lichen.firmware = 28
    lichen.setup_mode = True
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Adding the same serial twice aborts."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_new_device(hass: HomeAssistant, lichen: FakeLichen) -> None:
    """A discovered device is confirmed and added."""
    lichen.setup_mode = True
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PRIVATE_KEY] == KEY


async def test_zeroconf_second_device(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """With one device added, a different one is still offered."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf(serial=555, host="192.168.1.60")
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert config_entry.data[CONF_HOST] == HOST


async def test_zeroconf_updates_known_device(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Rediscovery updates only the matching entry's address and firmware."""
    config_entry.add_to_hass(hass)
    other = MockConfigEntry(
        domain=DOMAIN,
        unique_id="555",
        data={**config_entry.data, CONF_SERIAL_NUMBER: 555, CONF_HOST: "192.168.1.60"},
    )
    other.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_zeroconf(host="192.168.1.99", firmware="29")
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    await hass.async_block_till_done()
    assert config_entry.data[CONF_HOST] == "192.168.1.99"
    assert config_entry.data[CONF_FIRMWARE] == 29
    assert other.data[CONF_HOST] == "192.168.1.60"


@pytest.mark.parametrize(
    ("info", "reason"),
    [
        (_zeroconf(serial="abc"), "invalid_discovery_info"),
        (
            ZeroconfServiceInfo(
                ip_address=ip_address("fe80::1"),
                ip_addresses=[ip_address("fe80::1")],
                hostname="lichen.local.",
                name="lichen._playtopro._tcp.local.",
                port=PORT,
                type="_playtopro._tcp.local.",
                properties={"serial": str(SERIAL)},
            ),
            "not_ipv4_address",
        ),
    ],
)
async def test_zeroconf_aborts(hass: HomeAssistant, info, reason) -> None:
    """Unusable discoveries abort."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_reauth(hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry) -> None:
    """Reauth fetches the key again from a device in setup mode."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, CONF_PRIVATE_KEY: KEY & 0xFFFFFF}
    )
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "device_must_be_in_setup_mode_to_get_private_key"}

    lichen.setup_mode = True
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert config_entry.data[CONF_PRIVATE_KEY] == KEY


async def test_options_change_host_without_setup_mode(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """The address can be changed with the device in normal mode."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.77", CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert config_entry.data[CONF_HOST] == "192.168.1.77"
    assert config_entry.data[CONF_PRIVATE_KEY] == KEY


async def test_options_wrong_device(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Pointing at a different device is refused."""
    config_entry.add_to_hass(hass)
    lichen.serial = 123
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.77", CONF_PORT: PORT}
    )
    assert result["errors"] == {"base": "serial_number_mismatch"}
    assert config_entry.data[CONF_HOST] == HOST
