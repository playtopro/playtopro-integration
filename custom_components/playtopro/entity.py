"""Base class for P2P entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FIRMWARE, CONF_SERIAL_NUMBER, DOMAIN
from .coordinator import P2PDataUpdateCoordinator
from .P2PDevice import P2PZone


class P2PEntity(CoordinatorEntity[P2PDataUpdateCoordinator]):
    """Defines a base P2P entity.

    The unique ID is "<serial>_<key>". The card relies on these keys, so don't
    change them.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: P2PDataUpdateCoordinator, key: str) -> None:
        """Initialize P2P entity."""
        super().__init__(coordinator)
        data = coordinator.config_entry.data
        serial_number = str(data[CONF_SERIAL_NUMBER])

        self._attr_unique_id = f"{serial_number}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            model="lichen play",
            manufacturer="playtopro",
            name=f"PlayToPro {serial_number}",
            sw_version=str(data[CONF_FIRMWARE]),
            serial_number=serial_number,
        )


class P2PZoneEntity(P2PEntity):
    """An entity for one of the eight zones."""

    def __init__(
        self, coordinator: P2PDataUpdateCoordinator, key: str, index: int
    ) -> None:
        """Initialize the zone entity; `key` gets the zone suffix."""
        super().__init__(coordinator, f"{key}_{index:02d}")
        self.index = index

    @property
    def zone(self) -> P2PZone:
        """The zone's latest state."""
        return self.coordinator.data.zones[self.index]
