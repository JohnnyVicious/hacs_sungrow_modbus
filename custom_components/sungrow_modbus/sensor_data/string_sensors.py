from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)

from custom_components.sungrow_modbus.data.enums import Category, InverterFeature, PollSpeed

# Sungrow String Inverter Modbus Registers
# Based on: SunGather registers-sungrow.yaml and Sungrow communication protocols
# String inverters (SG-series) use different register addresses than hybrid (SH-series)
# for AC output currents, total power, grid frequency, and work state

string_sensors = [
    # ==================== DEVICE INFORMATION (Input Registers 4989-5000) ====================
    {
        "register_start": 4989,
        "poll_speed": PollSpeed.ONCE,
        "entities": [
            {
                "name": "Inverter Serial",
                "unique": "sungrow_modbus_inverter_serial",
                "category": Category.BASIC_INFORMATION,
                "register": ["4989", "4990", "4991", "4992", "4993", "4994", "4995", "4996", "4997", "4998"],
                "multiplier": 0,  # String type
            },
        ],
    },
    {
        "register_start": 4999,
        "poll_speed": PollSpeed.ONCE,
        "entities": [
            {
                "name": "Device Type Code",
                "unique": "sungrow_modbus_device_type_code",
                "category": Category.BASIC_INFORMATION,
                "register": ["4999"],
                "multiplier": 1,
            },
        ],
    },
    # ==================== NOMINAL POWER (Input Registers 5000-5001) ====================
    {
        "register_start": 5000,
        "poll_speed": PollSpeed.ONCE,
        "entities": [
            {
                "name": "Nominal Active Power",
                "unique": "sungrow_modbus_nominal_active_power",
                "category": Category.BASIC_INFORMATION,
                "register": ["5000"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.POWER,
                "unit_of_measurement": UnitOfPower.KILO_WATT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {"type": "reserve", "register": ["5001"]},
        ],
    },
    # ==================== PV GENERATION SUMMARY (Input Registers 5002-5008) ====================
    {
        "register_start": 5002,
        "poll_speed": PollSpeed.SLOW,
        "feature_requirement": [InverterFeature.PV],
        "entities": [
            {
                "name": "Daily PV Generation",
                "unique": "sungrow_modbus_daily_pv_generation",
                "category": Category.PV_INFORMATION,
                "register": ["5002"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.ENERGY,
                "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            {
                "name": "Total PV Generation",
                "unique": "sungrow_modbus_total_pv_generation",
                "category": Category.PV_INFORMATION,
                "register": ["5003", "5004"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.ENERGY,
                "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
                "state_class": SensorStateClass.TOTAL,
            },
            {"type": "reserve", "register": ["5005", "5006"]},
            {
                "name": "Inverter Temperature",
                "unique": "sungrow_modbus_inverter_temperature",
                "category": Category.BASIC_INFORMATION,
                "register": ["5007"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit_of_measurement": UnitOfTemperature.CELSIUS,
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
        ],
    },
    # ==================== MPPT DATA (Input Registers 5011-5018) ====================
    # MPPT1 and MPPT2 - All PV inverters have at least 2 MPPTs
    {
        "register_start": 5011,
        "poll_speed": PollSpeed.FAST,
        "feature_requirement": [InverterFeature.PV],
        "entities": [
            {
                "name": "MPPT1 Voltage",
                "unique": "sungrow_modbus_mppt1_voltage",
                "category": Category.PV_INFORMATION,
                "register": ["5011"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {
                "name": "MPPT1 Current",
                "unique": "sungrow_modbus_mppt1_current",
                "category": Category.PV_INFORMATION,
                "register": ["5012"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {
                "name": "MPPT2 Voltage",
                "unique": "sungrow_modbus_mppt2_voltage",
                "category": Category.PV_INFORMATION,
                "register": ["5013"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {
                "name": "MPPT2 Current",
                "unique": "sungrow_modbus_mppt2_current",
                "category": Category.PV_INFORMATION,
                "register": ["5014"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # MPPT3 - Only for larger inverters with MPPT3 feature
    {
        "register_start": 5015,
        "poll_speed": PollSpeed.FAST,
        "feature_requirement": [InverterFeature.PV, InverterFeature.MPPT3],
        "entities": [
            {
                "name": "MPPT3 Voltage",
                "unique": "sungrow_modbus_mppt3_voltage",
                "category": Category.PV_INFORMATION,
                "register": ["5015"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {
                "name": "MPPT3 Current",
                "unique": "sungrow_modbus_mppt3_current",
                "category": Category.PV_INFORMATION,
                "register": ["5016"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # Total DC Power - All PV inverters
    {
        "register_start": 5017,
        "poll_speed": PollSpeed.FAST,
        "feature_requirement": [InverterFeature.PV],
        "entities": [
            {
                "name": "Total DC Power",
                "unique": "sungrow_modbus_total_dc_power",
                "category": Category.PV_INFORMATION,
                "register": ["5017", "5018"],
                "multiplier": 1,
                "device_class": SensorDeviceClass.POWER,
                "unit_of_measurement": UnitOfPower.WATT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # ==================== AC OUTPUT VOLTAGES (Input Registers 5018-5020) ====================
    # Phase A - All inverters
    {
        "register_start": 5018,
        "poll_speed": PollSpeed.FAST,
        "entities": [
            {
                "name": "Phase A Voltage",
                "unique": "sungrow_modbus_phase_a_voltage",
                "category": Category.AC_INFORMATION,
                "register": ["5018"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # Phase B and C - Only three-phase inverters
    {
        "register_start": 5019,
        "poll_speed": PollSpeed.FAST,
        "feature_requirement": [InverterFeature.THREE_PHASE],
        "entities": [
            {
                "name": "Phase B Voltage",
                "unique": "sungrow_modbus_phase_b_voltage",
                "category": Category.AC_INFORMATION,
                "register": ["5019"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            {
                "name": "Phase C Voltage",
                "unique": "sungrow_modbus_phase_c_voltage",
                "category": Category.AC_INFORMATION,
                "register": ["5020"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit_of_measurement": UnitOfElectricPotential.VOLT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # ==================== AC OUTPUT CURRENTS (Input Registers 5022-5024) ====================
    # STRING INVERTER SPECIFIC - Different from hybrid which uses 13030-13032
    # Phase A Current - All inverters
    {
        "register_start": 5022,
        "poll_speed": PollSpeed.FAST,
        "entities": [
            {
                "name": "Phase A Current",
                "unique": "sungrow_modbus_phase_a_current",
                "category": Category.AC_INFORMATION,
                "register": ["5022"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
        ],
    },
    # Phase B and C Current - Only three-phase inverters
    {
        "register_start": 5023,
        "poll_speed": PollSpeed.FAST,
        "feature_requirement": [InverterFeature.THREE_PHASE],
        "entities": [
            {
                "name": "Phase B Current",
                "unique": "sungrow_modbus_phase_b_current",
                "category": Category.AC_INFORMATION,
                "register": ["5023"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
            {
                "name": "Phase C Current",
                "unique": "sungrow_modbus_phase_c_current",
                "category": Category.AC_INFORMATION,
                "register": ["5024"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
        ],
    },
    # ==================== TOTAL ACTIVE POWER (Input Registers 5031-5032) ====================
    # STRING INVERTER SPECIFIC - Different from hybrid which uses 13033-13034
    {
        "register_start": 5031,
        "poll_speed": PollSpeed.FAST,
        "entities": [
            {
                "name": "Total Active Power",
                "unique": "sungrow_modbus_total_active_power",
                "category": Category.AC_INFORMATION,
                "register": ["5031", "5032"],
                "multiplier": 1,
                "device_class": SensorDeviceClass.POWER,
                "unit_of_measurement": UnitOfPower.WATT,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # ==================== REACTIVE POWER AND POWER FACTOR (Input Registers 5033-5035) ====================
    {
        "register_start": 5033,
        "poll_speed": PollSpeed.FAST,
        "entities": [
            {
                "name": "Reactive Power",
                "unique": "sungrow_modbus_reactive_power",
                "category": Category.AC_INFORMATION,
                "register": ["5033", "5034"],
                "multiplier": 1,
                "device_class": SensorDeviceClass.REACTIVE_POWER,
                "unit_of_measurement": "var",
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
            {
                "name": "Power Factor",
                "unique": "sungrow_modbus_power_factor",
                "category": Category.AC_INFORMATION,
                "register": ["5035"],
                "multiplier": 0.001,
                "device_class": SensorDeviceClass.POWER_FACTOR,
                "unit_of_measurement": PERCENTAGE,
                "state_class": SensorStateClass.MEASUREMENT,
                "signed": True,
            },
        ],
    },
    # ==================== GRID FREQUENCY (Input Register 5036) ====================
    # STRING INVERTER SPECIFIC - Different from hybrid which uses 5241
    {
        "register_start": 5036,
        "poll_speed": PollSpeed.NORMAL,
        "entities": [
            {
                "name": "Grid Frequency",
                "unique": "sungrow_modbus_grid_frequency",
                "category": Category.GRID_CODE_INFORMATION,
                "register": ["5036"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.FREQUENCY,
                "unit_of_measurement": UnitOfFrequency.HERTZ,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # ==================== WORK STATE (Input Register 5038) ====================
    # STRING INVERTER SPECIFIC - Different from hybrid which uses 12999-13000
    {
        "register_start": 5038,
        "poll_speed": PollSpeed.NORMAL,
        "entities": [
            {
                "name": "Work State",
                "unique": "sungrow_modbus_work_state",
                "category": Category.STATUS_INFORMATION,
                "register": ["5038"],
                "multiplier": 1,
                "value_mapping": "running_state",
            },
        ],
    },
    # ==================== FAULT CODES (Input Register 5045) ====================
    {
        "register_start": 5045,
        "poll_speed": PollSpeed.NORMAL,
        "entities": [
            {
                "name": "Fault Code",
                "unique": "sungrow_modbus_fault_code",
                "category": Category.STATUS_INFORMATION,
                "register": ["5045"],
                "multiplier": 1,
                "value_mapping": "alarm",
            },
        ],
    },
    # ==================== NOMINAL REACTIVE POWER (Input Register 5049) ====================
    {
        "register_start": 5049,
        "poll_speed": PollSpeed.ONCE,
        "entities": [
            {
                "name": "Nominal Reactive Power",
                "unique": "sungrow_modbus_nominal_reactive_power",
                "category": Category.BASIC_INFORMATION,
                "register": ["5049"],
                "multiplier": 0.1,
                "device_class": SensorDeviceClass.REACTIVE_POWER,
                "unit_of_measurement": "kvar",
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
    # ==================== ARRAY INSULATION RESISTANCE (Input Register 5071) ====================
    {
        "register_start": 5071,
        "poll_speed": PollSpeed.SLOW,
        "feature_requirement": [InverterFeature.PV],
        "entities": [
            {
                "name": "Array Insulation Resistance",
                "unique": "sungrow_modbus_array_insulation_resistance",
                "category": Category.PV_INFORMATION,
                "register": ["5071"],
                "multiplier": 1,
                "unit_of_measurement": "kΩ",
                "state_class": SensorStateClass.MEASUREMENT,
            },
        ],
    },
]

# Derived sensors (calculated from other sensor values)
string_sensors_derived = []
