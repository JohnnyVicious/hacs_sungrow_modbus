import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from custom_components.sungrow_modbus import ModbusController
from custom_components.sungrow_modbus.const import (
    BATTERY_CONTROLLER,
    BATTERY_SENSORS,
    DOMAIN,
    SENSOR_DERIVED_ENTITIES,
    SENSOR_ENTITIES,
    VALUES,
)
from custom_components.sungrow_modbus.helpers import get_controller_from_entry
from custom_components.sungrow_modbus.sensors.sungrow_derived_sensor import SungrowDerivedSensor
from custom_components.sungrow_modbus.sensors.sungrow_sensor import SungrowSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up Modbus sensors from a config entry."""
    controller: ModbusController = get_controller_from_entry(hass, config_entry)
    sensor_entities: list[SungrowSensor] = []
    sensor_derived_entities: list[SensorEntity] = []
    hass.data[DOMAIN].setdefault(VALUES, {})

    for sensor_group in controller.sensor_groups:
        for sensor in sensor_group.sensors:
            if sensor.name != "reserve":
                sensor_entities.append(SungrowSensor(hass, sensor))

    for sensor in controller.derived_sensors:
        sensor_derived_entities.append(SungrowDerivedSensor(hass, sensor))

    # Namespace by entry_id to support multi-inverter setups
    hass.data[DOMAIN].setdefault(SENSOR_ENTITIES, {})
    hass.data[DOMAIN].setdefault(SENSOR_DERIVED_ENTITIES, {})
    hass.data[DOMAIN][SENSOR_ENTITIES][config_entry.entry_id] = sensor_entities
    hass.data[DOMAIN][SENSOR_DERIVED_ENTITIES][config_entry.entry_id] = sensor_derived_entities

    async_add_entities(sensor_entities, True)
    async_add_entities(sensor_derived_entities, True)

    # Set up battery stack sensors if multi-battery is enabled
    battery_controllers = hass.data[DOMAIN].get(BATTERY_CONTROLLER, {}).get(config_entry.entry_id)
    if battery_controllers:
        from custom_components.sungrow_modbus.sensors.sungrow_battery_sensor import create_battery_sensors

        status_sensors, diagnostic_sensors = create_battery_sensors(hass, battery_controllers)

        # Store for later access (e.g., by data retrieval)
        hass.data[DOMAIN].setdefault(BATTERY_SENSORS, {})
        hass.data[DOMAIN][BATTERY_SENSORS][config_entry.entry_id] = status_sensors

        async_add_entities(status_sensors, True)
        async_add_entities(diagnostic_sensors, True)

        _LOGGER.info(
            "Added %d battery sensors for %d stack(s)",
            len(status_sensors) + len(diagnostic_sensors),
            len(battery_controllers),
        )

    @callback
    def update(now):
        """Update Modbus data periodically."""

    return True
