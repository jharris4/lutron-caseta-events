# Lutron Caséta Events

Event entities for **Lutron Caséta Pico remotes and keypad buttons** in Home Assistant.

Home Assistant's [Lutron Caséta](https://www.home-assistant.io/integrations/lutron_caseta/) integration announces button presses only as `lutron_caseta_button_event` on the event bus (plus device triggers in the automation editor) — it never creates [`event` entities](https://www.home-assistant.io/integrations/event/) for them. That means Pico buttons are invisible to entity pickers, dashboards, the logbook, and every integration that consumes event entities.

This integration fills that gap: **one `event` entity per button**, attached to the button's existing Caséta device, updated live from the integration's own bus events.

```text
Closet Pico            (the existing Caséta device)
├── event.closet_pico_on       → press / release
├── event.closet_pico_stop     → press / release
├── event.closet_pico_off      → press / release
├── event.closet_pico_raise    → press / release
└── event.closet_pico_lower    → press / release
```

- **Zero configuration.** Add the integration once; every button on every bridge is discovered automatically via the Caséta integration's device triggers.
- **Truthful metadata.** Each entity advertises exactly the actions the bridge offers that button (`press`/`release` everywhere; `multi_tap`/`long_press` only on hardware that supports them), so consumers can tell what a button can do.
- **All button devices.** Picos, shade remotes, and RA3/HomeWorks keypad buttons — anything the Caséta integration offers press triggers for.

## Installation

Via [HACS](https://hacs.xyz/), as a custom repository:

1. HACS → menu (⋮) → **Custom repositories**
2. Repository: `jharris4/lutron-caseta-events`, category: **Integration**
3. Install **Lutron Caséta Events**, restart Home Assistant
4. Settings → Devices & services → **Add integration** → *Lutron Caséta Events*

Requires Home Assistant 2025.8 or newer and the Lutron Caséta integration to
be set up first.

## Usage notes

- Entities live on each remote's existing device page (Settings → Devices → your Pico).
- Pairing new remotes later? **Reload this integration** (or restart HA) to create their entities.
- Entity state is the timestamp of the last event, with the action in the `event_type` attribute — standard `event` entity semantics. State starts `unknown` after a restart; stale pre-restart presses are never replayed.
- Automations can keep using the Caséta device triggers — the entities are additive, nothing is replaced.

## Why not upstream?

It should be. Other button ecosystems (Hue, deCONZ, Matter, Zigbee2MQTT) have all migrated to event entities; `lutron_caseta` hasn't yet, and [the feature request](https://community.home-assistant.io/t/lutron-caseta-integration-pico-remote-double-click-hold-events/521194) has been open since 2023. This integration exists to close the gap now and to serve as the working model for a core `event` platform in `lutron_caseta`. If/when core ships one, disable or remove this integration and re-pick the (new) core entities where you used these.

## Related projects

- [pico-link](https://github.com/smartqasa/pico-link) — a YAML-configured controller mapping Picos directly to lights/fans/covers. Different goal: it *acts on* presses; this integration *exposes* them.
- [lutron-caseta-pro](https://github.com/upsert/lutron-caseta-pro) — Telnet-based alternative to the core integration (Pro bridges only), exposing Picos as `sensor` entities.
- [MoLight](https://github.com/jharris4/molight) — virtual lighting automation whose Virtual Remote binds event-entity buttons (including these) to light actions.

## License

[GPL-3.0](LICENSE)
