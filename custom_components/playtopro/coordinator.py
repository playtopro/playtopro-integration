"""DataUpdateCoordinator for P2PDevice."""

from __future__ import annotations

from typing import Any
import copy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SERIAL_NUMBER, CONF_PRIVATE_KEY, DOMAIN, LOGGER, SCAN_INTERVAL
from .P2PDevice import P2PConfirmationResponse, P2PDevice, P2PError, P2PStatusResponse


class P2PDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching P2P data from single endpoint."""

    device: P2PDevice
    status_response: P2PStatusResponse | None

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
    ) -> None:
        """Initialize global P2P data updater."""

        # self.unsub: CALLBACK_TYPE | None = None

        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

        self.status_response = None

    async def _async_setup(self):
        """Setup the coordinator."""
        self.device = P2PDevice(
            ipv4=self.config_entry.data[CONF_HOST],
            port=self.config_entry.data[CONF_PORT],
            private_key=self.config_entry.data[
                CONF_PRIVATE_KEY
            ],  # , session=async_get_clientsession(hass)
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from P2PDevice ."""
        try:
            self.status_response: P2PStatusResponse = (
                await self.device.async_get_status()
            )

            data: dict[str, Any] = {}
            data["status"] = self.status_response
        except P2PError as e:
            raise UpdateFailed(f"Unable to update data: {e.error}") from e
        else:
            return data

    async def async_set_zone_manual_mode(self, zone: int, state: bool) -> bool:
        """Set zone manual mode."""
        try:
            response: P2PConfirmationResponse = (
                await self.device.async_set_zone_manual_mode(zone, state)
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response is not None:
                    self.status_response.zones[zone].manual_mode_active = state
                    self.async_set_updated_data({"status": self.status_response})

                # Always reconcile with device truth
                self.async_request_refresh()

                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set zone manual mode: {error}") from error
        else:
            return response.result

    async def async_set_auto_mode(self, state: bool) -> bool:
        """Set device auto mode."""
        try:
            response: P2PConfirmationResponse = await self.device.async_set_auto_mode(
                state
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response:
                    self.status_response.system_auto = state
                    self.async_set_updated_data({"status": self.status_response})
                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set auto mode: {error}") from error
        else:
            return response.result

    async def async_set_zone_auto_mode(self, zone: int, state: bool) -> bool:
        """Set zone auto mode."""
        try:
            response: P2PConfirmationResponse = (
                await self.device.async_set_zone_auto_mode(zone, state)
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response:
                    self.status_response.zones[zone].auto_mode = state
                    self.async_set_updated_data({"status": self.status_response})
                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set zone auto mode: {error}") from error
        else:
            return response.result

    async def async_set_eco_mode(self, state: bool) -> bool:
        """Set device eco mode."""
        try:
            response: P2PConfirmationResponse = await self.device.async_set_eco_mode(
                state
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response:
                    self.status_response.eco_mode = state
                    self.async_set_updated_data({"status": self.status_response})
                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set eco mode: {error}") from error
        else:
            return response.result

    async def async_set_zone_eco_mode(self, zone: int, state: bool) -> bool:
        """Set zone eco mode."""
        try:
            response: P2PConfirmationResponse = (
                await self.device.async_set_zone_eco_mode(zone, state)
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response:
                    self.status_response.zones[zone].eco_mode = state
                    self.async_set_updated_data({"status": self.status_response})
                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set zone eco mode: {error}") from error
        else:
            return response.result

    async def async_set_zone_sleep_mode(self, zone: int, state: bool) -> bool:
        """Set zone sleep mode."""
        try:
            response: P2PConfirmationResponse = (
                await self.device.async_set_zone_sleep_mode(zone, state)
            )

            # Check the result and update the stored status for the device
            if response.result:
                if self.status_response:
                    self.status_response.zones[zone].sleep_mode = state
                    self.async_set_updated_data({"status": self.status_response})
                return True
            return False

        except P2PError as error:
            raise UpdateFailed(f"Unable to set zone sleep mode: {error}") from error
        else:
            return response.result
