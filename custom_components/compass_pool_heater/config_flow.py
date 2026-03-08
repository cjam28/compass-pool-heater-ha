"""Config flow for Compass Pool Heater."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CompassApi, CompassAuthError, CompassApiError, DeviceInfo
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_THERMOSTAT_KEY,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class CompassPoolHeaterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Compass Pool Heater."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str = ""
        self._devices: list[DeviceInfo] = []
        self._email: str = ""
        self._password: str = ""
        self._scan_interval: int = DEFAULT_SCAN_INTERVAL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle login step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            self._scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            session = async_get_clientsession(self.hass)
            try:
                self._token, self._devices = await CompassApi.login(
                    self._email, self._password, session
                )
            except CompassAuthError:
                errors["base"] = "invalid_auth"
            except CompassApiError:
                errors["base"] = "cannot_connect"
            else:
                if len(self._devices) == 1:
                    device = self._devices[0]
                    await self.async_set_unique_id(device.unique_key)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"{device.name} ({device.unique_key})",
                        data={
                            CONF_EMAIL: self._email,
                            CONF_PASSWORD: self._password,
                            CONF_THERMOSTAT_KEY: device.unique_key,
                            CONF_TOKEN: self._token,
                            CONF_SCAN_INTERVAL: self._scan_interval,
                        },
                    )
                elif len(self._devices) > 1:
                    return await self.async_step_device()
                else:
                    errors["base"] = "no_devices"

        return self.async_show_form(
            step_id="user",
            data_schema=LOGIN_SCHEMA,
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection for multi-device accounts."""
        if user_input is not None:
            key = user_input[CONF_THERMOSTAT_KEY]
            device = next((d for d in self._devices if d.unique_key == key), None)
            if device:
                await self.async_set_unique_id(key)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{device.name} ({key})",
                    data={
                        CONF_EMAIL: self._email,
                        CONF_PASSWORD: self._password,
                        CONF_THERMOSTAT_KEY: key,
                        CONF_TOKEN: self._token,
                        CONF_SCAN_INTERVAL: self._scan_interval,
                    },
                )

        device_options = {
            d.unique_key: f"{d.name} - {d.description} ({d.unique_key})"
            for d in self._devices
        }

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {vol.Required(CONF_THERMOSTAT_KEY): vol.In(device_options)}
            ),
        )
