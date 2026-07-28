"""Event entities for Lutron Caséta Pico and keypad buttons.

One entity per physical button. Buttons are enumerated through Home
Assistant's device-automation API: lutron_caseta offers a device trigger per
(button, action) pair, and those triggers' subtype/type vocabulary is exactly
what its lutron_caseta_button_event bus payloads carry — so the entities'
advertised event_types mirror what the bridge can actually report (press and
release everywhere; multi_tap and long_press only where supported).

Each entity attaches to the button's existing Caséta device by declaring the
same registry identifiers, so buttons appear on the Pico's own device page.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.device_automation import (
    DeviceAutomationType,
    async_get_device_automations,
)
from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,  # noqa: ARG001 — fixed platform signature
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Enumerate every Caséta button and create its event entity."""
    dev_registry = dr.async_get(hass)
    devices = {
        device.id: device
        for device in dev_registry.devices.values()
        if any(domain == LUTRON_DOMAIN for domain, _ in device.identifiers)
    }
    if not devices:
        return

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
    async_add_entities(entities)


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
        serial = next(v for domain, v in device.identifiers if domain == LUTRON_DOMAIN)
        self._attr_unique_id = f"{serial}_{button_type}"
        self._attr_name = button_type.replace("_", " ").capitalize()
        self._attr_event_types = _ordered_event_types(actions)
        # The same identifiers as the existing Caséta device, so the entity
        # lands on the Pico/keypad's own device page instead of a new device.
        self._attr_device_info = DeviceInfo(identifiers=set(device.identifiers))

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
