"""Base class for P2P entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FIRMWARE, DOMAIN
from .coordinator import CONF_SERIAL_NUMBER, P2PDataUpdateCoordinator


class P2PEntity(CoordinatorEntity[P2PDataUpdateCoordinator]):
    """Defines a base P2P entity."""

    def __init__(self, coordinator: P2PDataUpdateCoordinator) -> None:
        """Initialize P2P entity."""
        super().__init__(coordinator)

        if self.coordinator.config_entry is not None:
            serial_number: int = int(
                self.coordinator.config_entry.data[CONF_SERIAL_NUMBER]
            )

            firmware: int = int(self.coordinator.config_entry.data[CONF_FIRMWARE])

            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, serial_number)},
                model="lichen play",
                manufacturer="playtopro",
                name=f"PlayToPro {serial_number}",
                sw_version=str(firmware),
                serial_number=str(serial_number),
            )
