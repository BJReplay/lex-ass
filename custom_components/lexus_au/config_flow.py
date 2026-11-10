"""Config flow for Lexus Connected AU."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .api import LexusAUAuthError, LexusAUClient, LexusAURequestError
from .api.client import generate_device_id
from .const import (
    CONF_DEVICE_ID,
    CONF_LEXUS_API_KEY,
    CONF_LEXUS_X_API_KEY,
    CONF_RECENT_TRIPS_LIMIT,
    CONF_REFRESH_INTERVAL_SECONDS,
    CONF_VIN,
    DEFAULT_RECENT_TRIPS_LIMIT,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    DOMAIN,
    MAX_RECENT_TRIPS_LIMIT,
    MIN_REFRESH_INTERVAL_SECONDS,
)

LOGGER = logging.getLogger(__name__)


class LexusAUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Lexus Connected AU config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None
        self._default_email = ""
        self._default_api_key = ""
        self._default_vin = ""
        self._default_x_api_key = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle the initial setup flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_email = user_input[CONF_EMAIL].strip().lower()
            normalized_vin = user_input[CONF_VIN].strip().upper()
            device_id = generate_device_id()

            client = LexusAUClient(
                username=normalized_email,
                password=user_input[CONF_PASSWORD],
                vin=normalized_vin,
                device_id=device_id,
                api_key=user_input[CONF_LEXUS_API_KEY].strip(),
                x_api_key=user_input[CONF_LEXUS_X_API_KEY].strip(),
            )
            try:
                await client.async_test_connection()
            except LexusAUAuthError:
                errors["base"] = "invalid_auth"
            except (LexusAURequestError, httpx.HTTPError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected Lexus AU config-flow failure")
                errors["base"] = "unknown"
            else:
                unique_id = f"{normalized_email}::{normalized_vin}"
                await self.async_set_unique_id(unique_id)

                if not self._reauth_entry:
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Lexus {normalized_vin[-6:]}",
                        data={
                            CONF_EMAIL: normalized_email,
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_VIN: normalized_vin,
                            CONF_DEVICE_ID: device_id,
                            CONF_LEXUS_API_KEY: user_input[CONF_LEXUS_API_KEY].strip(),
                            CONF_LEXUS_X_API_KEY: user_input[CONF_LEXUS_X_API_KEY].strip(),
                        },
                        options={
                            CONF_REFRESH_INTERVAL_SECONDS: DEFAULT_REFRESH_INTERVAL_SECONDS,
                            CONF_RECENT_TRIPS_LIMIT: DEFAULT_RECENT_TRIPS_LIMIT,
                        },
                    )

                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_EMAIL: normalized_email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VIN: normalized_vin,
                        CONF_LEXUS_API_KEY: user_input[CONF_LEXUS_API_KEY].strip(),
                        CONF_LEXUS_X_API_KEY: user_input[CONF_LEXUS_X_API_KEY].strip(),
                    },
                    unique_id=unique_id,
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            finally:
                await client.async_close()

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL, default=self._default_email): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_VIN, default=self._default_vin): str,
                vol.Required(
                    CONF_LEXUS_API_KEY, default=self._default_api_key
                ): str,
                vol.Required(
                    CONF_LEXUS_X_API_KEY, default=self._default_x_api_key
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> Any:
        """Handle a reauthentication flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._default_email = entry_data[CONF_EMAIL]
        self._default_api_key = entry_data.get(CONF_LEXUS_API_KEY, "")
        self._default_vin = entry_data[CONF_VIN]
        self._default_x_api_key = entry_data.get(CONF_LEXUS_X_API_KEY, "")
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "LexusAUOptionsFlow":
        """Return the options flow."""
        return LexusAUOptionsFlow(config_entry)


class LexusAUOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Lexus Connected AU."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_REFRESH_INTERVAL_SECONDS,
                    default=self._config_entry.options.get(
                        CONF_REFRESH_INTERVAL_SECONDS,
                        DEFAULT_REFRESH_INTERVAL_SECONDS,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_REFRESH_INTERVAL_SECONDS),
                ),
                vol.Required(
                    CONF_RECENT_TRIPS_LIMIT,
                    default=self._config_entry.options.get(
                        CONF_RECENT_TRIPS_LIMIT, DEFAULT_RECENT_TRIPS_LIMIT
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=MAX_RECENT_TRIPS_LIMIT),
                ),
                vol.Required(
                    CONF_LEXUS_API_KEY,
                    default=self._config_entry.options.get(
                        CONF_LEXUS_API_KEY,
                        self._config_entry.data.get(CONF_LEXUS_API_KEY, ""),
                    ),
                ): str,
                vol.Required(
                    CONF_LEXUS_X_API_KEY,
                    default=self._config_entry.options.get(
                        CONF_LEXUS_X_API_KEY,
                        self._config_entry.data.get(CONF_LEXUS_X_API_KEY, ""),
                    ),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
