"""Tests for the P2PDevice protocol client, using a fake device on localhost."""

import asyncio
from collections.abc import AsyncGenerator, Callable

import pytest

from homeassistant.components.playtopro import P2PDevice as p2p
from homeassistant.components.playtopro.P2PDevice import (
    P2PDevice,
    P2PError,
    P2PRequest,
    P2PRequestError,
)

# HA's test suite blocks real sockets; these tests talk to a fake device on
# localhost, so opt back in.
pytestmark = pytest.mark.usefixtures("socket_enabled")

SERIAL = 0x12345678
KEY = 0x9ABCDEF0

# Packet ids that tell the fake device how to misbehave.
PACKET_NO_REPLY = 50
PACKET_HANG = 51
PACKET_WRONG_PACKET = 52


def _packet(packet: int, payload: bytes, header: bytes = b"$") -> bytes:
    """Build a response the way the device does: header, serial, ids, payload."""
    return (
        header
        + SERIAL.to_bytes(4, "little")
        + bytes([packet, 0, len(payload)])
        + payload
    )


def _status_payload() -> bytes:
    """Status payload: running, auto on, zones 1 and 3 on, dated 2026-11-23."""
    body = bytearray(27)
    body[0] = 1  # system_run
    body[1] = 1  # system_auto
    body[2] = 0b101  # zones on
    body[4] = 0xFF  # auto mode zones
    body[5] = 1  # eco mode
    body[7] = 80  # eco mode factor
    body[9:11] = (2026).to_bytes(2, "little")
    body[11], body[12], body[13] = 11, 23, 1  # month, day, day of week
    body[14], body[15], body[16] = 11, 38, 25  # hh:mm:ss
    body[26] = 0b10  # sleep mode zones
    return bytes(body)


async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    request = await reader.read(64)
    packet = request[5]
    if packet == 0:
        writer.write(
            _packet(0, (300).to_bytes(2, "little") + b"\x01" + KEY.to_bytes(4, "little"))
        )
    elif packet == 1:
        writer.write(_packet(1, _status_payload()))
    elif packet == 8:
        writer.write(_packet(8, b"\x01"))
    elif packet == PACKET_HANG:
        await asyncio.sleep(30)
    elif packet == PACKET_WRONG_PACKET:
        writer.write(_packet(99, b"\x01"))
    # PACKET_NO_REPLY and anything else: close without answering.
    await writer.drain()
    writer.close()


@pytest.fixture
async def device() -> AsyncGenerator[Callable[[int], P2PDevice]]:
    """Start a fake device and return a factory for clients pointed at it."""
    server = await asyncio.start_server(_handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield lambda key=SERIAL: P2PDevice("127.0.0.1", port, key)
    server.close()
    await server.wait_closed()


async def test_firmware_parses_multibyte_fields(device) -> None:
    """Serial and private key are 4 bytes, firmware is 2 bytes."""
    firmware = await device().async_get_firmware()
    assert firmware.serial_number == SERIAL
    assert firmware.firmware == 300
    assert firmware.mode == 1
    assert firmware.private_key == KEY


async def test_status_parses_fields_and_zones(device) -> None:
    """Status fields, the 2-byte year and per-zone bits are decoded."""
    status = await device(KEY).async_get_status()
    assert status.system_run is True
    assert status.system_auto is True
    assert status.eco_mode is True
    assert status.eco_mode_factor == 80
    assert (status.year, status.month, status.day) == (2026, 11, 23)
    assert status.day_of_week == 1
    assert (status.hour, status.minute, status.second) == (11, 38, 25)
    assert [zone.on for zone in status.zones] == [
        True, False, True, False, False, False, False, False
    ]
    assert all(zone.auto_mode for zone in status.zones)
    assert [zone.sleep_mode for zone in status.zones][:3] == [False, True, False]


async def test_command_confirmation(device) -> None:
    """A command returns the device's confirmation."""
    response = await device(KEY).async_set_eco_mode(True)
    assert response.result is True


async def test_concurrent_requests_are_serialised(device) -> None:
    """Several requests at once on one client all succeed."""
    client = device(KEY)
    results = await asyncio.gather(*(client.async_get_status() for _ in range(5)))
    assert len(results) == 5


async def test_no_reply_raises_request_error(device) -> None:
    """A device that closes without answering points at the private key."""
    with pytest.raises(P2PRequestError, match="check private key") as err:
        await device().async_get_response(
            P2PRequest(SERIAL, PACKET_NO_REPLY, 0, bytearray())
        )
    assert str(err.value) == err.value.error


async def test_hanging_device_times_out(
    device, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A device that never answers fails after the timeout instead of hanging."""
    monkeypatch.setattr(p2p, "REQUEST_TIMEOUT", 0.2)
    with pytest.raises(P2PRequestError, match="Timed out"):
        await device().async_get_response(
            P2PRequest(SERIAL, PACKET_HANG, 0, bytearray())
        )


async def test_packet_mismatch(device) -> None:
    """A reply for a different packet id is rejected."""
    with pytest.raises(P2PRequestError, match="Packet mismatch"):
        await device().async_get_response(
            P2PRequest(SERIAL, PACKET_WRONG_PACKET, 0, bytearray())
        )


async def test_short_status_rejected() -> None:
    """A status reply too short to parse raises instead of reading garbage."""
    response = p2p.P2PResponse(bytearray(_packet(1, b"\x00" * 5)))
    with pytest.raises(P2PError, match="too short"):
        p2p.P2PStatusResponse(response)


async def test_connection_refused() -> None:
    """Nothing listening gives a request error, wrapped for status requests."""
    server = await asyncio.start_server(_handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    with pytest.raises(P2PRequestError, match="Unable to get status"):
        await P2PDevice("127.0.0.1", port, KEY).async_get_status()
