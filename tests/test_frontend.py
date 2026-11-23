"""Tests for registering the card as a dashboard resource."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.playtopro.const import JSMODULES, URL_BASE
from homeassistant.core import HomeAssistant

from .conftest import FakeLichen

VERSION = JSMODULES[0]["version"]
CARD = f"{URL_BASE}/playtopro-card.js"


class FakeResources:
    """Stands in for lovelace's ResourceStorageCollection."""

    loaded = True

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items

    def async_items(self) -> list[dict[str, Any]]:
        return list(self.items)

    async def async_create_item(self, data: dict[str, Any]) -> None:
        self.items.append({"id": str(len(self.items)), "url": data["url"]})

    async def async_update_item(self, item_id: str, data: dict[str, Any]) -> None:
        for item in self.items:
            if item["id"] == item_id:
                item["url"] = data["url"]

    async def async_delete_item(self, item_id: str) -> None:
        self.items = [item for item in self.items if item["id"] != item_id]


def _lovelace(hass: HomeAssistant, items: list[dict[str, Any]]) -> FakeResources:
    resources = FakeResources(items)
    hass.data["lovelace"] = SimpleNamespace(resource_mode="storage", resources=resources)
    return resources


async def test_card_added_once_and_removed_with_last_device(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """The resource is added on setup and removed when the last device goes."""
    resources = _lovelace(hass, [{"id": "a", "url": "/local/other.js"}])
    second = MockConfigEntry(domain=config_entry.domain, unique_id="2", data=config_entry.data)
    config_entry.add_to_hass(hass)
    second.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert [r["url"] for r in resources.items] == ["/local/other.js", f"{CARD}?v={VERSION}"]

    await hass.config_entries.async_remove(second.entry_id)
    assert len(resources.items) == 2
    await hass.config_entries.async_remove(config_entry.entry_id)
    assert [r["url"] for r in resources.items] == ["/local/other.js"]


async def test_card_version_updated(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """An older registered version is updated in place."""
    resources = _lovelace(hass, [{"id": "a", "url": f"{CARD}?v=2025.1.1"}])
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert resources.items == [{"id": "a", "url": f"{CARD}?v={VERSION}"}]


async def test_yaml_mode_left_alone(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """In YAML mode the resources aren't touched."""
    resources = _lovelace(hass, [])
    hass.data["lovelace"].resource_mode = "yaml"
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert resources.items == []
