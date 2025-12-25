from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfPower, UnitOfEnergy,
    UnitOfFrequency, UnitOfTemperature, PERCENTAGE
)

from custom_components.sungrow_modbus.data.enums import PollSpeed, InverterFeature, Category

# Sungrow String Inverter Modbus Registers
# Note: Sungrow SHx hybrid inverters use the registers defined in hybrid_sensors.py
# This file is reserved for future string-only (non-hybrid) inverter support

string_sensors = []

# Derived sensors (calculated from other sensor values)
string_sensors_derived = []
