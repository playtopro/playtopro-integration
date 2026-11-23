"""Tests for the protocol client."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from custom_components.playtopro.P2PDevice import (
    P2PConnectionError,
    P2PDevice,
    P2PFirmwareNotSupportedError,
    P2PInvalidResponseError,
    P2PRejectedError,
    P2PRequest,
)

from .conftest import HOST, KEY, PORT, SERIAL, FakeLichen


def test_request_encoding() -> None:
    """Requests are '$', key, packet, counter, length, payload, '!'."""
    assert P2PRequest(KEY, 7, bytes([1, 3])).to_bytes() == (
        b"$" + KEY.to_bytes(4, "little") + bytes([7, 0, 2, 1, 3]) + b"!"
    )


async def test_firmware_full_width_fields(lichen: FakeLichen) -> None:
    """Serial (4 bytes), firmware (2) and key (4) are read in full."""
    lichen.setup_mode = True
    lichen.firmware = 300
    firmware = await P2PDevice(HOST, PORT, SERIAL).async_get_firmware()
    assert firmware.serial_number == SERIAL
    assert firmware.firmware == 300
    assert firmware.mode == 1
    assert firmware.private_key == KEY


async def test_firmware_without_setup_mode_has_no_key(lichen: FakeLichen) -> None:
    """Outside setup mode the device doesn't hand out its key."""
    firmware = await P2PDevice(HOST, PORT, SERIAL).async_get_firmware()
    assert firmware.mode == 0
    assert firmware.private_key == 0


async def test_old_firmware_short_reply(lichen: FakeLichen) -> None:
    """A reply without firmware details means firmware older than 27."""
    lichen.handle = lambda request: lichen._packet(0, b"")  # type: ignore[method-assign]
    with pytest.raises(P2PFirmwareNotSupportedError):
        await P2PDevice(HOST, PORT, SERIAL).async_get_firmware()


async def test_status(lichen: FakeLichen) -> None:
    """Status bytes are decoded at the firmware's offsets."""
    lichen.eco = 0b10000000
    lichen.sleep = 0b01000000
    status = await P2PDevice(HOST, PORT, KEY).async_get_status()
    assert status.system_auto is True
    assert status.eco_mode_factor == 60
    assert [z.on for z in status.zones[:3]] == [True, False, True]
    assert status.zones[0].manual_mode_active is True
    assert status.zones[7].eco_mode is True
    assert status.zones[6].sleep_mode is True
    assert status.zones[5].sleep_mode is False


async def test_commands(lichen: FakeLichen) -> None:
    """Commands send the payload in the order the firmware expects."""
    device = P2PDevice(HOST, PORT, KEY)
    assert await device.async_set_zone_manual_mode(3, True)
    assert await device.async_set_zone_auto_mode(2, False)
    assert await device.async_set_zone_eco_mode(4, True)
    assert await device.async_set_zone_sleep_mode(5, True)
    assert await device.async_set_auto_mode(False)
    assert await device.async_set_eco_mode(True)
    assert lichen.manual == 0b00001001
    assert lichen.auto == 0b11111011
    assert lichen.eco == 0b00010000
    assert lichen.sleep == 0b00100000
    assert lichen.system_auto is False
    assert lichen.eco_mode is True


async def test_wrong_key_rejected(lichen: FakeLichen) -> None:
    """The device closes the connection when the key is wrong."""
    with pytest.raises(P2PRejectedError):
        await P2PDevice(HOST, PORT, KEY & 0xFFFFFF).async_set_auto_mode(True)


async def test_unreachable(lichen: FakeLichen) -> None:
    """Connection failures become P2PConnectionError."""
    lichen.reachable = False
    with pytest.raises(P2PConnectionError):
        await P2PDevice(HOST, PORT, KEY).async_get_status()


async def test_packet_mismatch(lichen: FakeLichen) -> None:
    """A reply for a different packet is rejected."""
    lichen.handle = lambda request: lichen._packet(5, b"\x01")  # type: ignore[method-assign]
    with pytest.raises(P2PInvalidResponseError):
        await P2PDevice(HOST, PORT, KEY).async_get_status()


async def test_short_status(lichen: FakeLichen) -> None:
    """A truncated status packet is rejected instead of raising IndexError."""
    lichen.handle = lambda request: lichen._packet(1, bytes(10))  # type: ignore[method-assign]
    with pytest.raises(P2PInvalidResponseError):
        await P2PDevice(HOST, PORT, KEY).async_get_status()


async def test_real_socket_and_timeout(socket_enabled) -> None:
    """Over real TCP: one request per write, and a silent device times out."""
    device = FakeLichen()
    silent = False

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        header = await reader.readexactly(8)
        body = await reader.readexactly(header[7] + 1)
        if not silent:
            writer.write(device.handle(header + body))
            await writer.drain()
        else:
            await asyncio.sleep(1)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        status = await P2PDevice("127.0.0.1", port, KEY).async_get_status()
        assert status.eco_mode_factor == 60

        silent = True
        with (
            patch("custom_components.playtopro.P2PDevice.REQUEST_TIMEOUT", 0.1),
            pytest.raises(P2PConnectionError),
        ):
            await P2PDevice("127.0.0.1", port, KEY).async_get_status()
