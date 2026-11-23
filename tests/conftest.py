"""Fixtures for the playtopro tests: a fake Lichen Play that follows the firmware's rules."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest.mock import patch

from awesomeversion import AwesomeVersion
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.playtopro.const import (
    CONF_FIRMWARE,
    CONF_PRIVATE_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from homeassistant import loader
from homeassistant.const import CONF_HOST, CONF_PORT

# Both above 2^24, so a 3-byte parse of either would be caught.
SERIAL = 30000001
KEY = 0x9A3F21C7
HOST = "192.168.1.50"
PORT = 1233


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> Generator[None]:
    """Let Home Assistant load custom_components/playtopro.

    manifest.json has no version so the integration also works as a core
    integration in the dev container; the release workflow adds one. HA blocks
    custom integrations without a version, so give it one here.
    """
    with patch.object(
        loader.Integration,
        "version",
        property(lambda self: AwesomeVersion(self.manifest.get("version", "0.0.0"))),
    ):
        yield


class FakeLichen:
    """Answers requests like app_main.c's process_request()."""

    def __init__(self) -> None:
        self.serial = SERIAL
        self.key = KEY
        self.firmware = 28
        self.setup_mode = False
        self.reachable = True
        self.reject_count = 0  # reject this many otherwise-valid requests
        self.refuse_commands = False
        self.requests: list[bytes] = []

        self.system_auto = True
        self.eco_mode = False
        self.eco_mode_factor = 60
        self.outputs = 0b00000101
        self.manual = 0b00000001
        self.auto = 0b11111111
        self.eco = 0
        self.eco_active = 0
        self.sleep = 0

    def _packet(self, message: int, payload: bytes) -> bytes:
        return (
            b"$"
            + self.serial.to_bytes(4, "little")
            + bytes([message, 0, len(payload)])
            + payload
            + b"!"
        )

    def handle(self, request: bytes) -> bytes:
        """Return the reply, or b"" to close without replying."""
        self.requests.append(request)
        if len(request) < 9 or request[0] != ord("$") or request[-1] != ord("!"):
            return b""
        key = int.from_bytes(request[1:5], "little")
        message = request[5]
        payload = request[8:-1]

        accepted = (
            message == 0
            or (message == 1 and key == self.serial)
            or key == self.key
            or self.setup_mode
        )
        if not accepted:
            return b""
        if self.reject_count:
            self.reject_count -= 1
            return b""

        if message == 0:
            key_bytes = self.key.to_bytes(4, "little") if self.setup_mode else bytes(4)
            return self._packet(
                0,
                self.firmware.to_bytes(2, "little")
                + bytes([int(self.setup_mode)])
                + key_bytes,
            )
        if message == 1:
            body = bytearray(36)
            body[0] = 1  # system_run
            body[1] = int(self.system_auto)
            body[2] = self.outputs
            body[3] = self.manual
            body[4] = self.auto
            body[5] = int(self.eco_mode)
            body[6] = self.eco
            body[7] = self.eco_mode_factor
            body[8] = self.eco_active
            body[9:11] = (126).to_bytes(2, "little")  # RTC year
            body[26] = self.sleep
            return self._packet(1, bytes(body))

        if self.refuse_commands:
            return self._packet(message, b"\x00")
        if message == 5:
            self.system_auto = bool(payload[0])
        elif message == 8:
            self.eco_mode = bool(payload[0])
        elif message == 7:  # state, zone
            self.manual = _set_bit(self.manual, payload[1], payload[0])
        elif message in (6, 9, 14):  # zone, state
            attr = {6: "auto", 9: "eco", 14: "sleep"}[message]
            setattr(self, attr, _set_bit(getattr(self, attr), payload[0], payload[1]))
        else:
            return b""
        return self._packet(message, b"\x01")

    async def open_connection(self, host: str, port: int):
        if not self.reachable:
            raise OSError("Host unreachable")
        reader = asyncio.StreamReader()
        return reader, _FakeWriter(self, reader)


def _set_bit(mask: int, index: int, on: int) -> int:
    return mask | (1 << index) if on else mask & ~(1 << index)


class _FakeWriter:
    def __init__(self, device: FakeLichen, reader: asyncio.StreamReader) -> None:
        self._device = device
        self._reader = reader

    def write(self, data: bytes) -> None:
        # The firmware reads each request in one go: one write = one request.
        self._reader.feed_data(self._device.handle(bytes(data)))
        self._reader.feed_eof()

    async def drain(self) -> None:
        return

    def close(self) -> None:
        return

    async def wait_closed(self) -> None:
        return


@pytest.fixture
def lichen() -> Generator[FakeLichen]:
    """A fake device that every P2PDevice connection reaches."""
    device = FakeLichen()
    with patch(
        "custom_components.playtopro.P2PDevice.open_connection", device.open_connection
    ):
        yield device


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """An entry for the fake device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Lichen {SERIAL}",
        unique_id=str(SERIAL),
        version=1,
        minor_version=2,
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SERIAL_NUMBER: SERIAL,
            CONF_PRIVATE_KEY: KEY,
            CONF_FIRMWARE: 28,
        },
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Skip entry setup in config flow tests."""
    with patch("custom_components.playtopro.async_setup_entry", return_value=True):
        yield
