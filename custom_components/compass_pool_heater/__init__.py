"""Compass Pool Heater integration for Home Assistant.

Controls Gulfstream, Aqua Comfort, Built Right, and other ICM Controls-based
pool heat pumps via the captouchwifi.com cloud API.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CompassApi
from .const import CONF_SCAN_INTERVAL, CONF_THERMOSTAT_KEY, CONF_TOKEN, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import CompassCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

BLUEPRINT_FILENAME = "pump_coordination.yaml"
BLUEPRINT_DIR = "compass_pool_heater"


def _install_blueprints(hass: HomeAssistant) -> None:
    """Copy bundled blueprints into the HA blueprints directory."""
    source = Path(__file__).parent / "blueprints" / BLUEPRINT_FILENAME
    if not source.is_file():
        return

    dest_dir = Path(hass.config.path("blueprints", "automation", BLUEPRINT_DIR))
    dest = dest_dir / BLUEPRINT_FILENAME

    if dest.is_file():
        if source.read_bytes() == dest.read_bytes():
            return
        _LOGGER.info("Updating Compass pool heater blueprint: %s", BLUEPRINT_FILENAME)
    else:
        _LOGGER.info("Installing Compass pool heater blueprint: %s", BLUEPRINT_FILENAME)

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)

    async_create(
        hass,
        (
            "The **Compass Pool Heater** integration installed the "
            "**Pump Coordination** automation blueprint.\n\n"
            "Go to **Settings → Automations & Scenes → Blueprints** to create "
            "an automation from it. You will need to configure your pump's "
            "start/stop actions and state entity."
        ),
        title="Compass Pool Heater – Blueprint Installed",
        notification_id=f"{DOMAIN}_blueprint_installed",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Compass Pool Heater from a config entry."""
    session = async_get_clientsession(hass)
    api = CompassApi(
        thermostat_key=entry.data[CONF_THERMOSTAT_KEY],
        token=entry.data[CONF_TOKEN],
        session=session,
    )

    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = CompassCoordinator(hass, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await hass.async_add_executor_job(_install_blueprints, hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
