"""Constants for the Lutron Caséta Events integration."""

DOMAIN = "lutron_caseta_events"

# The integration whose bus events we re-expose as event entities.
LUTRON_DOMAIN = "lutron_caseta"
LUTRON_BUTTON_EVENT = "lutron_caseta_button_event"

# Payload fields of lutron_caseta_button_event (its public trigger contract:
# the integration's own device triggers match on exactly these).
ATTR_DEVICE_ID = "device_id"
ATTR_BUTTON_TYPE = "button_type"
ATTR_ACTION = "action"

# Canonical ordering for an entity's advertised event_types. The actions a
# button offers are read from its device triggers (press/release everywhere;
# multi_tap and long_press only where the bridge supports them) — this just
# keeps the advertised list stable and readable.
EVENT_TYPE_ORDER = ("press", "release", "multi_tap", "long_press")
