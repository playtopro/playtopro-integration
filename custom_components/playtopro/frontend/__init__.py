"""PlayToPro – JavaScript module registration."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import MODE_STORAGE, LovelaceData
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import JSMODULES, URL_BASE  # module list + /playtopro base

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Register JavaScript modules for PlayToPro."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        # Lovelace keeps its data object in hass.data["lovelace"] (a LovelaceData dataclass)
        self.lovelace: LovelaceData = self.hass.data.get("lovelace")

        # Future-proof: HA 2026.2 introduces breaking changes to Lovelace data access.
        # If resource_mode exists, use it, otherwise fall back to mode.
        # (Safer than checking MAJOR/MINOR only.)
        if hasattr(self.lovelace, "resource_mode"):
            self.resource_mode = self.lovelace.resource_mode
        else:
            self.resource_mode = getattr(self.lovelace, "mode", None)

    async def async_register(self) -> None:
        """Register static path and (in storage mode) add Lovelace resources."""
        await self._async_register_path()
        if self.lovelace and self.resource_mode == MODE_STORAGE:
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Register /playtopro/* → this package dir (async, non-deprecated API)."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, Path(__file__).parent, cache_headers=True)]
            )
            _LOGGER.debug("Registered resource path from %s", Path(__file__).parent)
        except RuntimeError:
            # Path likely already registered on reload
            _LOGGER.debug("Resource path already registered")

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait for Lovelace resources to finish loading, then register modules."""

        async def _check_lovelace_resources_loaded(_now):
            # ResourceStorageCollection exposes a 'loaded' flag after loading storage
            if getattr(self.lovelace.resources, "loaded", True):
                await self._async_register_modules()
            else:
                _LOGGER.debug(
                    "Lovelace resources not yet loaded; retrying in 5 seconds"
                )
                async_call_later(self.hass, 5, _check_lovelace_resources_loaded)

        await _check_lovelace_resources_loaded(0)

    async def _async_register_modules(self) -> None:
        """Ensure our card(s) are present and versioned (storage mode)."""
        _LOGGER.debug("Installing JavaScript modules")

        # Recent cores keep a ResourceStorageCollection with items accessible from the loop.
        # Some builds expose async_items(); if it’s sync, just call it.
        items = self.lovelace.resources.async_items()
        if callable(getattr(items, "__await__", None)):
            items = await items  # type: ignore

        resources = [
            resource for resource in items if str(resource["url"]).startswith(URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{URL_BASE}/{module.get('filename')}"
            new_url = f"{url}?v={module.get('version')}"

            # Already registered?
            existing = next(
                (r for r in resources if self._get_resource_path(r["url"]) == url),
                None,
            )

            if existing:
                # If version changed, update
                if self._get_resource_version(existing["url"]) != module.get("version"):
                    _LOGGER.debug(
                        "Updating %s to version %s",
                        module.get("name"),
                        module.get("version"),
                    )
                    await self.lovelace.resources.async_update_item(
                        existing.get("id"),
                        {"res_type": "module", "url": new_url},
                    )
                    await self.async_remove_gzip_files()
                else:
                    _LOGGER.debug(
                        "%s already registered as version %s",
                        module.get("name"),
                        module.get("version"),
                    )
            else:
                _LOGGER.debug(
                    "Registering %s as version %s",
                    module.get("name"),
                    module.get("version"),
                )
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": new_url}
                )

    @staticmethod
    def _get_resource_path(url: str) -> str:
        return url.split("?", 1)[0]

    @staticmethod
    def _get_resource_version(url: str) -> str:
        parts = url.split("?", 1)
        if len(parts) == 2:
            q = parts[1]
            if q.startswith("v="):
                return q.replace("v=", "")
            # Support '... ?v=1.2.3' and also any accidental '...?param=v=...'
            if "v=" in q:
                return q.split("v=", 1)[1]
        return "0"

    async def async_unregister(self) -> None:
        """Remove Lovelace resources on unload (storage mode only)."""
        if self.resource_mode != MODE_STORAGE:
            return

        items = self.lovelace.resources.async_items()
        if callable(getattr(items, "__await__", None)):
            items = await items  # type: ignore

        for module in JSMODULES:
            url = f"{URL_BASE}/{module.get('filename')}"
            for res in list(items):
                if str(res["url"]).startswith(url):
                    await self.lovelace.resources.async_delete_item(res.get("id"))

    async def async_remove_gzip_files(self) -> None:
        """Remove stale .gz files (done off the event loop)."""
        await self.hass.async_add_executor_job(self._remove_gzip_files)

    def _remove_gzip_files(self) -> None:
        """Remove cached gzip files in this package dir if the .js is newer."""
        # CHANGED: Use this folder, not a hard-coded "wiser" path.
        path = Path(__file__).parent
        try:
            for file in path.glob("*.gz"):
                js = file.with_suffix("")  # strip .gz
                try:
                    if js.exists() and file.stat().st_mtime < js.stat().st_mtime:
                        _LOGGER.debug("Removing older gzip file - %s", file.name)
                        file.unlink(missing_ok=True)
                except OSError:
                    pass
        except OSError:
            pass
