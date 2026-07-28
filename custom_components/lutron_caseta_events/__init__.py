"""Lutron Caséta Events — event entities for Pico and keypad buttons.

Home Assistant's lutron_caseta integration announces button presses only as
lutron_caseta_button_event on the event bus (plus device triggers); it never
creates `event` entities for them. This integration fills that gap: one
event entity per button, attached to the button's existing Caséta device,
so presses become visible to entity pickers, dashboards, the logbook, and
any integration that consumes event entities.

It should become obsolete the day lutron_caseta grows an event platform of
its own — see the README.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import LUTRON_DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.EVENT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the single Lutron Caséta Events entry.

    Buttons are enumerated from the lutron_caseta integration's device
    triggers, which only exist once a bridge is connected — so if Caséta
    entries exist but none has finished setting up yet (HA still starting,
    bridge briefly unreachable), retry rather than creating zero entities.
    """
    lutron_entries = hass.config_entries.async_entries(LUTRON_DOMAIN)
    if lutron_entries and not any(
        e.state is ConfigEntryState.LOADED for e in lutron_entries
    ):
        msg = "Waiting for Lutron Caséta to finish setting up"
        raise ConfigEntryNotReady(msg)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
