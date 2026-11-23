"""The lichen playtopro integration."""

# To validate the integration, run:
# python3 -m script.hassfest --integration-path ./components/playtopro
# You have to set your target level in your manifest.json.
# To bypass the check so your integration will load, first set:
# "quality_scale":"internal"
# Then, tell home assistant to bypass the check.
# Locate script/hassfest/quality_scale.py
# Locate INTEGRATIONS_WITHOUT_SCALE, and add the domain name - playtopro.
# To confirm, rerun the following and you should get a pass:
# python3 -m script.hassfest --integration-path ./homeassistant/components/playtopro
# NOTE you must run this from the hacore folder.
# Finally, to have your integration included, run:
# python3 -m script.hassfest
# NOTE you must run this from the hacore folder.
# To confirm that your integration in now available, check:
# from the UI, go to Configuration -> Integrations, and click the + button. You should see your integration listed.
# Devices announce via zeroconfig (mDNS). Since HA is hosted inside a docker container, you need to emulate zeroconfig from the command line.
# From the terminal inside the docker container, install run:
# sudo apt update
# sudo apt install avahi-utils
# sudo mkdir -p /run/dbus
# sudo dbus-daemon --system --fork
# sudo avahi-daemon --no-chroot
# Now from a separate terminal, run the following command to announce your device:
# avahi-publish-service "lichen" _playtopro._tcp 1233 "serial=123456" "firmware=28"

# You can do this by running:
# sudo chown -R vscode ./playtopro
# NOTE To have your translations inclided into Home Assistant
# you must run:
# python3 -m script.translations develop

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SERIAL_NUMBER, DOMAIN, LOGGER
from .coordinator import P2PConfigEntry, P2PDataUpdateCoordinator
from .frontend import JSModuleRegistration
from .P2PDevice import ZONE_COUNT

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card and add it to the dashboard resources, once."""
    await JSModuleRegistration(hass).async_register()
    return True


async def async_setup_entry(hass: HomeAssistant, entry: P2PConfigEntry) -> bool:
    """Set up lichen playtopro from a config entry."""
    coordinator = P2PDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: P2PConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: P2PConfigEntry) -> None:
    """Remove the card resource when the last device is removed."""
    if not any(
        other.entry_id != entry.entry_id
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        await JSModuleRegistration(hass).async_unregister()


async def async_migrate_entry(hass: HomeAssistant, entry: P2PConfigEntry) -> bool:
    """Migrate entries created by older versions."""
    if entry.version > 1:
        return False

    if entry.minor_version < 2:
        serial_number = str(entry.data[CONF_SERIAL_NUMBER])

        # The device identifier used to be an int; it must be a str.
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, int(serial_number))}  # type: ignore[arg-type]
        )
        if device is not None:
            device_registry.async_update_device(
                device.id, new_identifiers={(DOMAIN, serial_number)}
            )

        # Zone sensors moved from the sensor to the binary_sensor platform.
        entity_registry = er.async_get(hass)
        for index in range(ZONE_COUNT):
            if entity_id := entity_registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, f"{serial_number}_zone_{index:02d}"
            ):
                entity_registry.async_remove(entity_id)

        hass.config_entries.async_update_entry(entry, minor_version=2)
        LOGGER.debug("Migrated %s to version 1.2", entry.title)

    return True
