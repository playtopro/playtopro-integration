"""DataUpdateCoordinator for P2PDevice."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PRIVATE_KEY, DOMAIN, LOGGER, SCAN_INTERVAL
from .P2PDevice import P2PDevice, P2PError, P2PRejectedError, P2PStatusResponse

type P2PConfigEntry = ConfigEntry[P2PDataUpdateCoordinator]


class P2PDataUpdateCoordinator(DataUpdateCoordinator[P2PStatusResponse]):
    """Polls the device status and sends commands to it."""

    config_entry: P2PConfigEntry

    def __init__(self, hass: HomeAssistant, entry: P2PConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.device = P2PDevice(
            host=entry.data[CONF_HOST],
            port=int(entry.data[CONF_PORT]),
            private_key=int(entry.data[CONF_PRIVATE_KEY]),
        )

    async def _async_update_data(self) -> P2PStatusResponse:
        """Fetch the status from the device."""
        try:
            return await self.device.async_get_status()
        except P2PRejectedError:
            pass
        except P2PError as err:
            raise UpdateFailed(f"Unable to get status: {err}") from err

        # Rejected: ask once more so a single dropped request doesn't start
        # re-authentication, then treat a second rejection as a bad key.
        try:
            return await self.device.async_get_status()
        except P2PRejectedError as err:
            raise ConfigEntryAuthFailed(
                "The device rejected the saved private key"
            ) from err
        except P2PError as err:
            raise UpdateFailed(f"Unable to get status: {err}") from err

    async def async_send_command(self, command: Awaitable[bool]) -> None:
        """Send a command, raise if it fails, then refresh the status."""
        try:
            accepted = await command
        except P2PError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if not accepted:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_refused"
            )
        await self.async_request_refresh()
