"""API client for the ICM Controls / Compass WiFi pool heater cloud.

Communicates with https://www.captouchwifi.com/icm/api/call to control
Gulfstream, Aqua Comfort, Built Right, and other ICM-based pool heat pumps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    API_URL,
    MODE_OFF,
    MODE_POOL,
    MODE_SPA,
    SET_BLOCK_LENGTH,
    SET_BLOCK_START_ADDRESS,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
}


@dataclass
class DeviceInfo:
    """Basic device info returned by getPasDevices."""

    device_id: str
    unique_key: str
    name: str
    description: str
    model_name: str
    owner: str
    online: bool


@dataclass
class HeaterState:
    """Parsed heater state from the API."""

    online: bool
    mode: int
    pool_setpoint: int
    spa_setpoint: int
    current_temp: int
    max_setpoint: int
    min_setpoint: int
    fault_code: int
    name: str
    description: str = ""
    last_online: str = ""
    deadband: int = 0
    heat_temp_sensitivity: int = 0
    calibration: int = 0
    defrost_guard: int = 0
    defrost_duration: int = 0
    defrost_lock: int = 0
    aux_heat_delta: int = 0
    vacation_hold: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertConfig:
    """Alert thresholds and notification settings."""

    high_temp_value: int = 0
    high_temp_enabled: bool = False
    low_temp_value: int = 0
    low_temp_enabled: bool = False
    notify_email: bool = False
    notify_mobile: bool = False
    notify_text: bool = False


class CompassApiError(Exception):
    """Raised on API communication failure."""


class CompassAuthError(CompassApiError):
    """Raised when login credentials are invalid."""


class CompassApi:
    """Client for the captouchwifi.com cloud API."""

    def __init__(
        self,
        thermostat_key: str,
        token: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._thermostat_key = thermostat_key
        self._token = token
        self._session = session
        self._owns_session = session is None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def _call(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = await self._ensure_session()
        payload["thermostatKey"] = self._thermostat_key
        payload["token"] = self._token

        try:
            async with session.post(
                API_URL, json=payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CompassApiError(f"API request failed: {err}") from err

        if data.get("result") != "success":
            raise CompassApiError(f"API returned: {data.get('message', data.get('result', 'unknown'))}")

        return data

    @staticmethod
    async def login(
        email: str, password: str, session: aiohttp.ClientSession | None = None
    ) -> tuple[str, list[DeviceInfo]]:
        """Authenticate and return (token, devices).

        Raises CompassAuthError on invalid credentials.
        """
        owns_session = session is None
        if session is None:
            session = aiohttp.ClientSession()

        try:
            payload = {"action": "login", "email": email, "password": password}
            async with session.post(
                API_URL, json=payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            if data.get("result") != "success":
                raise CompassAuthError(
                    data.get("message", "Login failed")
                )

            token = data.get("token", "")
            if not token:
                raise CompassAuthError("No token returned from login")

            devices_payload = {
                "action": "getPasDevices",
                "token": token,
                "additionalFields": ["MD", "CF", "RMT"],
            }
            async with session.post(
                API_URL, json=devices_payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                dev_data = await resp.json()

            devices = []
            for d in dev_data.get("devices", []):
                devices.append(
                    DeviceInfo(
                        device_id=d.get("id", ""),
                        unique_key=d.get("unique_key", ""),
                        name=d.get("name", ""),
                        description=d.get("description", ""),
                        model_name=d.get("model_name", ""),
                        owner=d.get("owner", ""),
                        online=d.get("online") == "1",
                    )
                )

            return token, devices

        except aiohttp.ClientError as err:
            raise CompassApiError(f"Login request failed: {err}") from err
        finally:
            if owns_session:
                await session.close()

    async def get_state(self) -> HeaterState:
        """Poll the heater for its current state."""
        data = await self._call({"action": "thermostatGetDetail"})
        detail = data.get("detail", {})
        cs = detail.get("currentState", {})

        return HeaterState(
            online=True,
            mode=cs.get("MD", 0),
            pool_setpoint=cs.get("RSV1", 0),
            spa_setpoint=cs.get("RSV2", 0),
            current_temp=cs.get("RMT", 0),
            max_setpoint=cs.get("MXH", 104),
            min_setpoint=cs.get("MNH", 50),
            fault_code=cs.get("FLT", 0),
            name=detail.get("name", "Pool Heater"),
            description=detail.get("description", ""),
            last_online=detail.get("last_online", ""),
            deadband=cs.get("DB", 0),
            heat_temp_sensitivity=cs.get("HTS", 0),
            calibration=cs.get("CAL", 0),
            defrost_guard=cs.get("DFG", 0),
            defrost_duration=cs.get("DFU", 0),
            defrost_lock=cs.get("DFL", 0),
            aux_heat_delta=cs.get("AXD", 0),
            vacation_hold=cs.get("VH", 0),
            raw=cs,
        )

    async def set_state(
        self,
        pool_setpoint: int,
        spa_setpoint: int,
        mode: int,
    ) -> None:
        """Send a control command to the heater."""
        if mode not in (MODE_OFF, MODE_POOL, MODE_SPA):
            raise ValueError(f"Invalid mode: {mode}")

        data = [pool_setpoint, spa_setpoint, 0, 0, 0, 0, mode]

        await self._call(
            {
                "action": "thermostatSetBlock",
                "startAddress": SET_BLOCK_START_ADDRESS,
                "length": SET_BLOCK_LENGTH,
                "data": data,
            }
        )
        _LOGGER.debug(
            "Set heater: pool=%d spa=%d mode=%d", pool_setpoint, spa_setpoint, mode
        )

    async def set_fields(self, fields: dict[str, int]) -> None:
        """Set one or more configuration fields on the heater."""
        await self._call({"action": "thermostatSetFields", "fields": fields})
        _LOGGER.debug("Set fields: %s", fields)

    async def get_alerts(self) -> AlertConfig:
        """Get alert configuration."""
        alerts_data = await self._call({"action": "thermostatGetAlerts"})
        method_data = await self._call({"action": "thermostatGetAlertMethod"})

        config = AlertConfig(
            notify_email=bool(method_data.get("email")),
            notify_mobile=bool(method_data.get("mobile")),
            notify_text=bool(method_data.get("text")),
        )

        for alert in alerts_data.get("alerts", []):
            if alert["alert_type"] == "HIGH_TEMP":
                config.high_temp_value = int(alert["nValue"])
                config.high_temp_enabled = alert["enabled"] == "1"
            elif alert["alert_type"] == "LOW_TEMP":
                config.low_temp_value = int(alert["nValue"])
                config.low_temp_enabled = alert["enabled"] == "1"

        return config

    async def set_alert(self, alert_type: str, value: int, enabled: bool) -> None:
        """Set a temperature alert threshold."""
        await self._call(
            {
                "action": "thermostatSetAlert",
                "alertType": alert_type,
                "value": value,
                "enabled": enabled,
            }
        )

    async def test_connection(self) -> bool:
        """Test if credentials are valid."""
        try:
            await self.get_state()
            return True
        except CompassApiError:
            return False
