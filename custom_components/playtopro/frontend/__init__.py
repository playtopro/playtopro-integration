"""PlayToPro: serve the card and register it as a dashboard resource."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import MODE_STORAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)

LOVELACE_RETRY_SECONDS = 5


class JSModuleRegistration:
    """Register JavaScript modules for PlayToPro."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        self.hass = hass
        # LovelaceData; None when the dashboard integration isn't loaded.
        self.lovelace: Any = hass.data.get("lovelace")
        # `resource_mode` replaced `mode` in HA 2026.2.
        self.resource_mode = getattr(
            self.lovelace, "resource_mode", getattr(self.lovelace, "mode", None)
        )

    @property
    def _manages_resources(self) -> bool:
        """Resources can only be edited in storage mode."""
        return self.lovelace is not None and self.resource_mode == MODE_STORAGE

    async def async_register(self) -> None:
        """Serve /playtopro/* and, in storage mode, add the dashboard resource."""
        await self._async_register_path()
        if self._manages_resources:
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Serve this folder at /playtopro."""
        if self.hass.http is None:
            return
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(Path(__file__).parent), True)]
            )
        except RuntimeError:
            _LOGGER.debug("Resource path already registered")

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait for the dashboard resources to load, then register the card."""

        async def _check_loaded(_now: Any) -> None:
            if getattr(self.lovelace.resources, "loaded", True):
                await self._async_register_modules()
            else:
                _LOGGER.debug("Dashboard resources not loaded yet; retrying")
                async_call_later(self.hass, LOVELACE_RETRY_SECONDS, _check_loaded)

        await _check_loaded(None)

    async def _async_resource_items(self) -> list[dict[str, Any]]:
        if not getattr(self.lovelace.resources, "loaded", True):
            await self.lovelace.resources.async_load()
        return list(self.lovelace.resources.async_items())

    async def _async_register_modules(self) -> None:
        """Add the card resource, or update its version."""
        resources = [
            r for r in await self._async_resource_items() if str(r["url"]).startswith(URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            new_url = f"{url}?v={module['version']}"
            existing = next(
                (r for r in resources if self._get_resource_path(r["url"]) == url),
                None,
            )

            if existing is None:
                _LOGGER.debug("Registering %s %s", module["name"], module["version"])
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": new_url}
                )
            elif self._get_resource_version(existing["url"]) != module["version"]:
                _LOGGER.debug("Updating %s to %s", module["name"], module["version"])
                await self.lovelace.resources.async_update_item(
                    existing["id"], {"res_type": "module", "url": new_url}
                )
                await self.hass.async_add_executor_job(self._remove_gzip_files)

    async def async_unregister(self) -> None:
        """Remove the card resource (storage mode only)."""
        if not self._manages_resources:
            return
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            for resource in await self._async_resource_items():
                if self._get_resource_path(str(resource["url"])) == url:
                    await self.lovelace.resources.async_delete_item(resource["id"])

    @staticmethod
    def _get_resource_path(url: str) -> str:
        return url.split("?", 1)[0]

    @staticmethod
    def _get_resource_version(url: str) -> str:
        parts = url.split("?", 1)
        if len(parts) == 2 and "v=" in parts[1]:
            return parts[1].split("v=", 1)[1]
        return "0"

    @staticmethod
    def _remove_gzip_files() -> None:
        """Remove cached .gz files older than their .js file."""
        for file in Path(__file__).parent.glob("*.gz"):
            js = file.with_suffix("")
            try:
                if js.exists() and file.stat().st_mtime < js.stat().st_mtime:
                    _LOGGER.debug("Removing older gzip file %s", file.name)
                    file.unlink(missing_ok=True)
            except OSError:
                pass
