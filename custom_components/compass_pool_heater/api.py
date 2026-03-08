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

    # Core status
    online: bool
    mode: int  # 0=off, 1=pool, 4=spa
    pool_setpoint: int  # 0=off, 50-104°F
    spa_setpoint: int  # 0=off, 50-104°F
    current_temp: int  # RMT - water temperature °F
    coil_temp: int  # GEN15 - coil temperature °F
    fault_code: int  # CHGF - 0=OK, 8=No Flow
    name: str
    description: str = ""
    last_online: str = ""

    # Limits
    max_setpoint: int = 104  # MXH
    min_setpoint: int = 50  # MNH

    # Settings - mapped to app System Configuration
    pool_cool: bool = False  # DF1 - #11 Pool Cool
    pool_heat_cool: bool = False  # DF2 - #12 Pool Heat/Cool
    pool_heat_cool_deadband: int = 3  # DFU - #13 (range 2-8)
    spa_timer_hours: int = 0  # DF3 - #15 Spa Timer hours (0-20)
    spa_timer_minutes: int = 0  # STOF - #15 Spa Timer minutes (0,15,30,45)
    defrost_mode: int = 1  # DFL - #17 (0=Reverse Cycle, 1=Air Defrost)
    defrost_end: int = 42  # AXD - #18 (range 42-50°F)
    calibration: int = 0  # CAL - sensor calibration
    deadband: int = 10  # DB
    heat_temp_sensitivity: int = 10  # HTS
    vacation_hold: bool = False  # VH
    lock: bool = False  # LKO - #2 Lock

    raw: dict[str, Any] = field(default_factory=dict)


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
            payload = {"action": "login", "username": email, "password": password}
            async with session.post(
                API_URL, json=payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            if data.get("result") != "success":
                raise CompassAuthError(data.get("message", "Login failed"))

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
            coil_temp=cs.get("GEN15", 0),
            fault_code=cs.get("CHGF", 0),
            name=detail.get("name", "Pool Heater"),
            description=detail.get("description", ""),
            last_online=detail.get("last_online", ""),
            max_setpoint=cs.get("MXH", 104),
            min_setpoint=cs.get("MNH", 50),
            pool_cool=bool(cs.get("DF1", 0)),
            pool_heat_cool=bool(cs.get("DF2", 0)),
            pool_heat_cool_deadband=cs.get("DFU", 3),
            spa_timer_hours=cs.get("DF3", 0),
            spa_timer_minutes=cs.get("STOF", 0),
            defrost_mode=cs.get("DFL", 1),
            defrost_end=cs.get("AXD", 42),
            calibration=cs.get("CAL", 0),
            deadband=cs.get("DB", 10),
            heat_temp_sensitivity=cs.get("HTS", 10),
            vacation_hold=bool(cs.get("VH", 0)),
            lock=bool(cs.get("LKO", 0)),
            raw=cs,
        )

    async def set_state(
        self,
        pool_setpoint: int,
        spa_setpoint: int,
        mode: int,
    ) -> None:
        """Send a control command to the heater.

        Setpoints: 0=Off, or 50-104°F.
        Mode: 0=Off, 1=Pool Heat, 4=Spa Heat.
        """
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

    async def test_connection(self) -> bool:
        """Test if credentials are valid."""
        try:
            await self.get_state()
            return True
        except CompassApiError:
            return False
