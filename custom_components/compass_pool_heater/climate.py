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
from .const import CONF_THERMOSTAT_KEY, DOMAIN, FAULT_CODES, MODE_OFF, MODE_POOL, MODE_SPA
from .coordinator import CompassCoordinator

_LOGGER = logging.getLogger(__name__)

PRESET_POOL = "Pool"
PRESET_SPA = "Spa"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
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
        self._key = entry.data[CONF_THERMOSTAT_KEY]
        self._attr_unique_id = f"compass_{self._key}"

    @property
    def _state(self) -> HeaterState | None:
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        name = self._state.name if self._state else "Compass Pool Heater"
        return {
            "identifiers": {(DOMAIN, self._key)},
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
        sp = self._active_setpoint
        if sp == 0:
            return HVACAction.OFF
        if self._state.current_temp < sp:
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
        sp = self._active_setpoint
        return sp if sp > 0 else None

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
        s = self._state
        pool_display = f"{s.pool_setpoint}°F" if s.pool_setpoint > 0 else "Off"
        spa_display = f"{s.spa_setpoint}°F" if s.spa_setpoint > 0 else "Off"
        fault_text = FAULT_CODES.get(s.fault_code, f"Code {s.fault_code}")
        return {
            "pool_setpoint": pool_display,
            "spa_setpoint": spa_display,
            "water_temp": s.current_temp,
            "coil_temp": s.coil_temp,
            "fault": fault_text,
            "fault_active": s.fault_code != 0,
            "last_online": s.last_online,
            "thermostat_key": self._key,
        }

    async def _send_command(
        self,
        pool_sp: int | None = None,
        spa_sp: int | None = None,
        mode: int | None = None,
    ) -> None:
        if self._state is None:
            _LOGGER.warning("Cannot send command: state unknown")
            return

        final_pool = pool_sp if pool_sp is not None else self._state.pool_setpoint
        final_spa = spa_sp if spa_sp is not None else self._state.spa_setpoint
        final_mode = mode if mode is not None else self._state.mode

        try:
            await self._api.set_state(
                pool_setpoint=final_pool,
                spa_setpoint=final_spa,
                mode=final_mode,
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
        temp = int(max(self._attr_min_temp, min(self._attr_max_temp, temp)))

        if self._state and self._state.mode == MODE_SPA:
            await self._send_command(spa_sp=temp)
        else:
            await self._send_command(pool_sp=temp)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_SPA:
            await self._send_command(mode=MODE_SPA)
        elif preset_mode == PRESET_POOL:
            await self._send_command(mode=MODE_POOL)
