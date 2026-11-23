"""P2P Irrigation Switches."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import P2PConfigEntry, P2PDataUpdateCoordinator
from .entity import P2PEntity, P2PZoneEntity
from .P2PDevice import ZONE_COUNT, P2PDevice, P2PStatusResponse, P2PZone

# The device handles one request at a time.
PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class P2PSwitchDescription(SwitchEntityDescription):
    """A device-wide switch."""

    is_on_fn: Callable[[P2PStatusResponse], bool]
    set_fn: Callable[[P2PDevice, bool], Awaitable[bool]]


@dataclass(frozen=True, kw_only=True)
class P2PZoneSwitchDescription(SwitchEntityDescription):
    """A per-zone switch; `key` and `name` get the zone added."""

    is_on_fn: Callable[[P2PZone], bool]
    set_fn: Callable[[P2PDevice, int, bool], Awaitable[bool]]


DEVICE_SWITCHES: tuple[P2PSwitchDescription, ...] = (
    P2PSwitchDescription(
        key="auto_mode",
        name="Auto Mode",
        icon="mdi:checkbox-marked-circle-auto-outline",
        is_on_fn=lambda status: status.system_auto,
        set_fn=lambda device, on: device.async_set_auto_mode(on),
    ),
    P2PSwitchDescription(
        key="eco_mode",
        name="Eco Mode",
        icon="mdi:leaf",
        is_on_fn=lambda status: status.eco_mode,
        set_fn=lambda device, on: device.async_set_eco_mode(on),
    ),
)

ZONE_SWITCHES: tuple[P2PZoneSwitchDescription, ...] = (
    P2PZoneSwitchDescription(
        key="zone_manual_mode",
        name="Manual Mode",
        icon="mdi:run",
        is_on_fn=lambda zone: zone.manual_mode_active,
        set_fn=lambda device, zone, on: device.async_set_zone_manual_mode(zone, on),
    ),
    P2PZoneSwitchDescription(
        key="zone_auto_mode",
        name="Auto Mode",
        icon="mdi:checkbox-marked-circle-auto-outline",
        is_on_fn=lambda zone: zone.auto_mode,
        set_fn=lambda device, zone, on: device.async_set_zone_auto_mode(zone, on),
    ),
    P2PZoneSwitchDescription(
        key="zone_eco_mode",
        name="Eco Mode",
        icon="mdi:leaf",
        is_on_fn=lambda zone: zone.eco_mode,
        set_fn=lambda device, zone, on: device.async_set_zone_eco_mode(zone, on),
    ),
    P2PZoneSwitchDescription(
        key="zone_sleep_mode",
        name="Sleep Mode",
        icon="mdi:sleep",
        is_on_fn=lambda zone: zone.sleep_mode,
        set_fn=lambda device, zone, on: device.async_set_zone_sleep_mode(zone, on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: P2PConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up P2P switches based on a config entry."""
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = [
        P2PSwitch(coordinator, description) for description in DEVICE_SWITCHES
    ]
    entities.extend(
        P2PZoneSwitch(coordinator, description, index)
        for description in ZONE_SWITCHES
        for index in range(ZONE_COUNT)
    )
    async_add_entities(entities)


class P2PSwitch(P2PEntity, SwitchEntity):
    """A device-wide switch."""

    entity_description: P2PSwitchDescription

    def __init__(
        self, coordinator: P2PDataUpdateCoordinator, description: P2PSwitchDescription
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return true if the setting is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the setting on."""
        await self.coordinator.async_send_command(
            self.entity_description.set_fn(self.coordinator.device, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the setting off."""
        await self.coordinator.async_send_command(
            self.entity_description.set_fn(self.coordinator.device, False)
        )


class P2PZoneSwitch(P2PZoneEntity, SwitchEntity):
    """A per-zone switch."""

    entity_description: P2PZoneSwitchDescription

    def __init__(
        self,
        coordinator: P2PDataUpdateCoordinator,
        description: P2PZoneSwitchDescription,
        index: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key, index)
        self.entity_description = description
        self._attr_name = f"Zone {index + 1:02d} {description.name}"

    @property
    def is_on(self) -> bool:
        """Return true if the zone setting is on."""
        return self.entity_description.is_on_fn(self.zone)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the zone setting on."""
        await self.coordinator.async_send_command(
            self.entity_description.set_fn(self.coordinator.device, self.index, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone setting off."""
        await self.coordinator.async_send_command(
            self.entity_description.set_fn(self.coordinator.device, self.index, False)
        )
