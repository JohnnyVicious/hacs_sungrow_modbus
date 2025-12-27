import logging
from typing import List

from homeassistant.config_entries import ConfigEntry

from custom_components.sungrow_modbus import ModbusController
from custom_components.sungrow_modbus.helpers import get_controller_from_entry
from custom_components.sungrow_modbus.const import DOMAIN, ENTITIES, SWITCH_ENTITIES
from custom_components.sungrow_modbus.data.enums import InverterType, InverterFeature
from custom_components.sungrow_modbus.sensors.sungrow_binary_sensor import SungrowBinaryEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_devices):
    modbus_controller: ModbusController = get_controller_from_entry(hass, config_entry)

    # Internal switch to enable/disable polling (not a real Modbus register)
    switch_sensors = [
        {
            "register": 90005,
            "entities": [
                {"bit_position": 0, "name": "Sungrow Modbus Enabled"},
            ]
        }
    ]

    if modbus_controller.inverter_config.type == InverterType.HYBRID:
        # Sungrow Hybrid Inverter controls
        # Reference: modbus_sungrow.yaml and Sungrow Modbus documentation
        switch_sensors.extend([
            # Inverter Start/Stop - Register 12999 (holding)
            # 0xCF (207) = Start, 0xCE (206) = Stop
            {
                "register": 12999,
                "entities": [
                    {"name": "Inverter Power", "on_value": 0xCF, "off_value": 0xCE},
                ]
            },
            # Backup Mode Enable - Register 13074 (holding)
            # 0xAA (170) = Enable, 0x55 (85) = Disable
            {
                "register": 13074,
                "entities": [
                    {"name": "Backup Mode", "on_value": 0xAA, "off_value": 0x55},
                ]
            },
            # Export Power Limit Mode - Register 13086 (holding)
            # 0xAA (170) = Enable, 0x55 (85) = Disable
            {
                "register": 13086,
                "entities": [
                    {"name": "Export Power Limit Mode", "on_value": 0xAA, "off_value": 0x55},
                ]
            },
        ])

        # Load Adjustment controls (if battery feature is present)
        if InverterFeature.BATTERY in modbus_controller.inverter_config.features:
            switch_sensors.extend([
                # Load Adjustment On/Off - Register 13010 (holding)
                # 0xAA (170) = ON, 0x55 (85) = OFF
                {
                    "register": 13010,
                    "entities": [
                        {"name": "Load Adjustment Switch", "on_value": 0xAA, "off_value": 0x55},
                    ]
                },
            ])

    elif modbus_controller.inverter_config.type in [InverterType.GRID, InverterType.STRING]:
        # String/Grid inverter controls
        # Power Limit Enable - uses different registers for read/write
        switch_sensors.extend([
            {
                "read_register": 5007,
                "write_register": 5007,
                "entities": [
                    {"name": "Power Limitation Switch", "on_value": 0xAA, "off_value": 0x55},
                ]
            },
            {
                "read_register": 5010,
                "write_register": 5010,
                "entities": [
                    {"name": "Export Power Limitation", "on_value": 0xAA, "off_value": 0x55},
                ]
            },
        ])

    switchEntities: List[SungrowBinaryEntity] = []

    for main_entity in switch_sensors:
        for child_entity in main_entity[ENTITIES]:
            child_entity['register'] = main_entity.get('register', main_entity.get('read_register'))
            child_entity['write_register'] = main_entity.get('write_register', None)
            switchEntities.append(SungrowBinaryEntity(hass, modbus_controller, child_entity))

    hass.data[DOMAIN][SWITCH_ENTITIES] = switchEntities
    async_add_devices(switchEntities, True)

    return True
