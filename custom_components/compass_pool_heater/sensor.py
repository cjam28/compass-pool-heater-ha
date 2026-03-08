"""Sensor platform for Compass Pool Heater."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HeaterState
from .const import CONF_THERMOSTAT_KEY, DOMAIN, FAULT_CODES, FAULT_DESCRIPTIONS
from .coordinator import CompassCoordinator

MODE_NAMES = {0: "Off", 1: "Pool Heat", 4: "Spa Heat"}
DEFROST_MODE_NAMES = {0: "Reverse Cycle", 1: "Air Defrost"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: CompassCoordinator = data["coordinator"]
    key = entry.data[CONF_THERMOSTAT_KEY]

    async_add_entities([
        CompassWaterTempSensor(coordinator, entry, key),
        CompassCoilTempSensor(coordinator, entry, key),
        CompassPoolSetpointSensor(coordinator, entry, key),
        CompassSpaSetpointSensor(coordinator, entry, key),
        CompassModeSensor(coordinator, entry, key),
        CompassFaultSensor(coordinator, entry, key),
        CompassDefrostModeSensor(coordinator, entry, key),
        CompassLastOnlineSensor(coordinator, entry, key),
    ])


class _Base(CoordinatorEntity[CompassCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._key = key

    @property
    def _state(self) -> HeaterState | None:
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._key)},
            "name": self._state.name if self._state else "Compass Pool Heater",
            "manufacturer": "Gulfstream / ICM Controls",
            "model": "Compass WiFi Heat Pump",
        }


class CompassWaterTempSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:thermometer-water"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_water_temp"
        self._attr_name = "Water Temperature"

    @property
    def native_value(self) -> float | None:
        return self._state.current_temp if self._state else None


class CompassCoilTempSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:thermostat-cog"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_coil_temp"
        self._attr_name = "Coil Temperature"

    @property
    def native_value(self) -> float | None:
        return self._state.coil_temp if self._state else None


class CompassPoolSetpointSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:pool-thermometer"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_pool_setpoint"
        self._attr_name = "Pool Setpoint"

    @property
    def native_value(self) -> float | None:
        if self._state is None:
            return None
        return self._state.pool_setpoint if self._state.pool_setpoint > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._state and self._state.pool_setpoint == 0:
            return {"status": "Off"}
        return {}


class CompassSpaSetpointSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:hot-tub"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_spa_setpoint"
        self._attr_name = "Spa Setpoint"

    @property
    def native_value(self) -> float | None:
        if self._state is None:
            return None
        return self._state.spa_setpoint if self._state.spa_setpoint > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._state and self._state.spa_setpoint == 0:
            return {"status": "Off"}
        return {}


class CompassModeSensor(_Base):
    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_mode"
        self._attr_name = "System Mode"

    @property
    def native_value(self) -> str | None:
        if self._state is None:
            return None
        return MODE_NAMES.get(self._state.mode, f"Unknown ({self._state.mode})")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._state is None:
            return {}
        return {"mode_raw": self._state.mode}


class CompassFaultSensor(_Base):
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_fault"
        self._attr_name = "Fault Status"

    @property
    def native_value(self) -> str | None:
        if self._state is None:
            return None
        code = self._state.fault_code
        if code == 0:
            return "No Current Fault"
        if code in FAULT_CODES:
            return FAULT_CODES[code]
        return f"Fault Code {code}"

    @property
    def icon(self) -> str:
        if self._state and self._state.fault_code:
            return "mdi:alert-circle"
        return "mdi:check-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._state is None:
            return {}
        code = self._state.fault_code
        attrs: dict[str, Any] = {
            "fault_code_raw": code,
            "fault_active": code != 0,
            "known_fault_types": FAULT_DESCRIPTIONS,
        }
        return attrs


class CompassDefrostModeSensor(_Base):
    _attr_icon = "mdi:snowflake-melt"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_defrost_mode"
        self._attr_name = "Defrost Mode"

    @property
    def native_value(self) -> str | None:
        if self._state is None:
            return None
        return DEFROST_MODE_NAMES.get(self._state.defrost_mode, f"Unknown ({self._state.defrost_mode})")


class CompassLastOnlineSensor(_Base):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_last_online"
        self._attr_name = "Last Online"

    @property
    def native_value(self) -> str | None:
        if self._state is None or not self._state.last_online:
            return None
        return self._state.last_online.replace(" ", "T") + "+00:00"
