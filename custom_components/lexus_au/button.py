"""Button entities for Lexus Connected AU."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity


@dataclass(frozen=True, kw_only=True)
class LexusAUButtonDescription(ButtonEntityDescription):
    """Description of a Lexus AU action button."""

    method_name: str


BUTTONS: tuple[LexusAUButtonDescription, ...] = (
    LexusAUButtonDescription(
        key="refresh_vehicle",
        translation_key="refresh_vehicle",
        icon="mdi:refresh",
        method_name="async_refresh_vehicle",
    ),
    LexusAUButtonDescription(
        key="refresh_electric_status",
        translation_key="refresh_electric_status",
        icon="mdi:battery-sync",
        method_name="async_refresh_electric_realtime_status",
    ),
    LexusAUButtonDescription(
        key="refresh_recent_trips",
        translation_key="refresh_recent_trips",
        icon="mdi:map-refresh",
        method_name="async_refresh_recent_trips",
    ),
    LexusAUButtonDescription(
        key="lock_doors",
        translation_key="lock_doors",
        icon="mdi:lock",
        method_name="async_lock_doors",
    ),
    LexusAUButtonDescription(
        key="unlock_doors",
        translation_key="unlock_doors",
        icon="mdi:lock-open-variant",
        method_name="async_unlock_doors",
    ),
    LexusAUButtonDescription(
        key="flash_hazards",
        translation_key="flash_hazards",
        icon="mdi:car-light-alert",
        method_name="async_flash_hazards",
    ),
    LexusAUButtonDescription(
        key="engine_start",
        translation_key="engine_start",
        icon="mdi:engine-outline",
        method_name="async_engine_start",
    ),
    LexusAUButtonDescription(
        key="engine_stop",
        translation_key="engine_stop",
        icon="mdi:engine-off-outline",
        method_name="async_engine_stop",
    ),
    LexusAUButtonDescription(
        key="lock_boot_trial",
        translation_key="lock_boot_trial",
        icon="mdi:car-back",
        method_name="async_lock_boot_trial",
    ),
    LexusAUButtonDescription(
        key="unlock_boot_trial",
        translation_key="unlock_boot_trial",
        icon="mdi:car-back",
        method_name="async_unlock_boot_trial",
    ),
    LexusAUButtonDescription(
        key="flash_headlights_trial",
        translation_key="flash_headlights_trial",
        icon="mdi:car-light-high",
        method_name="async_flash_headlights_trial",
    ),
    LexusAUButtonDescription(
        key="sound_horn_trial",
        translation_key="sound_horn_trial",
        icon="mdi:bullhorn",
        method_name="async_sound_horn_trial",
    ),
    LexusAUButtonDescription(
        key="buzzer_warning_trial",
        translation_key="buzzer_warning_trial",
        icon="mdi:volume-high",
        method_name="async_buzzer_warning_trial",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(LexusAUButton(coordinator, description) for description in BUTTONS)


class LexusAUButton(LexusAUEntity, ButtonEntity):
    """A button that triggers a Lexus AU remote action."""

    entity_description: LexusAUButtonDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: LexusAUButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Execute the configured coordinator action."""
        await getattr(self.coordinator, self.entity_description.method_name)()
