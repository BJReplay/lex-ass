"""Constants for the Lexus Connected AU integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "lexus_au"
NAME = "Lexus Connected AU"
MANUFACTURER = "Lexus"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONF_DEVICE_ID = "device_id"
CONF_LEXUS_API_KEY = "lexus_api_key"
CONF_LEXUS_X_API_KEY = "lexus_x_api_key"
CONF_RECENT_TRIPS_LIMIT = "recent_trips_limit"
CONF_REFRESH_INTERVAL_SECONDS = "refresh_interval_seconds"
CONF_VIN = "vin"

DEFAULT_RECENT_TRIPS_LIMIT = 1
DEFAULT_REFRESH_INTERVAL_SECONDS = 300
MAX_RECENT_TRIPS_LIMIT = 20
MIN_REFRESH_INTERVAL_SECONDS = 60

COMMAND_CONFIRMATION_TIMEOUT_SECONDS = 20
COMMAND_CONFIRMATION_POLL_INTERVAL_SECONDS = 2

BACKGROUND_POLL_JITTER_RATIO = 0.15
BACKGROUND_POLL_MAX_BACKOFF_FACTOR = 8
