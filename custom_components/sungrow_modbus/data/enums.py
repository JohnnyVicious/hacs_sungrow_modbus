from enum import Enum


class PollSpeed(Enum):
    ONCE = "once"
    STARTUP = "startup"
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"

class InverterType(Enum):
    HYBRID = "hybrid"
    STRING = "string"
    GRID = "grid"
    ENERGY = "energy"
    WAVESHARE = "waveshare"

class InverterFeature(Enum):
    PV = "pv"
    BMS = "bms"
    SMART_PORT = "smart_port"
    BATTERY = "battery"
    GRID = "grid"
    V2 = "v2"
    TCP = "tcp"
    HV_BATTERY = "high_voltage_battery"
    LV_BATTERY = "low_voltage_battery"
    ZONNEPLAN = "zonneplan"
    THREE_PHASE = "three_phase"
    MPPT3 = "mppt3"
    MULTI_BATTERY = "multi_battery"  # Multiple battery stacks (slave ID 200-203)
    BATTERY_DIRECT = "battery_direct"  # Direct battery communication available

class Category(Enum):
    BASIC_INFORMATION = "Basic Information"
    PV_INFORMATION = "PV Information"
    BATTERY_INFORMATION = "Battery Information"
    AC_INFORMATION = "AC Information"
    GRID_CODE_INFORMATION = "Grid Code Information"
    STATUS_INFORMATION = "Status Information"
    DEVICE_INTERNAL_DATA = "Device Internal Data"
    LOAD_INFORMATION = "Load Information"
    METER_INFORMATION = "Meter Information"
    OTHER_INFORMATION = "Other Information"
    FUNCTIONAL_INFORMATION = "Functional Information"
    HISTORICAL_DATA = "Historical Data"
    SMART_PORT_INFORMATION = "Smart port Information"
    ENERGY_DATA = "Energy Data"

    BASIC_SETTING = "Basic Setting"
    BATTERY_SETTING = "Battery Setting"
    AC_PORT_SETTING = "AC Port Setting"
    GRID_CODE_SETTING = "Grid Code Setting"
    POWER_CONTROL_SETTING = "Power Control Setting"
    FUNCTIONAL_SETTING = "Functional Setting"
    HYBRID_MODE_SETTING = "Hybrid Mode Setting"
    BACKUP_PORT_SETTING = "Backup Port Setting"
    REMOTE_CONTROL_SETTING = "Remote Control Setting"
    SMART_PORT_SETTING = "Smart port Setting"
    HISTORY_DATA_QUERY_SETTING = "History Data Query Setting"
    REMOTE_DISPATCH_SETTING = "Remote Dispatch Setting"