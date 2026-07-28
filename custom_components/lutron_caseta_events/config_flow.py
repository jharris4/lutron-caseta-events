"""Config flow for Lutron Caséta Events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN, LUTRON_DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult


class LutronCasetaEventsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance flow: confirm, then enumerate everything automatically.

    There is nothing to configure — every button the Caséta bridge knows
    gets an entity. Duplicate instances are prevented by the manifest's
    single_config_entry flag.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm creation, guarding against a missing Caséta integration."""
        if not self.hass.config_entries.async_entries(LUTRON_DOMAIN):
            return self.async_abort(reason="no_lutron_caseta")
        if user_input is not None:
            return self.async_create_entry(title="Lutron Caséta Events", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
