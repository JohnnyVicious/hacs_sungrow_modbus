# Sungrow Modbus Integration for Home Assistant

> **Warning**: This integration is under active development. Use at your own risk.

## Overview

A Home Assistant custom integration for Sungrow inverters via Modbus TCP or Serial connection. Supports hybrid, string, and grid-connected inverters with automatic model-specific register mapping.

## Features

- **Modbus TCP and Serial** connection support
- **Model-specific register overrides** - automatic adjustment for different inverter register layouts
- **Configurable poll intervals** - fast/normal/slow polling for different sensor types
- **Hybrid inverter support** - PV, battery, grid, and load monitoring
- **String inverter support** - PV and grid monitoring
- **Example dashboards** - ready-to-use Lovelace dashboard templates

## Supported Inverters

### Tested

| Model | Connection    | Notes                                      |
|-------|---------------|--------------------------------------------|
| SH25T | TCP (WiNet-S) | Register offset -1 vs residential hybrids  |

### Expected Compatible

- **SH-RT series**: SH5.0RT, SH6.0RT, SH8.0RT, SH10RT, SH10RT-V112
- **SH-RS series**: SH3.6RS, SH4.6RS, SH5.0RS, SH6.0RS
- **SH-K series**: SH3K6, SH4K6, SH5K-20, SH5K-30
- **SG-RT series**: SG3.0RT - SG20RT (string inverters)

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=JohnnyVicious&repository=hacs_sungrow_modbus&category=integration)

1. Open HACS in Home Assistant
2. Click the 3-dot menu → "Custom Repositories"
3. Add `https://github.com/JohnnyVicious/hacs_sungrow_modbus` as "Integration"
4. Search for "Sungrow Modbus" and install

### Manual

Copy `custom_components/sungrow_modbus` to your Home Assistant `custom_components` directory.

## Configuration

1. Navigate to **Settings → Devices & Services → Add Integration**
2. Search for "Sungrow Modbus"
3. Enter connection details:
   - **TCP**: IP address and port (default: 502)
   - **Serial**: Device path, baudrate, parity settings
4. Select your inverter model
5. Configure optional features (PV, battery, generator support)

## Example Dashboards

The [`dashboards/`](dashboards/) folder contains ready-to-use Lovelace dashboard templates:

- **auto_entities_dashboard.yaml** - Auto-discovers all inverters, multi-inverter compatible (requires [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) HACS card)
- **hybrid_inverter.yaml** - Single inverter template (manual entity ID editing)

See [`dashboards/README.md`](dashboards/README.md) for installation instructions.

## Technical Details

### Register Architecture

Base sensor definitions target residential hybrid inverters (SH-RT/RS series). Model-specific overrides handle register differences:

```text
hybrid_sensors.py     →  Base register definitions
model_overrides.py    →  Per-model register adjustments
```

### SH25T Register Offsets

The SH25T uses registers offset by -1 compared to residential hybrids:

| Sensor          | Residential | SH25T |
|-----------------|-------------|-------|
| MPPT1 Voltage   | 5011        | 5010  |
| Daily PV Energy | 13002       | 13001 |
| Battery SOC     | 13023       | 13022 |
| Battery SOH     | 13024       | 13023 |

### Adding Model Overrides

Edit `sensor_data/model_overrides.py`:

```python
MODEL_OVERRIDES = {
    "SH25T": {
        "sensors": {
            "sungrow_modbus_mppt1_voltage": {"register": ['5010']},
            "sungrow_modbus_daily_pv_energy": {"register": ['13001']},
        }
    },
    "SH*T": {  # Wildcard pattern
        "sensors": {}
    }
}
```

## Register Reference

Register definitions are based on the [SunGather register map](https://raw.githubusercontent.com/bohdan-s/SunGather/refs/heads/main/SunGather/registers-sungrow.yaml) by [@bohdan-s](https://github.com/bohdan-s). Thank you for the comprehensive Sungrow register documentation.

## Acknowledgments

- [SunGather](https://github.com/bohdan-s/SunGather) by @bohdan-s - Sungrow register definitions and documentation
- [ha_solis_modbus](https://github.com/fboundy/ha_solis_modbus) by @fboundy - Original integration architecture
- [solis_modbus](https://github.com/Pho3niX90/solis_modbus) by @Pho3niX90 - Additional inspiration
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) by @MatthewFlamm - Home Assistant test fixtures
- [Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant) by @mkaiser - Sungrow Modbus YAML configuration reference

## License

See [LICENSE](LICENSE) for details.
