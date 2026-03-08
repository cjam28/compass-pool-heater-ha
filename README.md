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

## Automation Blueprints

### Pump Coordination

This blueprint automatically coordinates your pool pump with the heater to prevent "No Flow" faults and handle stale temperature readings (the water temp sensor at the heater reads stagnant pipe water when the pump is off).

**Three behaviors:**

1. **Auto-Start** — turns the pump on when heating is activated
2. **Periodic Check** — every N minutes, if the heater wants to heat but the pump is off, starts the pump, waits for a fresh reading, and decides whether to keep it running or shut it back off
3. **Auto-Stop** — optionally turns the pump off after a configurable delay when the heater is turned off

The blueprint works with **any** pump controller — njsPC-HA, Pentair ScreenLogic, Hayward OmniLogic, a simple relay switch, or anything else in Home Assistant. You define exactly what "start pump" and "stop pump" mean for your setup via the action selectors.

#### Setup

The blueprint is **automatically installed** when you add the integration. After installing or updating via HACS and restarting Home Assistant, you will see a persistent notification prompting you to configure it.

1. Go to **Settings** → **Automations & Scenes** → **Blueprints**
2. Find **Compass Pool Heater – Pump Coordination**
3. Click **Create Automation**
4. Configure the inputs (see below) for your pump setup
5. Save and enable the automation

<details>
<summary>Manual import (alternative)</summary>

If you prefer to import manually, go to **Blueprints** → **Import Blueprint** and paste:
```
https://github.com/cjam28/compass-pool-heater-ha/raw/main/blueprints/automation/compass_pool_heater/pump_coordination.yaml
```
</details>

#### Inputs

| Input | Description | Default |
|-------|-------------|---------|
| Pool Heater | Compass heater climate entity | — |
| Water Temperature Sensor | Water temp sensor (from heater) | — |
| Pump State Entity | Entity showing pump on/off (binary_sensor, switch, etc.) | — |
| Pump "On" State Value | State value meaning the pump is running | `on` |
| Pump Start Action | Action(s) to start the pump | — |
| Pump Stop Action | Action(s) to stop the pump | — |
| Check Frequency | How often to check temp when pump is off | Every 60 min |
| Pump Warmup Time | Seconds to run pump for a fresh temp reading | 120 |
| Pump-Off Delay | Minutes to keep pump on after heater turns off (0 = disabled) | 5 |

#### Example: Simple On/Off Switch

| Input | Value |
|-------|-------|
| Pump State Entity | `switch.pool_pump` |
| Pump "On" State Value | `on` |
| Pump Start Action | Service `switch.turn_on` on `switch.pool_pump` |
| Pump Stop Action | Service `switch.turn_off` on `switch.pool_pump` |

#### Example: njsPC-HA (Multi-Speed Pump)

| Input | Value |
|-------|-------|
| Pump State Entity | `binary_sensor.pump_running_state` |
| Pump "On" State Value | `on` |
| Pump Start Action | Service `script.turn_on` on `script.pump_set_speed_exclusive` with data `target: default` |
| Pump Stop Action | Service `script.turn_on` on `script.pump_all_speeds_off` |

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
