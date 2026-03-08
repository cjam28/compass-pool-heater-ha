# Compass Pool Heater - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for **Gulfstream**, **Aqua Comfort**, **Built Right**, and other pool heat pumps controlled by the **Compass WiFi** app (by ICM Controls).

## Features

- **Climate entity** with full thermostat controls (temperature, on/off)
- **Pool / Spa presets** to switch between pool and spa heating modes
- **Temperature sensors** for water temperature, pool setpoint, and spa setpoint
- **Diagnostic sensors** for operating mode, fault codes, deadband, calibration, and more
- **Switches** for vacation hold, defrost guard, and defrost lock
- **Automatic device discovery** for accounts with multiple heaters

## Requirements

- A pool heat pump with the **Compass WiFi** module installed
- A working **Compass app** account (the same email/password you use in the mobile app)
- The heater must be online and connected to the Compass cloud service

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu (top right) and select **Custom repositories**
4. Add this repository URL: `https://github.com/christoalto/compass-pool-heater-ha`
5. Select **Integration** as the category
6. Click **Add**
7. Search for "Compass Pool Heater" and install it
8. Restart Home Assistant

### Manual

1. Copy the `custom_components/compass_pool_heater` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Compass Pool Heater**
3. Enter your Compass app **email** and **password**
4. If you have multiple heaters, select which one to add
5. Done! The integration will create climate, sensor, and switch entities

## Entities

### Climate

| Entity | Description |
|--------|-------------|
| `climate.compass_pool_heater` | Main thermostat — set temperature, switch between Pool/Spa presets, turn on/off |

### Sensors

| Entity | Description |
|--------|-------------|
| Water Temperature | Current water temperature reading (°F) |
| Pool Setpoint | Current pool heating target (°F) |
| Spa Setpoint | Current spa heating target (°F) |
| Operating Mode | Current mode: Off, Pool, or Spa |
| Fault Code | Active fault code (0 = no fault) |
| Deadband | Temperature deadband setting |
| Heat Sensitivity | Heat temperature sensitivity setting |
| Calibration | Temperature calibration offset |
| Defrost Duration | Defrost cycle duration setting |
| Aux Heat Delta | Auxiliary heat delta threshold |

### Switches

| Entity | Description |
|--------|-------------|
| Vacation Hold | Enable/disable vacation hold mode |
| Defrost Guard | Enable/disable defrost guard |
| Defrost Lock | Enable/disable defrost lock |

## How It Works

This integration communicates with the **captouchwifi.com** cloud API — the same backend used by the Compass mobile app. It polls the heater status on a configurable interval (default 30 seconds) and sends commands when you adjust settings in Home Assistant.

```
Home Assistant → captouchwifi.com API → Heater WiFi Module → Heat Pump
```

## Compatible Hardware

This integration works with any pool heat pump that uses the **Compass WiFi** module by ICM Controls, including:

- Gulfstream heat pumps
- Aqua Comfort heat pumps
- Built Right heat pumps
- Other ICM Controls-based pool heaters

If your heater uses the "Compass WiFi Heat Pump Navigator" app, this integration should work.

## Using with nodejs-poolController

If you also use [nodejs-poolController](https://github.com/tagyoureit/nodejs-poolController) (njsPC) for your pool pump, this integration works alongside [njsPC-HA](https://github.com/Crewski/njsPC-HA). They are separate integrations controlling separate equipment:

- **njsPC-HA** controls your pool automation system (pumps, valves, chlorinator) via RS-485
- **Compass Pool Heater** controls your heat pump via the cloud API

You can create Home Assistant automations to coordinate between them, for example:
- Turn on the heater when the pool pump starts
- Set spa mode on the heater when njsPC activates the spa circuit

## Troubleshooting

- **"Could not connect"**: Verify the Compass cloud service is online by checking the mobile app
- **"Invalid credentials"**: Use the same email/password as your Compass mobile app
- **"No devices found"**: Ensure your heater is registered in the Compass app and online
- **Stale data**: The heater WiFi module can go offline temporarily. Check `last_online` attribute

## Credits

This integration was built by reverse-engineering the Compass WiFi app's cloud API. The API is not officially documented by ICM Controls.

## License

MIT
