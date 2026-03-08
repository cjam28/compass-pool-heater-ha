DOMAIN = "compass_pool_heater"

API_URL = "https://www.captouchwifi.com/icm/api/call"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_THERMOSTAT_KEY = "thermostat_key"
CONF_TOKEN = "token"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30

SET_BLOCK_START_ADDRESS = 27
SET_BLOCK_LENGTH = 7

MODE_OFF = 0
MODE_POOL = 1
MODE_SPA = 4

FAULT_CODES: dict[int, str] = {
    0: "No Current Fault",
    8: "No Flow",
}

FAULT_DESCRIPTIONS = [
    "Evap. Sensor Malfunction",
    "Water Sensor Malfunction",
    "No Flow",
    "Low Pressure Switch",
    "High Pressure Switch",
]
