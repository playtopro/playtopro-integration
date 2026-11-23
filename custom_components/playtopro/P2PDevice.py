"""Client for the Lichen Play local (P2P) protocol.

Every packet, in both directions, is laid out as:

    0       '$'
    1..4    serial number (requests: private key), uint32 little-endian
    5       packet (message) number
    6       packet counter
    7       payload length
    8..     payload
    last    '!'

The device reads each request with non-blocking reads, so a request must be
sent in a single write. When it rejects a request (for example, a wrong
private key) it closes the connection without replying.
"""

from __future__ import annotations

import asyncio
from asyncio import open_connection
from contextlib import suppress
from dataclasses import dataclass

HEADER = ord("$")
FOOTER = ord("!")
HEADER_LENGTH = 8
REQUEST_TIMEOUT = 5  # seconds, covers connect, send and receive
ZONE_COUNT = 8

PACKET_FIRMWARE = 0
PACKET_STATUS = 1
PACKET_AUTO_MODE = 5
PACKET_ZONE_AUTO_MODE = 6
PACKET_ZONE_MANUAL_MODE = 7
PACKET_ECO_MODE = 8
PACKET_ZONE_ECO_MODE = 9
PACKET_ZONE_SLEEP_MODE = 14

FIRMWARE_PAYLOAD_LENGTH = 7  # firmware 27 and later
STATUS_MIN_PAYLOAD_LENGTH = 27  # bytes 8..34, everything parsed below


# ---------------------------------------------------------------------------
# Errors. `error` is a translation key under config.error in strings.json.
# ---------------------------------------------------------------------------


class P2PError(Exception):
    """Base class for P2P errors."""

    error = "unknown"

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        super().__init__(message)


class P2PConnectionError(P2PError):
    """The device could not be reached, or timed out."""

    error = "cannot_connect"


class P2PRejectedError(P2PError):
    """The device closed the connection without replying."""

    error = "request_rejected"


class P2PInvalidResponseError(P2PError):
    """The device replied with a malformed or unexpected packet."""

    error = "invalid_response"


class P2PFirmwareNotSupportedError(P2PError):
    """The device firmware is too old for local control."""

    error = "firmware_not_supported"


# ---------------------------------------------------------------------------
# Packets
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class P2PRequest:
    """A request packet."""

    private_key: int
    packet: int
    payload: bytes = b""
    packet_counter: int = 0

    def to_bytes(self) -> bytes:
        """Encode the request for sending."""
        return (
            bytes([HEADER])
            + self.private_key.to_bytes(4, "little")
            + bytes([self.packet, self.packet_counter, len(self.payload)])
            + self.payload
            + bytes([FOOTER])
        )


@dataclass(slots=True)
class P2PResponse:
    """A response packet: the decoded header plus the raw packet."""

    raw: bytes
    serial_number: int
    packet: int
    packet_counter: int
    length: int

    @classmethod
    def from_bytes(cls, raw: bytes) -> P2PResponse:
        """Decode and validate a complete response packet."""
        if len(raw) < HEADER_LENGTH + 1 or raw[0] != HEADER:
            raise P2PInvalidResponseError("Unexpected header")
        length = raw[7]
        if len(raw) != HEADER_LENGTH + length + 1 or raw[-1] != FOOTER:
            raise P2PInvalidResponseError("Unexpected packet length or footer")
        return cls(
            raw=raw,
            serial_number=int.from_bytes(raw[1:5], "little"),
            packet=raw[5],
            packet_counter=raw[6],
            length=length,
        )

    def u8(self, offset: int) -> int:
        """Read one byte at a packet offset."""
        return self.raw[offset]

    def u16(self, offset: int) -> int:
        """Read a little-endian uint16 at a packet offset."""
        return int.from_bytes(self.raw[offset : offset + 2], "little")

    def u32(self, offset: int) -> int:
        """Read a little-endian uint32 at a packet offset."""
        return int.from_bytes(self.raw[offset : offset + 4], "little")


@dataclass(slots=True)
class P2PFirmwareResponse:
    """Reply to packet 0: serial number, firmware, mode and (in setup mode) key."""

    serial_number: int
    firmware: int
    mode: int
    private_key: int

    @classmethod
    def from_response(cls, response: P2PResponse) -> P2PFirmwareResponse:
        """Parse a packet 0 response."""
        if response.length < FIRMWARE_PAYLOAD_LENGTH:
            # Firmware older than 27 only returns the serial number.
            raise P2PFirmwareNotSupportedError(
                f"Firmware response too short ({response.length} bytes)"
            )
        return cls(
            serial_number=response.serial_number,
            firmware=response.u16(8),
            mode=response.u8(10),
            private_key=response.u32(11),
        )


@dataclass(slots=True)
class P2PZone:
    """State of one irrigation zone."""

    index: int
    on: bool
    manual_mode_active: bool
    auto_mode: bool
    eco_mode: bool
    eco_mode_active: bool
    sleep_mode: bool


@dataclass(slots=True)
class P2PStatusResponse:
    """Reply to packet 1: the system status."""

    system_run: bool
    system_auto: bool
    eco_mode: bool
    eco_mode_factor: int
    sleep_mode: bool
    zones: list[P2PZone]

    @classmethod
    def from_response(cls, response: P2PResponse) -> P2PStatusResponse:
        """Parse a packet 1 response (offsets match the firmware's comments)."""
        if response.length < STATUS_MIN_PAYLOAD_LENGTH:
            raise P2PInvalidResponseError(
                f"Status response too short ({response.length} bytes)"
            )
        outputs = response.u8(10)
        manual = response.u8(11)
        auto = response.u8(12)
        eco = response.u8(14)
        eco_active = response.u8(16)
        sleep = response.u8(34)

        def bit(mask: int, index: int) -> bool:
            return bool((mask >> index) & 0x01)

        return cls(
            system_run=bool(response.u8(8)),
            system_auto=bool(response.u8(9)),
            eco_mode=bool(response.u8(13)),
            eco_mode_factor=response.u8(15),
            sleep_mode=bool(response.u8(25)),
            zones=[
                P2PZone(
                    index=i,
                    on=bit(outputs, i),
                    manual_mode_active=bit(manual, i),
                    auto_mode=bit(auto, i),
                    eco_mode=bit(eco, i),
                    eco_mode_active=bit(eco_active, i),
                    sleep_mode=bit(sleep, i),
                )
                for i in range(ZONE_COUNT)
            ],
        )


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


class P2PDevice:
    """Talks to one Lichen Play over its local TCP port."""

    def __init__(self, host: str, port: int, private_key: int) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.private_key = private_key
        # The device handles one request at a time; don't overlap ours.
        self._lock = asyncio.Lock()

    async def async_get_firmware(self) -> P2PFirmwareResponse:
        """Get serial number, firmware and mode.

        The device always answers this packet. Send the serial number as the
        key; in setup mode the reply also carries the private key.
        """
        response = await self._async_request(P2PRequest(self.private_key, PACKET_FIRMWARE))
        return P2PFirmwareResponse.from_response(response)

    async def async_get_status(self) -> P2PStatusResponse:
        """Get the current status."""
        response = await self._async_request(P2PRequest(self.private_key, PACKET_STATUS))
        return P2PStatusResponse.from_response(response)

    async def async_set_auto_mode(self, state: bool) -> bool:
        """Turn the device schedule on or off."""
        return await self._async_command(PACKET_AUTO_MODE, bytes([state]))

    async def async_set_eco_mode(self, state: bool) -> bool:
        """Turn device eco mode on or off."""
        return await self._async_command(PACKET_ECO_MODE, bytes([state]))

    async def async_set_zone_manual_mode(self, zone: int, state: bool) -> bool:
        """Start or stop a manual run (this packet takes state before zone)."""
        return await self._async_command(PACKET_ZONE_MANUAL_MODE, bytes([state, zone]))

    async def async_set_zone_auto_mode(self, zone: int, state: bool) -> bool:
        """Turn a zone's schedule on or off."""
        return await self._async_command(PACKET_ZONE_AUTO_MODE, bytes([zone, state]))

    async def async_set_zone_eco_mode(self, zone: int, state: bool) -> bool:
        """Turn a zone's eco mode on or off."""
        return await self._async_command(PACKET_ZONE_ECO_MODE, bytes([zone, state]))

    async def async_set_zone_sleep_mode(self, zone: int, state: bool) -> bool:
        """Turn a zone's sleep mode on or off."""
        return await self._async_command(PACKET_ZONE_SLEEP_MODE, bytes([zone, state]))

    async def _async_command(self, packet: int, payload: bytes) -> bool:
        """Send a command and return the device's confirmation flag."""
        response = await self._async_request(P2PRequest(self.private_key, packet, payload))
        if response.length < 1:
            raise P2PInvalidResponseError("Confirmation response is empty")
        return response.u8(8) > 0

    async def _async_request(self, request: P2PRequest) -> P2PResponse:
        """Send one request on a fresh connection and read the reply."""
        async with self._lock:
            writer: asyncio.StreamWriter | None = None
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    reader, writer = await open_connection(self.host, self.port)
                    writer.write(request.to_bytes())
                    await writer.drain()
                    header = await reader.readexactly(HEADER_LENGTH)
                    if header[0] != HEADER:
                        raise P2PInvalidResponseError("Unexpected header")
                    body = await reader.readexactly(header[7] + 1)
            except asyncio.IncompleteReadError as err:
                raise P2PRejectedError(
                    "Device closed the connection without replying"
                ) from err
            except TimeoutError as err:
                raise P2PConnectionError(
                    f"Timed out talking to {self.host}:{self.port}"
                ) from err
            except OSError as err:
                raise P2PConnectionError(
                    f"Cannot connect to {self.host}:{self.port}: {err}"
                ) from err
            finally:
                if writer is not None:
                    writer.close()
                    with suppress(OSError):
                        await writer.wait_closed()

        response = P2PResponse.from_bytes(header + body)
        if response.packet != request.packet:
            raise P2PInvalidResponseError(
                f"Expected packet {request.packet}, got {response.packet}"
            )
        return response
