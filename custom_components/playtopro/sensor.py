"""P2P Sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import P2PConfigEntry, P2PDataUpdateCoordinator
from .entity import P2PEntity

# Entities only read coordinator data.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: P2PConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up P2P sensors based on a config entry."""
    async_add_entities([P2PEcoModeFactor(entry.runtime_data)])


class P2PEcoModeFactor(P2PEntity, SensorEntity):
    """Percentage of the normal run time used while eco mode is active."""

    _attr_icon = "mdi:water-percent"
    _attr_name = "Eco Mode Factor"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: P2PDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "eco_mode_factor")

    @property
    def native_value(self) -> int:
        """Return the eco mode factor."""
        return self.coordinator.data.eco_mode_factor
