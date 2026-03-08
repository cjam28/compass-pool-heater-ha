"""Number platform for Compass Pool Heater configurable settings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CompassApi, HeaterState
from .const import CONF_THERMOSTAT_KEY, DOMAIN
from .coordinator import CompassCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: CompassCoordinator = data["coordinator"]
    api: CompassApi = data["api"]
    key = entry.data[CONF_THERMOSTAT_KEY]

    async_add_entities([
        CompassPoolHeatCoolDeadband(coordinator, api, entry, key),
        CompassDefrostEnd(coordinator, api, entry, key),
        CompassCalibration(coordinator, api, entry, key),
        CompassSpaTimerHours(coordinator, api, entry, key),
        CompassSpaTimerMinutes(coordinator, api, entry, key),
    ])


class _Base(CoordinatorEntity[CompassCoordinator], NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CompassCoordinator, api: CompassApi, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._api = api
        self._key = key

    @property
    def _heater(self) -> HeaterState | None:
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._key)},
            "name": self._heater.name if self._heater else "Compass Pool Heater",
            "manufacturer": "Gulfstream / ICM Controls",
            "model": "Compass WiFi Heat Pump",
        }


class CompassPoolHeatCoolDeadband(_Base):
    """#13 Pool Heat/Cool Deadband (DFU, range 2-8°F)."""

    _attr_native_min_value = 2
    _attr_native_max_value = 8
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator, api, entry, key)
        self._attr_unique_id = f"compass_{key}_pool_heat_cool_deadband"
        self._attr_name = "Pool Heat/Cool Deadband"

    @property
    def native_value(self) -> float | None:
        return self._heater.pool_heat_cool_deadband if self._heater else None

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_fields({"DFU": int(value)})
        await self.coordinator.async_refresh_after_command()


class CompassDefrostEnd(_Base):
    """#18 Defrost End temperature (AXD, range 42-50°F)."""

    _attr_native_min_value = 42
    _attr_native_max_value = 50
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:snowflake-thermometer"

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator, api, entry, key)
        self._attr_unique_id = f"compass_{key}_defrost_end"
        self._attr_name = "Defrost End Temperature"

    @property
    def native_value(self) -> float | None:
        return self._heater.defrost_end if self._heater else None

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_fields({"AXD": int(value)})
        await self.coordinator.async_refresh_after_command()


class CompassCalibration(_Base):
    """Sensor calibration offset (CAL, range -10 to +10°F)."""

    _attr_native_min_value = -10
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator, api, entry, key)
        self._attr_unique_id = f"compass_{key}_calibration"
        self._attr_name = "Sensor Calibration"

    @property
    def native_value(self) -> float | None:
        return self._heater.calibration if self._heater else None

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_fields({"CAL": int(value)})
        await self.coordinator.async_refresh_after_command()


class CompassSpaTimerHours(_Base):
    """#15 Spa Timer hours component (DF3, range 0-20)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 20
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator, api, entry, key)
        self._attr_unique_id = f"compass_{key}_spa_timer_hours"
        self._attr_name = "Spa Timer Hours"

    @property
    def native_value(self) -> float | None:
        return self._heater.spa_timer_hours if self._heater else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._heater is None:
            return {}
        h = self._heater.spa_timer_hours
        m = self._heater.spa_timer_minutes
        if h == 0 and m == 0:
            return {"spa_timer_display": "Off"}
        return {"spa_timer_display": f"{h}h {m}m"}

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_fields({"DF3": int(value)})
        await self.coordinator.async_refresh_after_command()


class CompassSpaTimerMinutes(_Base):
    """#15 Spa Timer minutes component (STOF, values 0/15/30/45)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 45
    _attr_native_step = 15
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator, api, entry, key)
        self._attr_unique_id = f"compass_{key}_spa_timer_minutes"
        self._attr_name = "Spa Timer Minutes"

    @property
    def native_value(self) -> float | None:
        return self._heater.spa_timer_minutes if self._heater else None

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_fields({"STOF": int(value)})
        await self.coordinator.async_refresh_after_command()
