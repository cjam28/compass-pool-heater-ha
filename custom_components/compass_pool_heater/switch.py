"""Switch platform for Compass Pool Heater."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
        CompassFieldSwitch(
            coordinator, api, entry, key,
            field="VH", attr="vacation_hold",
            name="Vacation Hold",
            icon_on="mdi:beach", icon_off="mdi:beach",
            unique_suffix="vacation_hold",
        ),
        CompassFieldSwitch(
            coordinator, api, entry, key,
            field="DF1", attr="pool_cool",
            name="Pool Cool",
            icon_on="mdi:snowflake", icon_off="mdi:snowflake-off",
            unique_suffix="pool_cool",
        ),
        CompassFieldSwitch(
            coordinator, api, entry, key,
            field="DF2", attr="pool_heat_cool",
            name="Pool Heat/Cool",
            icon_on="mdi:sun-snowflake-variant", icon_off="mdi:sun-snowflake-variant",
            unique_suffix="pool_heat_cool",
        ),
        CompassDefrostModeSwitch(coordinator, api, entry, key),
        CompassLockSwitch(coordinator, api, entry, key),
    ])


class CompassFieldSwitch(CoordinatorEntity[CompassCoordinator], SwitchEntity):
    """Generic toggle switch backed by a thermostatSetFields boolean field."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CompassCoordinator,
        api: CompassApi,
        entry: ConfigEntry,
        key: str,
        *,
        field: str,
        attr: str,
        name: str,
        icon_on: str,
        icon_off: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._key = key
        self._field = field
        self._attr_name_str = attr
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._attr_unique_id = f"compass_{key}_{unique_suffix}"
        self._attr_name = name

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

    @property
    def is_on(self) -> bool | None:
        if self._state is None:
            return None
        return getattr(self._state, self._attr_name_str, False)

    @property
    def icon(self) -> str:
        return self._icon_on if self.is_on else self._icon_off

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.set_fields({self._field: 1})
        await self.coordinator.async_refresh_after_command()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._api.set_fields({self._field: 0})
        await self.coordinator.async_refresh_after_command()


class CompassDefrostModeSwitch(CoordinatorEntity[CompassCoordinator], SwitchEntity):
    """Defrost mode toggle: ON = Air Defrost, OFF = Reverse Cycle."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator)
        self._api = api
        self._key = key
        self._attr_unique_id = f"compass_{key}_defrost_mode_switch"
        self._attr_name = "Defrost Mode (Air Defrost)"

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

    @property
    def is_on(self) -> bool | None:
        if self._state is None:
            return None
        return self._state.defrost_mode == 1

    @property
    def icon(self) -> str:
        return "mdi:snowflake-melt" if self.is_on else "mdi:refresh"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"mode_description": "Air Defrost" if self.is_on else "Reverse Cycle"}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.set_fields({"DFL": 1})
        await self.coordinator.async_refresh_after_command()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._api.set_fields({"DFL": 0})
        await self.coordinator.async_refresh_after_command()


class CompassLockSwitch(CoordinatorEntity[CompassCoordinator], SwitchEntity):
    """Panel lock: ON = locked, OFF = unlocked."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, api, entry, key):
        super().__init__(coordinator)
        self._api = api
        self._key = key
        self._attr_unique_id = f"compass_{key}_lock"
        self._attr_name = "Panel Lock"

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

    @property
    def is_on(self) -> bool | None:
        if self._state is None:
            return None
        return self._state.lock

    @property
    def icon(self) -> str:
        return "mdi:lock" if self.is_on else "mdi:lock-open"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.set_fields({"LKO": 1})
        await self.coordinator.async_refresh_after_command()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._api.set_fields({"LKO": 0})
        await self.coordinator.async_refresh_after_command()
