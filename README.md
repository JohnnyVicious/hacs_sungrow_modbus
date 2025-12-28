# Sungrow Modbus Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/JohnnyVicious/hacs_sungrow_modbus?style=flat-square)](https://github.com/JohnnyVicious/hacs_sungrow_modbus/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/JohnnyVicious/hacs_sungrow_modbus?style=flat-square)](LICENSE)

## Overview

A Home Assistant custom integration for Sungrow inverters via Modbus TCP or Serial connection. Supports hybrid, string, and grid-connected inverters with automatic model detection and register mapping.

## Features

- **Modbus TCP and Serial (RS485)** connection support
- **Auto-detection** - automatically detects inverter model, serial number, and firmware
- **Multi-inverter support** - configure multiple inverters with proper entity namespacing
- **Model-specific register overrides** - automatic adjustment for different inverter register layouts
- **Configurable poll intervals** - fast/normal/slow polling for different sensor types
- **Hybrid inverter support** - PV, battery, grid, and load monitoring
- **String inverter support** - PV and grid monitoring
- **Multi-battery monitoring** - optional support for battery stack diagnostics (TCP only)
- **Writable entities** - control EMS mode, charge/discharge limits, and schedules
- **Example dashboards** - ready-to-use Lovelace dashboard templates

## Why a Native Integration?

This integration is built from the ground up as a native Home Assistant component rather than wrapping existing projects like [SunGather](https://github.com/bohdan-s/SunGather). While SunGather provides excellent register documentation (which we gratefully use as a reference), a native approach offers significant advantages:

| Aspect | SunGather Approach | This Integration |
|--------|-------------------|------------------|
| **Model filtering** | Per-register model lists (100+ models × 200+ registers) | Semantic features (`BATTERY`, `THREE_PHASE`, `MPPT3`) |
| **Polling** | Single interval for all registers | Multi-speed polling (fast/normal/slow) optimizes bandwidth |
| **HA Integration** | External via MQTT | Native entities with proper device grouping |
| **New model support** | Update hundreds of register lists | Add feature flags or pattern-matched overrides |
| **Auto-detection** | Manual model configuration | Reads device type code during setup |

The semantic feature system means adding support for a new inverter family often requires zero code changes - if it has battery storage, it automatically gets battery sensors. Pattern matching like `SH*T` applies overrides to all T-series models at once.

## Supported Inverters

### Hybrid Inverters (with battery storage)

| Series | Models | Notes |
|--------|--------|-------|
| **SH-RS** | SH3.0RS, SH3.6RS, SH4.0RS, SH4.6RS, SH5.0RS, SH6.0RS, SH8.0RS, SH10RS | Single-phase residential |
| **SH-RT** | SH5.0RT, SH6.0RT, SH8.0RT, SH10RT | Three-phase residential |
| **SH-RT-20** | SH5.0RT-20, SH6.0RT-20, SH8.0RT-20, SH10RT-20 | Three-phase with updated firmware |
| **SH-RT-V112/V122** | SH5.0RT-V112, SH8.0RT-V112, SH10RT-V112, SH10RT-V122 | Three-phase variants |
| **SH-T** | SH5T, SH10T, SH15T, SH20T, SH25T | Three-phase commercial |

### String Inverters (grid-tied, no battery)

| Series | Models | Notes |
|--------|--------|-------|
| **SG-RS** | SG3.0RS, SG3.6RS, SG4.0RS, SG5.0RS, SG6.0RS, SG10RS | Single-phase residential |
| **SG-RT** | SG3.0RT - SG20RT | Three-phase residential |

### Tested Models

| Model | Connection | Status |
|-------|------------|--------|
| SH25T | TCP (WiNet-S) | ✅ Verified |

> **Note**: Most Sungrow hybrid and string inverters using the standard Modbus protocol should work. The integration auto-detects the model during setup.

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
5. Configure optional features (PV, battery support)

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

## Recent Changes

### v0.1.4 (December 2025)

**Stability & Robustness Improvements**

- Thread-safe connection management with proper locking
- Input validation for service calls (register/value bounds checking)
- Fixed race conditions in derived sensor calculations
- Fixed premature cache updates before write confirmation
- Defensive programming for edge cases (null checks, index guards)

### v0.1.0

- Initial release with hybrid and string inverter support
- Auto-detection of inverter model and serial number
- Multi-speed polling (fast/normal/slow)
- Model-specific register overrides
- Example Lovelace dashboards

See [Releases](https://github.com/JohnnyVicious/hacs_sungrow_modbus/releases) for full changelog.

## Acknowledgments

- [SunGather](https://github.com/bohdan-s/SunGather) by @bohdan-s - Sungrow register definitions and documentation
- [ha_solis_modbus](https://github.com/fboundy/ha_solis_modbus) by @fboundy - Original integration architecture
- [solis_modbus](https://github.com/Pho3niX90/solis_modbus) by @Pho3niX90 - Additional inspiration
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) by @MatthewFlamm - Home Assistant test fixtures
- [Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant) by @mkaiser - Sungrow Modbus YAML configuration reference

## License

See [LICENSE](LICENSE) for details.
