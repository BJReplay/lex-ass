"""Home Assistant setup for Lexus Connected AU."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .api import LexusAUClient
from .const import (
    CONF_DEVICE_ID,
    CONF_LEXUS_API_KEY,
    CONF_LEXUS_X_API_KEY,
    CONF_RECENT_TRIPS_LIMIT,
    CONF_VIN,
    DEFAULT_RECENT_TRIPS_LIMIT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import LexusAUCoordinator

LexusAUConfigEntry = ConfigEntry


async def _async_reload_entry(hass: HomeAssistant, entry: LexusAUConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: LexusAUConfigEntry) -> bool:
    """Set up Lexus Connected AU from a config entry."""
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    client = LexusAUClient(
        username=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        vin=entry.data[CONF_VIN],
        device_id=entry.data[CONF_DEVICE_ID],
        api_key=entry.options.get(CONF_LEXUS_API_KEY, entry.data[CONF_LEXUS_API_KEY]),
        x_api_key=entry.options.get(
            CONF_LEXUS_X_API_KEY, entry.data[CONF_LEXUS_X_API_KEY]
        ),
        recent_trips_limit=entry.options.get(
            CONF_RECENT_TRIPS_LIMIT, DEFAULT_RECENT_TRIPS_LIMIT
        ),
    )
    coordinator = LexusAUCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.async_close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LexusAUConfigEntry) -> bool:
    """Unload a Lexus Connected AU config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: LexusAUCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    await coordinator.client.async_close()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok
