"""Switch platform for Compass Pool Heater."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CompassApi, CompassApiError, HeaterState
from .const import CONF_THERMOSTAT_KEY, DOMAIN
from .coordinator import CompassCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: CompassCoordinator = data["coordinator"]
    api: CompassApi = data["api"]
    key = entry.data[CONF_THERMOSTAT_KEY]

    async_add_entities(
        [
            CompassFieldSwitch(coordinator, api, entry, key, "vacation_hold", "Vacation Hold", "VH", "mdi:beach"),
            CompassFieldSwitch(coordinator, api, entry, key, "defrost_guard", "Defrost Guard", "DFG", "mdi:snowflake-alert"),
            CompassFieldSwitch(coordinator, api, entry, key, "defrost_lock", "Defrost Lock", "DFL", "mdi:snowflake-melt"),
        ],
    )


class CompassFieldSwitch(CoordinatorEntity[CompassCoordinator], SwitchEntity):
    """Toggle switch backed by a thermostatSetFields register."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CompassCoordinator, api: CompassApi,
        entry: ConfigEntry, key: str,
        switch_id: str, name: str, register: str, icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._key = key
        self._register = register
        self._attr_unique_id = f"compass_{key}_{switch_id}"
        self._attr_name = name
        self._attr_icon = icon

    @property
    def _state(self) -> HeaterState | None:
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._key)},
            "name": "Compass Pool Heater",
            "manufacturer": "Gulfstream / ICM Controls",
            "model": "Compass WiFi Heat Pump",
        }

    @property
    def is_on(self) -> bool | None:
        if self._state is None:
            return None
        return bool(self._state.raw.get(self._register, 0))

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._api.set_fields({self._register: 1})
            await self.coordinator.async_request_refresh()
        except CompassApiError as err:
            _LOGGER.error("Failed to turn on %s: %s", self._attr_name, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._api.set_fields({self._register: 0})
            await self.coordinator.async_request_refresh()
        except CompassApiError as err:
            _LOGGER.error("Failed to turn off %s: %s", self._attr_name, err)
