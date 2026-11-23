"""Tests for setup, entities, commands and migration."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.playtopro.const import CONF_SERIAL_NUMBER, DOMAIN
from homeassistant.config_entries import ConfigEntryState, SOURCE_REAUTH
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import SERIAL, FakeLichen


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, domain: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}")
    assert entity_id is not None, key
    return entity_id


async def test_setup_creates_entities(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """All entities are created with state from the first refresh."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(er.async_get(hass), config_entry.entry_id)
    assert len(entities) == 1 + 8 + 2 + 8 * 4

    assert hass.states.get(_entity_id(hass, "binary_sensor", "zone_00")).state == STATE_ON
    assert hass.states.get(_entity_id(hass, "binary_sensor", "zone_01")).state == STATE_OFF
    assert hass.states.get(_entity_id(hass, "sensor", "eco_mode_factor")).state == "60"
    assert hass.states.get(_entity_id(hass, "switch", "auto_mode")).state == STATE_ON
    assert hass.states.get(_entity_id(hass, "switch", "zone_manual_mode_00")).state == STATE_ON

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, str(SERIAL))})
    assert device is not None
    assert device.serial_number == str(SERIAL)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_unreachable(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """An unreachable device retries setup later."""
    lichen.reachable = False
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_switch_command_refreshes(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """A command is sent and the new state shows straight away."""
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "switch", "zone_manual_mode_03")
    assert hass.states.get(entity_id).state == STATE_OFF

    await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id}, blocking=True)
    assert lichen.manual & 0b1000
    assert hass.states.get(entity_id).state == STATE_ON


async def test_switch_command_errors(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Refused or failed commands raise HomeAssistantError."""
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "switch", "eco_mode")

    lichen.refuse_commands = True
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id}, blocking=True)
    assert err.value.translation_key == "command_refused"

    lichen.reachable = False
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id}, blocking=True)
    assert err.value.translation_key == "command_failed"


async def test_unavailable_then_recovers(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Entities go unavailable while the device is unreachable."""
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "binary_sensor", "zone_00")

    lichen.reachable = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    lichen.reachable = True
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=8))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON


async def test_single_rejection_is_retried(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """One dropped request doesn't start reauth."""
    lichen.reject_count = 1
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert not list(hass.config_entries.flow.async_progress_by_handler(DOMAIN))


async def test_rejected_key_starts_reauth(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """A key the device keeps rejecting starts reauth."""
    lichen.key = 1234
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = list(hass.config_entries.flow.async_progress_by_handler(DOMAIN))
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_migrate_1_1(
    hass: HomeAssistant, lichen: FakeLichen, config_entry: MockConfigEntry
) -> None:
    """Old int device identifiers and sensor-platform zone entities are migrated."""
    old = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(SERIAL),
        version=1,
        minor_version=1,
        data=dict(config_entry.data),
    )
    old.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=old.entry_id,
        identifiers={(DOMAIN, SERIAL)},  # type: ignore[arg-type]
    )
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor", DOMAIN, f"{SERIAL}_zone_00", config_entry=old, device_id=device.id
    )

    assert await hass.config_entries.async_setup(old.entry_id)
    await hass.async_block_till_done()

    assert old.minor_version == 2
    migrated = device_registry.async_get(device.id)
    assert migrated.identifiers == {(DOMAIN, str(SERIAL))}
    assert len(dr.async_entries_for_config_entry(device_registry, old.entry_id)) == 1
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_zone_00") is None
    zone = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{SERIAL}_zone_00")
    assert entity_registry.async_get(zone).device_id == device.id
    assert old.data[CONF_SERIAL_NUMBER] == SERIAL
