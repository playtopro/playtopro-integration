"""P2P Sensors."""

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_SERIAL_NUMBER
from .coordinator import P2PDataUpdateCoordinator
from .entity import P2PEntity
from .P2PDevice import P2PStatusResponse, P2PZone


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up P2P sensor based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([P2PEcoModeFactor(coordinator)])
    async_add_entities([P2PZoneSensor(coordinator, index) for index in range(8)])


class P2PEcoModeFactor(P2PEntity, SensorEntity):
    """P2P Sensor."""

    _attr_icon = "mdi:water-percent"
    _attr_has_entity_name = True

    def __init__(self, coordinator: P2PDataUpdateCoordinator) -> None:
        """Initializes the Switch."""
        super().__init__(coordinator)
        # Setup unique ID for this entity
        if self.coordinator.config_entry is not None:
            serial_number: str = self.coordinator.config_entry.data[CONF_SERIAL_NUMBER]
            self._attr_unique_id = f"{serial_number}_eco_mode_factor"
            self._attr_name = "Eco Mode Factor"
            self._attr_native_unit_of_measurement = PERCENTAGE

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None:
            if self.coordinator.data["status"]:
                status_response: P2PStatusResponse = self.coordinator.data["status"]
                self._attr_native_value = status_response.eco_mode_factor

        self.async_write_ha_state()


class P2PZoneSensor(P2PEntity, BinarySensorEntity):
    """P2P Sensor."""

    _attr_icon = "mdi:sprinkler"
    _attr_has_entity_name = True
    index: int

    def __init__(self, coordinator: P2PDataUpdateCoordinator, index: int) -> None:
        """Initializes the Switch."""
        super().__init__(coordinator)
        # Setup unique ID for this entity
        if self.coordinator.config_entry is not None:
            serial_number: str = self.coordinator.config_entry.data[CONF_SERIAL_NUMBER]
            self._attr_unique_id = f"{serial_number}_zone_{index:02d}"
            self._attr_name = f"Zone {(index + 1):02d}"

        self.index = index

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None:
            if self.coordinator.data["status"]:
                status_response: P2PStatusResponse = self.coordinator.data["status"]
                zone: P2PZone = status_response.zones[self.index]
                self._attr_is_on = zone.on

        self.async_write_ha_state()


    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""

        result: dict[str, Any] = {}

        if self.coordinator.data is not None:
            if self.coordinator.data["status"]:
                status_response: P2PStatusResponse = self.coordinator.data["status"]
                zone: P2PZone = status_response.zones[self.index]
                result = {
                    "manual_mode_active": zone.manual_mode_active,
                    "eco_mode_active": zone.eco_mode_active,
                    # "sleep_mode_active": zone.sleep_mode_active,
                }
        return result
