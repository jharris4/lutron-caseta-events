"""Tests for the button event entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lutron_caseta_events.const import (
    DOMAIN,
    LUTRON_BUTTON_EVENT,
    LUTRON_DOMAIN,
)
from tests.conftest import mock_lutron_integration, pico_triggers, setup_events_entry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _press(hass: HomeAssistant, device_id: str, button_type: str, action: str) -> None:
    """Fire a lutron_caseta_button_event exactly as the integration does."""
    hass.bus.async_fire(
        LUTRON_BUTTON_EVENT,
        {
            "serial": 68551522,
            "type": "Pico3Button",
            "button_number": 2,
            "leap_button_number": 0,
            "device_name": "Closet Pico",
            "device_id": device_id,
            "area_name": "Closet",
            "button_type": button_type,
            "action": action,
        },
    )


@pytest.mark.asyncio
async def test_entities_created_per_button(hass, pico_device) -> None:
    """One entity per button, on the Pico's device, advertising its actions."""
    await setup_events_entry(hass, {pico_device.id: pico_triggers(pico_device.id)})

    for button in ("on", "stop", "off"):
        state = hass.states.get(f"event.closet_pico_{button}")
        assert state is not None, button
        assert state.state == "unknown"
    # The multi_tap trigger surfaces only on the button that offers it.
    on_state = hass.states.get("event.closet_pico_on")
    assert on_state.attributes["event_types"] == ["press", "release", "multi_tap"]
    off_state = hass.states.get("event.closet_pico_off")
    assert off_state.attributes["event_types"] == ["press", "release"]

    # Attached to the existing Caséta device, with a serial-derived unique id.
    registry = er.async_get(hass)
    entity = registry.async_get("event.closet_pico_on")
    assert entity.device_id == pico_device.id
    assert entity.unique_id == "68551522_on"


@pytest.mark.asyncio
async def test_bus_event_updates_entity(hass, pico_device) -> None:
    """A button's bus event lands on its entity; everything else doesn't."""
    await setup_events_entry(hass, {pico_device.id: pico_triggers(pico_device.id)})

    _press(hass, pico_device.id, "on", "press")
    await hass.async_block_till_done()
    state = hass.states.get("event.closet_pico_on")
    assert state.state != "unknown"
    assert state.attributes["event_type"] == "press"
    assert hass.states.get("event.closet_pico_off").state == "unknown"

    _press(hass, pico_device.id, "on", "multi_tap")
    await hass.async_block_till_done()
    assert (
        hass.states.get("event.closet_pico_on").attributes["event_type"] == "multi_tap"
    )

    # Unknown actions and other devices' presses are ignored.
    before = hass.states.get("event.closet_pico_on")
    _press(hass, pico_device.id, "on", "weird_action")
    _press(hass, "some_other_device", "on", "press")
    await hass.async_block_till_done()
    assert hass.states.get("event.closet_pico_on") == before


@pytest.mark.asyncio
async def test_unload_stops_listening(hass, pico_device) -> None:
    """After unload the entities go unavailable and bus events go nowhere."""
    entry = await setup_events_entry(
        hass, {pico_device.id: pico_triggers(pico_device.id)}
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("event.closet_pico_on").state == "unavailable"

    _press(hass, pico_device.id, "on", "press")
    await hass.async_block_till_done()
    assert hass.states.get("event.closet_pico_on").state == "unavailable"


@pytest.mark.asyncio
async def test_retries_until_lutron_loaded(hass) -> None:
    """With Caséta configured but not yet set up, setup retries instead of
    creating zero entities."""
    mock_lutron_integration(hass)
    MockConfigEntry(domain=LUTRON_DOMAIN).add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_no_lutron_devices_creates_nothing(hass, lutron_entry) -> None:
    """A loaded Caséta entry with no button devices yields no entities."""
    await setup_events_entry(hass, {})
    assert not [s for s in hass.states.async_all() if s.entity_id.startswith("event.")]


@pytest.mark.asyncio
async def test_non_lutron_devices_ignored(hass, pico_device) -> None:
    """Devices from other integrations never reach trigger enumeration."""
    other = MockConfigEntry(domain="hue")
    other.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id,
        identifiers={("hue", "abc")},
        name="Hue Dimmer",
    )
    await setup_events_entry(hass, {pico_device.id: pico_triggers(pico_device.id)})
    assert hass.states.get("event.closet_pico_on") is not None
    assert not [
        s for s in hass.states.async_all() if s.entity_id.startswith("event.hue")
    ]
