"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lutron_caseta_events.const import DOMAIN, LUTRON_DOMAIN


async def test_aborts_without_lutron_caseta(hass) -> None:
    """Without a Caséta entry there is nothing to wrap — abort with a hint."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_lutron_caseta"


async def test_creates_single_entry(hass) -> None:
    """Confirming the form creates the (only) entry."""
    MockConfigEntry(domain=LUTRON_DOMAIN).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lutron Caséta Events"
    assert result["data"] == {}

    # single_config_entry: a second flow refuses to start.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
