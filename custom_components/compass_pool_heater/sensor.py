"""Sensor platform for Compass Pool Heater."""

from __future__ import annotations

import logging
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
from .const import CONF_THERMOSTAT_KEY, DOMAIN
from .coordinator import CompassCoordinator

_LOGGER = logging.getLogger(__name__)

MODE_NAMES = {0: "Off", 1: "Pool", 4: "Spa"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: CompassCoordinator = data["coordinator"]
    key = entry.data[CONF_THERMOSTAT_KEY]

    async_add_entities(
        [
            CompassTemperatureSensor(coordinator, entry, key, "water_temperature", "Water Temperature", "RMT"),
            CompassTemperatureSensor(coordinator, entry, key, "pool_setpoint", "Pool Setpoint", "RSV1"),
            CompassTemperatureSensor(coordinator, entry, key, "spa_setpoint", "Spa Setpoint", "RSV2"),
            CompassModeSensor(coordinator, entry, key),
            CompassFaultSensor(coordinator, entry, key),
            CompassDiagnosticSensor(coordinator, entry, key, "deadband", "Deadband", "DB", "mdi:thermometer-lines"),
            CompassDiagnosticSensor(coordinator, entry, key, "heat_sensitivity", "Heat Sensitivity", "HTS", "mdi:gauge"),
            CompassDiagnosticSensor(coordinator, entry, key, "calibration", "Calibration", "CAL", "mdi:tune"),
            CompassDiagnosticSensor(coordinator, entry, key, "defrost_duration", "Defrost Duration", "DFU", "mdi:snowflake-melt"),
            CompassDiagnosticSensor(coordinator, entry, key, "aux_heat_delta", "Aux Heat Delta", "AXD", "mdi:thermometer-chevron-up"),
        ],
    )


class CompassSensorBase(CoordinatorEntity[CompassCoordinator], SensorEntity):
    """Base class for Compass sensors using the shared coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key

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


class CompassTemperatureSensor(CompassSensorBase):
    """Temperature reading sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(
        self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str,
        sensor_id: str, name: str, register: str,
    ) -> None:
        super().__init__(coordinator, entry, key)
        self._register = register
        self._attr_unique_id = f"compass_{key}_{sensor_id}"
        self._attr_name = name

    @property
    def native_value(self) -> float | None:
        if self._state is None:
            return None
        return self._state.raw.get(self._register)


class CompassModeSensor(CompassSensorBase):
    """Heater operating mode sensor."""

    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_mode"
        self._attr_name = "Operating Mode"

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


class CompassFaultSensor(CompassSensorBase):
    """Fault code sensor."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._attr_unique_id = f"compass_{key}_fault"
        self._attr_name = "Fault Code"

    @property
    def native_value(self) -> int | None:
        if self._state is None:
            return None
        return self._state.fault_code

    @property
    def icon(self) -> str:
        if self._state and self._state.fault_code:
            return "mdi:alert-circle"
        return "mdi:check-circle-outline"


class CompassDiagnosticSensor(CompassSensorBase):
    """Generic diagnostic value sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: CompassCoordinator, entry: ConfigEntry, key: str,
        sensor_id: str, name: str, register: str, icon: str,
    ) -> None:
        super().__init__(coordinator, entry, key)
        self._register = register
        self._attr_unique_id = f"compass_{key}_{sensor_id}"
        self._attr_name = name
        self._attr_icon = icon

    @property
    def native_value(self) -> int | None:
        if self._state is None:
            return None
        return self._state.raw.get(self._register)
