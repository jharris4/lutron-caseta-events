"""Shared fixtures for Lutron Caséta Events tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.lutron_caseta_events.const import DOMAIN, LUTRON_DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in tests."""
    return


class _LutronFlow(ConfigFlow):
    """Placeholder flow so the mocked Caséta entry can be set up."""


def mock_lutron_integration(hass: HomeAssistant) -> None:
    """Stand in for lutron_caseta, whose real module needs pylutron_caseta."""
    mock_integration(
        hass,
        MockModule(
            LUTRON_DOMAIN,
            async_setup_entry=AsyncMock(return_value=True),
            async_unload_entry=AsyncMock(return_value=True),
        ),
    )
    mock_platform(hass, f"{LUTRON_DOMAIN}.config_flow", None)


@pytest.fixture
async def lutron_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A Caséta config entry, genuinely set up (against the mock module)."""
    mock_lutron_integration(hass)
    entry = MockConfigEntry(domain=LUTRON_DOMAIN)
    entry.add_to_hass(hass)
    with mock_config_flow(LUTRON_DOMAIN, _LutronFlow):
        assert await hass.config_entries.async_setup(entry.entry_id)
    return entry


@pytest.fixture
def pico_device(hass: HomeAssistant, lutron_entry: MockConfigEntry) -> dr.DeviceEntry:
    """A Caséta Pico device registered against the Caséta entry."""
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=lutron_entry.entry_id,
        identifiers={(LUTRON_DOMAIN, "68551522")},
        name="Closet Pico",
    )


def pico_triggers(device_id: str) -> list[dict[str, str]]:
    """The press/release triggers of a 3-button Pico, plus multi_tap on one."""
    base = {"platform": "device", "domain": LUTRON_DOMAIN, "device_id": device_id}
    triggers = [
        {**base, "type": action, "subtype": subtype}
        for subtype in ("on", "stop", "off")
        for action in ("press", "release")
    ]
    triggers.append({**base, "type": "multi_tap", "subtype": "on"})
    return triggers


async def setup_events_entry(
    hass: HomeAssistant, triggers_by_device: dict[str, list[dict[str, str]]]
) -> MockConfigEntry:
    """Set up a Lutron Caséta Events entry against patched device triggers."""
    entry = MockConfigEntry(domain=DOMAIN, title="Lutron Caséta Events")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.lutron_caseta_events.event.async_get_device_automations",
        return_value=triggers_by_device,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry
