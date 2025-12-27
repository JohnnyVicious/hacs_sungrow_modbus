"""Battery sensor entity for Sungrow multi-battery support.

Creates sensor entities for battery stacks connected via slave IDs 200-203.
"""

import logging
from typing import Optional, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback

from ..battery_controller import BatteryController
from ..const import DOMAIN
from ..sensor_data.battery_sensors import (
    battery_stack_sensors,
    get_battery_sensor_unique_id,
    get_battery_sensor_name,
)

_LOGGER = logging.getLogger(__name__)


class SungrowBatterySensor(SensorEntity):
    """Sensor entity for a battery stack measurement."""

    def __init__(
        self,
        hass: HomeAssistant,
        battery_controller: BatteryController,
        sensor_def: dict,
    ):
        """Initialize the battery sensor.

        Args:
            hass: Home Assistant instance
            battery_controller: The battery controller for this stack
            sensor_def: Sensor definition from battery_stack_sensors
        """
        self._hass = hass
        self._battery_controller = battery_controller
        self._sensor_def = sensor_def
        self._stack_index = battery_controller.stack_index
        self._inverter_serial = battery_controller.inverter.serial_number

        # Entity attributes
        self._attr_name = get_battery_sensor_name(sensor_def, self._stack_index)
        self._attr_unique_id = get_battery_sensor_unique_id(
            sensor_def, self._stack_index, self._inverter_serial
        )
        self._attr_has_entity_name = True

        # Sensor configuration
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_state_class = sensor_def.get("state_class")
        self._attr_native_unit_of_measurement = sensor_def.get("unit_of_measurement")

        # Internal state
        self._register = sensor_def.get("register")
        self._multiplier = sensor_def.get("multiplier", 1)
        self._signed = sensor_def.get("signed", False)
        self._register_count = sensor_def.get("register_count", 1)

        self._attr_native_value = None
        self._attr_available = battery_controller.battery.available

    @property
    def device_info(self):
        """Return device info for this battery stack."""
        return self._battery_controller.device_info

    def update_from_battery_data(self, data: dict) -> None:
        """Update sensor value from battery controller data.

        Args:
            data: Dictionary of battery data from read_status()
        """
        if not data:
            return

        # Map sensor unique to data key
        unique = self._sensor_def.get("unique", "")
        data_key_map = {
            "battery_stack_voltage": "voltage",
            "battery_stack_current": "current",
            "battery_stack_temperature": "temperature",
            "battery_stack_soc": "soc",
            "battery_stack_soh": "soh",
            "battery_stack_total_charge": "total_charge",
            "battery_stack_total_discharge": "total_discharge",
            "battery_stack_max_cell_voltage": "cell_voltage_max",
            "battery_stack_max_cell_position": "cell_voltage_max_position",
            "battery_stack_min_cell_voltage": "cell_voltage_min",
            "battery_stack_min_cell_position": "cell_voltage_min_position",
        }

        data_key = data_key_map.get(unique)
        if data_key and data_key in data:
            self._attr_native_value = data[data_key]
            self._attr_available = True
            # Only write state if entity is registered with HA
            if self.hass is not None:
                self.async_write_ha_state()

    @callback
    def async_update_availability(self, available: bool) -> None:
        """Update availability status."""
        self._attr_available = available
        # Only write state if entity is registered with HA
        if self.hass is not None:
            self.async_write_ha_state()


class SungrowBatteryDiagnosticSensor(SensorEntity):
    """Diagnostic sensor for battery stack (serial, firmware)."""

    def __init__(
        self,
        hass: HomeAssistant,
        battery_controller: BatteryController,
        sensor_def: dict,
    ):
        """Initialize the diagnostic sensor.

        Args:
            hass: Home Assistant instance
            battery_controller: The battery controller for this stack
            sensor_def: Sensor definition from battery_stack_diagnostic_sensors
        """
        self._hass = hass
        self._battery_controller = battery_controller
        self._sensor_def = sensor_def
        self._stack_index = battery_controller.stack_index
        self._inverter_serial = battery_controller.inverter.serial_number

        # Entity attributes
        self._attr_name = get_battery_sensor_name(sensor_def, self._stack_index)
        self._attr_unique_id = get_battery_sensor_unique_id(
            sensor_def, self._stack_index, self._inverter_serial
        )
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Set initial value from battery controller
        unique = sensor_def.get("unique", "")
        if "serial" in unique:
            self._attr_native_value = battery_controller.battery.serial_number
        elif "firmware" in unique:
            self._attr_native_value = battery_controller.battery.firmware_version
        else:
            self._attr_native_value = None

        self._attr_available = battery_controller.battery.available

    @property
    def device_info(self):
        """Return device info for this battery stack."""
        return self._battery_controller.device_info


def create_battery_sensors(
    hass: HomeAssistant,
    battery_controllers: list[BatteryController],
) -> tuple[list[SungrowBatterySensor], list[SungrowBatteryDiagnosticSensor]]:
    """Create sensor entities for all detected battery stacks.

    Args:
        hass: Home Assistant instance
        battery_controllers: List of detected battery controllers

    Returns:
        Tuple of (status_sensors, diagnostic_sensors)
    """
    from ..sensor_data.battery_sensors import (
        battery_stack_sensors,
        battery_stack_diagnostic_sensors,
    )

    status_sensors = []
    diagnostic_sensors = []

    for battery_controller in battery_controllers:
        # Create status sensors
        for sensor_def in battery_stack_sensors:
            sensor = SungrowBatterySensor(hass, battery_controller, sensor_def)
            status_sensors.append(sensor)

        # Create diagnostic sensors
        for sensor_def in battery_stack_diagnostic_sensors:
            sensor = SungrowBatteryDiagnosticSensor(hass, battery_controller, sensor_def)
            diagnostic_sensors.append(sensor)

    _LOGGER.info(
        "Created %d battery sensors for %d stack(s)",
        len(status_sensors) + len(diagnostic_sensors),
        len(battery_controllers),
    )

    return status_sensors, diagnostic_sensors
