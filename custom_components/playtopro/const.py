"""Constants for the lichen playtopro integration."""

from datetime import timedelta
import logging

DOMAIN = "playtopro"
CONF_SERIAL_NUMBER = "serial_number"
CONF_FIRMWARE = "firmware"
CONF_PRIVATE_KEY = "private_key"
LOGGER = logging.getLogger(__package__)
SCAN_INTERVAL = timedelta(seconds=3)
URL_BASE = "/playtopro"


JSMODULES = [
    {
        "name": "Playtopro Card",
        "filename": "playtopro-card.js",
        "version": "2026.2.10",
    }
]
