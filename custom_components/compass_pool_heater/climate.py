"""Climate platform for Compass Pool Heater."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CompassApi, CompassApiError, HeaterState
from .const import CONF_THERMOSTAT_KEY, DOMAIN, MODE_OFF, MODE_POOL, MODE_SPA
from .coordinator import CompassCoordinator

_LOGGER = logging.getLogger(__name__)

PRESET_POOL = "Pool"
PRESET_SPA = "Spa"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Compass Pool Heater climate entity."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CompassPoolHeaterClimate(data["coordinator"], data["api"], entry)])


class CompassPoolHeaterClimate(CoordinatorEntity[CompassCoordinator], ClimateEntity):
    """Climate entity for the Compass WiFi pool heater."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_preset_modes = [PRESET_POOL, PRESET_SPA]
    _attr_min_temp = 50
    _attr_max_temp = 104

    def __init__(
        self,
        coordinator: CompassCoordinator,
        api: CompassApi,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"compass_{entry.data[CONF_THERMOSTAT_KEY]}"

    @property
    def _state(self) -> HeaterState | None:
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        name = self._state.name if self._state else "Compass Pool Heater"
        return {
            "identifiers": {(DOMAIN, self._entry.data[CONF_THERMOSTAT_KEY])},
            "name": name,
            "manufacturer": "Gulfstream / ICM Controls",
            "model": "Compass WiFi Heat Pump",
        }

    @property
    def icon(self) -> str:
        if self._state and self._state.mode == MODE_SPA:
            return "mdi:hot-tub"
        return "mdi:pool-thermometer"

    @property
    def hvac_mode(self) -> HVACMode:
        if self._state is None or self._state.mode == MODE_OFF:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._state is None or self._state.mode == MODE_OFF:
            return HVACAction.OFF
        if self._state.current_temp < self._active_setpoint:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str:
        if self._state and self._state.mode == MODE_SPA:
            return PRESET_SPA
        return PRESET_POOL

    @property
    def current_temperature(self) -> float | None:
        return self._state.current_temp if self._state else None

    @property
    def target_temperature(self) -> float | None:
        if self._state is None:
            return None
        return self._active_setpoint

    @property
    def _active_setpoint(self) -> int:
        if self._state is None:
            return 0
        if self._state.mode == MODE_SPA:
            return self._state.spa_setpoint
        return self._state.pool_setpoint

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._state is None:
            return {}
        attrs: dict[str, Any] = {
            "pool_setpoint": self._state.pool_setpoint,
            "spa_setpoint": self._state.spa_setpoint,
            "heater_mode_raw": self._state.mode,
            "fault_code": self._state.fault_code,
            "thermostat_key": self._entry.data[CONF_THERMOSTAT_KEY],
            "last_online": self._state.last_online,
            "deadband": self._state.deadband,
            "calibration": self._state.calibration,
            "vacation_hold": bool(self._state.vacation_hold),
        }
        if self._state.fault_code:
            attrs["fault_active"] = True
        return attrs

    async def _send_command(
        self,
        pool_sp: int | None = None,
        spa_sp: int | None = None,
        mode: int | None = None,
    ) -> None:
        if self._state is None:
            _LOGGER.warning("Cannot send command: state unknown")
            return

        try:
            await self._api.set_state(
                pool_setpoint=pool_sp if pool_sp is not None else self._state.pool_setpoint,
                spa_setpoint=spa_sp if spa_sp is not None else self._state.spa_setpoint,
                mode=mode if mode is not None else self._state.mode,
            )
        except CompassApiError as err:
            _LOGGER.error("Failed to send command: %s", err)
            return

        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send_command(mode=MODE_OFF)
        elif hvac_mode == HVACMode.HEAT:
            current_preset = self.preset_mode
            target_mode = MODE_SPA if current_preset == PRESET_SPA else MODE_POOL
            await self._send_command(mode=target_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        temp = int(temp)

        if self._state and self._state.mode == MODE_SPA:
            await self._send_command(spa_sp=temp)
        else:
            await self._send_command(pool_sp=temp)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_SPA:
            await self._send_command(mode=MODE_SPA)
        elif preset_mode == PRESET_POOL:
            await self._send_command(mode=MODE_POOL)
