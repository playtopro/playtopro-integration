"""Fixtures for playtopro tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.playtopro.const import (
    CONF_FIRMWARE,
    CONF_PRIVATE_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT

from tests.common import MockConfigEntry

HOST = "192.168.1.137"
PORT = 1233
SERIAL = 1001
FIRMWARE = 28
PRIVATE_KEY = 0x0001E21F


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip real entry setup (coordinator, platforms, frontend card)."""
    with patch(
        "homeassistant.components.playtopro.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_device() -> Generator[MagicMock]:
    """Mock the P2PDevice used by the config flow.

    By default the device answers like a real unit in setup mode.
    """
    with patch(
        "homeassistant.components.playtopro.P2PFlowBase.P2PDevice", autospec=True
    ) as device_class:
        device = device_class.return_value
        device.async_get_firmware.return_value = MagicMock(
            serial_number=SERIAL, firmware=FIRMWARE, mode=1, private_key=PRIVATE_KEY
        )
        device.async_get_status.return_value = MagicMock()
        yield device


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a configured playtopro entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Lichen {SERIAL}",
        unique_id=str(SERIAL),
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SERIAL_NUMBER: SERIAL,
            CONF_PRIVATE_KEY: PRIVATE_KEY,
            CONF_FIRMWARE: FIRMWARE,
        },
    )
