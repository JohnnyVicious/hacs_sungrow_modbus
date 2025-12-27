import logging
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.sungrow_modbus import ModbusController
from custom_components.sungrow_modbus.data.enums import InverterFeature, InverterType
from custom_components.sungrow_modbus.helpers import get_controller_from_entry
from custom_components.sungrow_modbus.sensors.sungrow_select_entity import SungrowSelectEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_devices,
) -> None:
    controller: ModbusController = get_controller_from_entry(hass, config_entry)
    _LOGGER.info("Options %s", len(config_entry.options))

    platform_config = config_entry.data or {}
    inverter_type = controller.inverter_config.type

    if len(config_entry.options) > 0:
        platform_config = config_entry.options

    _LOGGER.info(f"Sungrow platform_config: {platform_config}")

    sensor_groups = []

    if inverter_type == InverterType.HYBRID:
        # Sungrow Hybrid Inverter selects
        # Reference: modbus_sungrow.yaml and Sungrow Modbus documentation

        # EMS Mode Selection - Register 13049
        # 0 = Self-consumption mode (default)
        # 2 = Forced mode (compulsory mode in modbus spec)
        # 3 = External EMS
        # 4 = VPP (used for Amber control)
        # 8 = MicroGrid
        sensor_groups.append({
            "register": 13049,
            "name": "EMS Mode",
            "entities": [
                {"name": "Self-consumption", "on_value": 0},
                {"name": "Forced mode", "on_value": 2},
                {"name": "External EMS", "on_value": 3},
                {"name": "VPP", "on_value": 4},
                {"name": "MicroGrid", "on_value": 8},
            ]
        })

        # Battery Forced Charge/Discharge Command - Register 13050
        # 0xCC (204) = Stop (default)
        # 0xAA (170) = Forced charge
        # 0xBB (187) = Forced discharge
        sensor_groups.append({
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": [
                {"name": "Stop", "on_value": 0xCC},
                {"name": "Force Charge", "on_value": 0xAA},
                {"name": "Force Discharge", "on_value": 0xBB},
            ]
        })

        # Load Adjustment Mode - Register 13001
        # 0 = Timing
        # 1 = ON/OFF
        # 2 = Power optimization
        # 3 = Disabled
        if InverterFeature.BATTERY in controller.inverter_config.features:
            sensor_groups.append({
                "register": 13001,
                "name": "Load Adjustment Mode",
                "entities": [
                    {"name": "Timing", "on_value": 0},
                    {"name": "ON/OFF", "on_value": 1},
                    {"name": "Power optimization", "on_value": 2},
                    {"name": "Disabled", "on_value": 3},
                ]
            })

    sensors: List[SungrowSelectEntity] = []
    for sensor_group in sensor_groups:
        sensors.append(SungrowSelectEntity(hass, controller, sensor_group))
    _LOGGER.info(f"Select entities = {len(sensors)}")
    async_add_devices(sensors, True)
