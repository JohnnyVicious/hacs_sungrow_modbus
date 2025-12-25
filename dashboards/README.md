# Example Dashboards

This folder contains example Lovelace dashboards for the Sungrow Modbus integration.

## Available Dashboards

| File | Description | Multi-Inverter |
|------|-------------|----------------|
| `auto_entities_dashboard.yaml` | Auto-discovers all inverters (recommended) | Yes |
| `hybrid_inverter.yaml` | Single inverter template | No (manual edit) |

## Recommended: Auto-Entities Dashboard

The `auto_entities_dashboard.yaml` automatically discovers all Sungrow inverters - no manual entity editing required. New inverters appear automatically.

### Requirements

Install the **auto-entities** card from HACS:
1. Open HACS → Frontend
2. Search for "auto-entities"
3. Install [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) by @thomasloven
4. Restart Home Assistant

### Installation

1. Go to **Settings → Dashboards → Add Dashboard**
2. Name it "Solar" or "Sungrow"
3. Open the new dashboard
4. Click three-dot menu → **Edit Dashboard**
5. Enable "Start with an empty dashboard" → **Take Control**
6. Click three-dot menu → **Raw configuration editor**
7. Paste the contents of `auto_entities_dashboard.yaml`
8. Save and reload

That's it! All your Sungrow inverters will appear automatically.

---

## Alternative: Manual Template Dashboard

If you prefer not to install auto-entities, use `hybrid_inverter.yaml` with manual entity ID editing.

### 1. Find Your Entity Prefix

After installing the integration, your entities will be named based on your inverter model. Check your entity IDs in **Settings > Devices & Services > Sungrow Modbus > Entities**.

Example entity naming patterns:
- `sensor.sungrow_sh25t_daily_pv_generation`
- `sensor.sungrow_sh10rt_battery_level`
- `sensor.sungrow_sh5_0rs_inverter_temperature`

### 2. Install the Dashboard

1. Go to **Settings > Dashboards > Add Dashboard**
2. Name it "Solar" or "PV System"
3. Click **Create**
4. Open the new dashboard
5. Click the three-dot menu (top right) > **Edit Dashboard**
6. Enable "Start with an empty dashboard" and click **Take Control**
7. Click the three-dot menu again > **Raw configuration editor**
8. Copy and paste the contents of the dashboard YAML file
9. **Find and replace** the placeholder prefix with your actual entity prefix:
   - Replace `sungrow_sh10rt_` with your prefix (e.g., `sungrow_sh25t_`)
10. Click **Save** and reload the page

### 3. Entity ID Reference

The dashboard uses these entity patterns (replace `sungrow_sh10rt_` with your prefix):

#### Power Sensors
| Dashboard Entity | Your Entity |
|-----------------|-------------|
| `sensor.sungrow_sh10rt_total_dc_power` | PV power from panels |
| `sensor.sungrow_sh10rt_load_power` | Home consumption |
| `sensor.sungrow_sh10rt_export_power` | Power to grid |
| `sensor.sungrow_sh10rt_battery_power` | Battery charge/discharge |

#### Energy Sensors
| Dashboard Entity | Your Entity |
|-----------------|-------------|
| `sensor.sungrow_sh10rt_daily_pv_generation` | Daily solar production |
| `sensor.sungrow_sh10rt_daily_import_energy` | Daily grid import |
| `sensor.sungrow_sh10rt_daily_export_energy` | Daily grid export |

#### Battery Sensors
| Dashboard Entity | Your Entity |
|-----------------|-------------|
| `sensor.sungrow_sh10rt_battery_level` | Battery state of charge |
| `sensor.sungrow_sh10rt_battery_state_of_health` | Battery health |
| `sensor.sungrow_sh10rt_battery_temperature` | Battery temperature |

## Customization

### Adding EMS Control

The base dashboard is read-only. To add control capabilities, you'll need to create Home Assistant helpers that write to the inverter's holding registers. See the integration documentation for available writable registers.

### Third-Party Cards

For enhanced visualizations, consider these HACS frontend cards:
- [Power Flow Card Plus](https://github.com/flixlix/power-flow-card-plus)
- [Tesla Style Solar Power Card](https://github.com/reptilex/tesla-style-solar-power-card)
- [Apex Charts Card](https://github.com/RomRider/apexcharts-card)

## Credits

Dashboard design inspired by [@mkaiser's Sungrow dashboard](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant).
