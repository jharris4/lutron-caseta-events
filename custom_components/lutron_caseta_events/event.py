"""Event entities for Lutron Caséta Pico and keypad buttons.

One entity per physical button. Buttons are enumerated through Home
Assistant's device-automation API: lutron_caseta offers a device trigger per
(button, action) pair, and those triggers' subtype/type vocabulary is exactly
what its lutron_caseta_button_event bus payloads carry — so the entities'
advertised event_types mirror what the bridge can actually report (press and
release everywhere; multi_tap and long_press only where supported).

Each entity links directly to the button's existing Caséta device, so buttons
appear on the Pico's own device page without making this helper integration a
co-owner of that device.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.device_automation import (
    DeviceAutomationType,
    async_get_device_automations,
)
from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, helper_integration

from .const import (
    ATTR_ACTION,
    ATTR_BUTTON_TYPE,
    ATTR_DEVICE_ID,
    EVENT_TYPE_ORDER,
    LUTRON_BUTTON_EVENT,
    LUTRON_DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Enumerate every Caséta button and create its event entity."""
    dev_registry = dr.async_get(hass)
    # Look devices up per Caséta entry: using registry.devices as a mapping is
    # deprecated from Home Assistant 2026.9, while iterating it only yields
    # entries (rather than ids) on the newest versions.
    devices = {
        device.id: device
        for lutron_entry in hass.config_entries.async_entries(LUTRON_DOMAIN)
        for device in dr.async_entries_for_config_entry(
            dev_registry, lutron_entry.entry_id
        )
        if _is_lutron_device(device)
    }
    if not devices:
        _LOGGER.warning(
            "No Lutron Caséta devices found in the device registry; "
            "no button entities created"
        )
        return

    _remove_helper_device_links(hass, entry.entry_id, devices)
    # The pre-2026.8 cleanup updates immutable DeviceEntry instances in place
    # in the registry, so refresh the objects before linking entities to them.
    devices = {
        device_id: device
        for device_id in devices
        if (device := dev_registry.async_get(device_id)) is not None
    }

    triggers_by_device = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, list(devices)
    )
    entities: list[LutronButtonEventEntity] = []
    for device_id, triggers in triggers_by_device.items():
        # subtype (button) -> the actions its triggers offer
        actions_by_button: dict[str, set[str]] = {}
        for trigger in triggers:
            if trigger.get("domain") != LUTRON_DOMAIN:
                continue
            actions_by_button.setdefault(str(trigger["subtype"]), set()).add(
                str(trigger["type"])
            )
        device = devices[device_id]
        entities.extend(
            LutronButtonEventEntity(device, button_type, actions)
            for button_type, actions in actions_by_button.items()
        )
    if not entities:
        _LOGGER.warning(
            "Found %d Lutron Caséta devices but none offered button triggers; "
            "no button entities created",
            len(devices),
        )
    else:
        _LOGGER.debug(
            "Created %d button event entities across %d Caséta devices",
            len(entities),
            len(devices),
        )
    async_add_entities(entities)


def _is_lutron_device(device: dr.DeviceEntry) -> bool:
    """Return whether a Caséta entry's device carries a Caséta identifier."""
    return any(identifier[0] == LUTRON_DOMAIN for identifier in device.identifiers)


def _remove_helper_device_links(
    hass: HomeAssistant,
    helper_config_entry_id: str,
    devices: dict[str, dr.DeviceEntry],
) -> None:
    """Remove device ownership left by versions before 0.1.2.

    The helper was renamed for Home Assistant 2026.8. Feature detection keeps
    this release compatible with Home Assistant 2025.8 through 2026.7 without
    using the deprecated alias on 2026.8 and later.
    """
    remove_helper_devices = getattr(
        helper_integration, "async_remove_helper_devices", None
    )
    for device_id in devices:
        if remove_helper_devices is not None:
            remove_helper_devices(
                hass,
                helper_config_entry_id=helper_config_entry_id,
                source_device_id=device_id,
            )
        else:
            helper_integration.async_remove_helper_config_entry_from_source_device(
                hass,
                helper_config_entry_id=helper_config_entry_id,
                source_device_id=device_id,
            )


def _ordered_event_types(actions: set[str]) -> list[str]:
    """Order a button's actions canonically (unknown ones last, sorted)."""
    known = [t for t in EVENT_TYPE_ORDER if t in actions]
    return known + sorted(actions - set(EVENT_TYPE_ORDER))


class LutronButtonEventEntity(EventEntity):
    """A single Caséta button, updated from the integration's bus events."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = EventDeviceClass.BUTTON

    def __init__(
        self, device: dr.DeviceEntry, button_type: str, actions: set[str]
    ) -> None:
        """Wrap one (device, button) pair."""
        self._device_id = device.id
        self._button_type = button_type
        serial = next(i[1] for i in device.identifiers if i[0] == LUTRON_DOMAIN)
        self._attr_unique_id = f"{serial}_{button_type}"
        self._attr_name = button_type.replace("_", " ").capitalize()
        self._attr_event_types = _ordered_event_types(actions)
        # Link to the source integration's device without adding this helper's
        # config entry to it. Device identifiers are scoped per config entry
        # starting in Home Assistant 2026.8 and must not be copied here.
        self.device_entry = device

    async def async_added_to_hass(self) -> None:
        """Subscribe to the Caséta integration's button announcements."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(LUTRON_BUTTON_EVENT, self._handle_button_event)
        )

    @callback
    def _handle_button_event(self, event: Event) -> None:
        """Record an action on this button; everything else is not ours."""
        data = event.data
        if (
            data.get(ATTR_DEVICE_ID) != self._device_id
            or data.get(ATTR_BUTTON_TYPE) != self._button_type
        ):
            return
        action = data.get(ATTR_ACTION)
        if action not in self.event_types:
            return
        self._trigger_event(action)
        self.async_write_ha_state()
