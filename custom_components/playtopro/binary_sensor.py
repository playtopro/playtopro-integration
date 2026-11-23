"""P2P binary sensors: whether each zone is watering."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import P2PConfigEntry, P2PDataUpdateCoordinator
from .entity import P2PZoneEntity
from .P2PDevice import ZONE_COUNT

# Entities only read coordinator data.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: P2PConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up P2P binary sensors based on a config entry."""
    async_add_entities(
        P2PZoneSensor(entry.runtime_data, index) for index in range(ZONE_COUNT)
    )


class P2PZoneSensor(P2PZoneEntity, BinarySensorEntity):
    """On while the zone's valve is open."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:sprinkler"

    def __init__(self, coordinator: P2PDataUpdateCoordinator, index: int) -> None:
        """Initialize the zone sensor."""
        super().__init__(coordinator, "zone", index)
        self._attr_name = f"Zone {index + 1:02d}"

    @property
    def is_on(self) -> bool:
        """Return true while the zone is watering."""
        return self.zone.on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return why the zone is (or isn't) running."""
        return {
            "manual_mode_active": self.zone.manual_mode_active,
            "eco_mode_active": self.zone.eco_mode_active,
        }
