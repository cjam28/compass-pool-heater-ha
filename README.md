# Compass Pool Heater – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

A Home Assistant custom integration for **Gulfstream**, **Aqua Comfort**, **Built Right**, and other pool/spa heat pumps that use the **ICM Controls Compass WiFi** module and the **Compass** mobile app.

## Features

| Platform | Entities |
|----------|----------|
| **Climate** | Full thermostat control — Off / Pool Heat / Spa Heat, target temperature (50-104°F or Off) |
| **Sensors** | Water Temperature, Coil Temperature, Pool Setpoint, Spa Setpoint, System Mode, Fault Status, Defrost Mode, Last Online |
| **Switches** | Vacation Hold, Pool Cool, Pool Heat/Cool, Defrost Mode (Air/Reverse Cycle), Panel Lock |
| **Numbers** | Pool Heat/Cool Deadband (2-8°F), Defrost End Temperature (42-50°F), Sensor Calibration (-10 to +10°F), Spa Timer Hours (0-20), Spa Timer Minutes (0/15/30/45) |

## Requirements

- A pool/spa heat pump with the **ICM Controls Compass WiFi** module
- An active **Compass** app account (email + password)
- The heat pump registered and working in the Compass mobile app

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add `https://github.com/cjam28/compass-pool-heater-ha` as an **Integration**
4. Click **Download**
5. Restart Home Assistant

### Manual

Copy the `custom_components/compass_pool_heater` folder into your Home Assistant `config/custom_components/` directory and restart.

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Compass Pool Heater**
3. Enter your Compass app email and password
4. If you have multiple heat pumps, select which one to add
5. Done — entities appear automatically

## Entities Reference

### Climate

The main thermostat entity with:
- **HVAC Modes**: Off, Heat
- **Presets**: Pool, Spa
- **Temperature range**: 50-104°F (setpoint of 0 = Off)

### Sensors

| Sensor | Description |
|--------|-------------|
| Water Temperature | Current water temperature (°F) — `RMT` register |
| Coil Temperature | Heat pump coil temperature (°F) — `GEN15` register |
| Pool Setpoint | Current pool target temperature or "Off" |
| Spa Setpoint | Current spa target temperature or "Off" |
| System Mode | Off / Pool Heat / Spa Heat |
| Fault Status | No Fault, No Flow, or fault code |
| Defrost Mode | Air Defrost or Reverse Cycle |
| Last Online | Timestamp of last communication |

### Switches

| Switch | App Setting | API Field |
|--------|-------------|-----------|
| Vacation Hold | Vacation Hold | `VH` |
| Pool Cool | #11 Pool Cool | `DF1` |
| Pool Heat/Cool | #12 Pool Heat/Cool | `DF2` |
| Defrost Mode (Air Defrost) | #17 Defrost Mode | `DFL` (1=Air, 0=Reverse Cycle) |
| Panel Lock | #2 Lock | `LKO` |

### Number Controls

| Control | App Setting | API Field | Range |
|---------|-------------|-----------|-------|
| Pool Heat/Cool Deadband | #13 Pool Heat/Cool Deadband | `DFU` | 2-8°F |
| Defrost End Temperature | #18 Defrost End | `AXD` | 42-50°F |
| Sensor Calibration | Sensor Calibration | `CAL` | -10 to +10°F |
| Spa Timer Hours | #15 Spa Timer (hours) | `DF3` | 0-20 |
| Spa Timer Minutes | #15 Spa Timer (minutes) | `STOF` | 0, 15, 30, 45 |

## How It Works

This integration communicates with the ICM Controls cloud API at `captouchwifi.com` — the same backend used by the Compass mobile app. The heat pump connects to WiFi and maintains a persistent connection to the cloud; commands are relayed through it.

**Polling interval**: 30 seconds (configurable).

## API Field Reference

| API Field | Compass App Setting | Description |
|-----------|-------------------|-------------|
| `MD` | #1 System Mode | 0=Off, 1=Pool Heat, 4=Spa Heat |
| `LKO` | #2 Lock | 0=Unlocked, 1=Locked |
| `CHGF` | #3 Fault Conditions | 0=No Fault, 8=No Flow |
| `GEN15` | #4 Coil Temperature | Read-only sensor (°F) |
| `RMT` | Water Temperature | Read-only sensor (°F) |
| `DF1` | #11 Pool Cool | 0=Disabled, 1=Enabled |
| `DF2` | #12 Pool Heat/Cool | 0=Disabled, 1=Enabled |
| `DFU` | #13 Pool Heat/Cool Deadband | Range 2-8 (°F) |
| `DF3` | #15 Spa Timer (hours) | Range 0-20 |
| `STOF` | #15 Spa Timer (minutes) | 0, 15, 30, 45 |
| `DFL` | #17 Defrost Mode | 0=Reverse Cycle, 1=Air Defrost |
| `AXD` | #18 Defrost End | Range 42-50 (°F) |
| `CAL` | Sensor Calibration | Range -10 to +10 (°F) |
| `VH` | Vacation Hold | 0=Off, 1=On |
| `RSV1` | Pool Setpoint | 0=Off, 50-104 (°F) |
| `RSV2` | Spa Setpoint | 0=Off, 50-104 (°F) |

## Compatible Hardware

Any pool/spa heat pump using the ICM Controls Compass WiFi module, including:

- **Gulfstream** (confirmed working)
- **Aqua Comfort**
- **Built Right**
- Other ICM Controls-based units with the Compass app

## Troubleshooting

- **"Invalid email or password"**: The API uses your email as the `username` field. Make sure you can log in to the Compass mobile app with the same credentials.
- **Stale data**: The cloud API is polled every 30 seconds. If the heater is offline, the last known state is shown.
- **"No Flow" fault**: This is reported by the heat pump itself when it detects insufficient water flow. Check your pool pump.

## Known Fault Codes (CHGF register)

Extracted from the Compass app source:

| CHGF Value | Fault Description |
|---|---|
| 0 | No Current Fault |
| 8 | No Flow *(confirmed)* |
| ? | Evap. Sensor Malfunction |
| ? | Water Sensor Malfunction |
| ? | Low Pressure Switch |
| ? | High Pressure Switch |

Only `CHGF=8` has been confirmed via live testing. The other fault codes exist in the app but their exact CHGF values haven't been mapped yet. If you encounter a different fault code, the raw value will be shown — please report it so we can complete the mapping!

## License

MIT
