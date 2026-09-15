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

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import P2PDataUpdateCoordinator

# NEW: import the helper functions
from .frontend import JSModuleRegistration

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up lichen playtopro from a config entry."""

    # Register static path so /playtopro/playtopro-card.js is served

    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = P2PDataUpdateCoordinator(hass, entry=entry)
    await entry.runtime_data.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register custom cards
    module_register = JSModuleRegistration(hass)
    await module_register.async_register()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
