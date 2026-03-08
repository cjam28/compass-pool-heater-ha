"""DataUpdateCoordinator for Compass Pool Heater."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CompassApi, CompassApiError, HeaterState
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class CompassCoordinator(DataUpdateCoordinator[HeaterState]):
    """Shared data coordinator that polls the heater API once per interval."""

    def __init__(
        self, hass: HomeAssistant, api: CompassApi, scan_interval: int = DEFAULT_SCAN_INTERVAL
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Compass Pool Heater",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> HeaterState:
        try:
            return await self.api.get_state()
        except CompassApiError as err:
            raise UpdateFailed(f"Error communicating with heater API: {err}") from err
