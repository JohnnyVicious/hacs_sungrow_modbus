"""Battery sensor definitions for Sungrow multi-battery support.

These sensors are polled from battery stacks via slave IDs 200-203.
They provide higher-resolution data than the aggregate battery info
available from the inverter's own registers.

Note: These registers are only accessible via the inverter's direct LAN port,
not through WiNet-S which only exposes limited battery data on slave ID 2.
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfTemperature,
    UnitOfEnergy,
    PERCENTAGE,
)

from ..data.enums import PollSpeed, Category, InverterFeature


# Battery stack sensors (read from slave ID 200+)
# These are separate from inverter sensor groups and polled independently
battery_stack_sensors = [
    # Core battery status
    {
        "name": "Battery Stack Voltage",
        "unique": "battery_stack_voltage",
        "register": 10740,
        "multiplier": 0.1,
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit_of_measurement": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Current",
        "unique": "battery_stack_current",
        "register": 10741,
        "multiplier": 0.1,
        "signed": True,
        "device_class": SensorDeviceClass.CURRENT,
        "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Temperature",
        "unique": "battery_stack_temperature",
        "register": 10742,
        "multiplier": 0.1,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack SOC",
        "unique": "battery_stack_soc",
        "register": 10743,
        "multiplier": 0.1,  # 0.1% resolution - higher than inverter's 1%
        "device_class": SensorDeviceClass.BATTERY,
        "unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack SOH",
        "unique": "battery_stack_soh",
        "register": 10744,
        "multiplier": 1,
        "device_class": SensorDeviceClass.BATTERY,
        "unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    # Energy totals (32-bit registers)
    {
        "name": "Battery Stack Total Charge",
        "unique": "battery_stack_total_charge",
        "register": 10745,
        "register_count": 2,
        "multiplier": 0.1,
        "device_class": SensorDeviceClass.ENERGY,
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Total Discharge",
        "unique": "battery_stack_total_discharge",
        "register": 10747,
        "register_count": 2,
        "multiplier": 0.1,
        "device_class": SensorDeviceClass.ENERGY,
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "category": Category.BATTERY_INFORMATION,
    },
    # Cell voltage monitoring
    {
        "name": "Battery Stack Max Cell Voltage",
        "unique": "battery_stack_max_cell_voltage",
        "register": 10756,
        "multiplier": 0.0001,  # 0.1mV resolution
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit_of_measurement": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Max Cell Position",
        "unique": "battery_stack_max_cell_position",
        "register": 10757,
        "multiplier": 1,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Min Cell Voltage",
        "unique": "battery_stack_min_cell_voltage",
        "register": 10758,
        "multiplier": 0.0001,  # 0.1mV resolution
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit_of_measurement": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "category": Category.BATTERY_INFORMATION,
    },
    {
        "name": "Battery Stack Min Cell Position",
        "unique": "battery_stack_min_cell_position",
        "register": 10759,
        "multiplier": 1,
        "category": Category.BATTERY_INFORMATION,
    },
]

# Diagnostic sensors (read once at startup)
battery_stack_diagnostic_sensors = [
    {
        "name": "Battery Stack Serial Number",
        "unique": "battery_stack_serial",
        "register": 10710,
        "register_count": 10,
        "type": "string",
        "category": Category.BASIC_INFORMATION,
        "poll_speed": PollSpeed.ONCE,
    },
    {
        "name": "Battery Stack Firmware",
        "unique": "battery_stack_firmware",
        "register": 10720,
        "register_count": 10,
        "type": "string",
        "category": Category.BASIC_INFORMATION,
        "poll_speed": PollSpeed.ONCE,
    },
]


def get_battery_sensor_unique_id(sensor: dict, stack_index: int, inverter_serial: str) -> str:
    """Generate unique ID for a battery sensor.

    Args:
        sensor: Sensor definition dictionary
        stack_index: Battery stack index (0-3)
        inverter_serial: Parent inverter's serial number

    Returns:
        Unique ID string for the sensor entity
    """
    base_unique = sensor.get("unique", sensor.get("name", "unknown").lower().replace(" ", "_"))
    return f"sungrow_modbus_{inverter_serial}_battery_{stack_index}_{base_unique}"


def get_battery_sensor_name(sensor: dict, stack_index: int) -> str:
    """Generate display name for a battery sensor.

    Args:
        sensor: Sensor definition dictionary
        stack_index: Battery stack index (0-3)

    Returns:
        Display name string for the sensor entity
    """
    base_name = sensor.get("name", "Unknown")
    # Replace "Battery Stack" with "Battery Stack N"
    if "Battery Stack" in base_name:
        return base_name.replace("Battery Stack", f"Battery Stack {stack_index + 1}")
    return f"Battery Stack {stack_index + 1} {base_name}"
