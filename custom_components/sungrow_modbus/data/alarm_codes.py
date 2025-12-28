"""
Sungrow inverter alarm and fault code mappings.

Sources:
- Sungrow Modbus Protocol Appendix 3
- SunGather registers-sungrow.yaml
- https://solaranalytica.com/sungrow-alarm-codes/

Codes are organized by series/category for maintainability.
"""


# =============================================================================
# ALARM CODE MAPPING
# Organized by code series for different inverter types and subsystems
# =============================================================================

ALARM_CODES = {
    # =========================================================================
    # 0xx Series - Single-Phase & Three-Phase Inverters (Grid/PV faults)
    # =========================================================================
    2: "Grid over-voltage",
    3: "Transient over-voltage",
    4: "Grid under-voltage",
    5: "Grid under-voltage (lower threshold)",
    6: "AC over-current",
    7: "Transient AC overcurrent",
    8: "Grid over-frequency",
    9: "Grid under-frequency",
    10: "Grid failure (Islanding)",
    11: "DC injection over-current",
    12: "Leakage current over-current",
    13: "Grid abnormal",
    14: "10-minute grid over-voltage",
    15: "Grid over-voltage (higher threshold)",
    16: "Bus voltage/power high",
    17: "Grid voltage unbalance",
    19: "Bus transient over-voltage",
    20: "Bus over-voltage",
    21: "PV1 input over-current",
    22: "PV2 input over-current",
    24: "Neutral point voltage imbalance",
    28: "PV1 reverse connection",
    29: "PV2 reverse connection",
    36: "Radiator temperature too high",
    37: "Internal inverter temperature too high",
    38: "Relay fault (grid side)",
    39: "Low PV insulation resistance",
    41: "Leakage current sampling fault",
    43: "Inner under-temperature fault",
    44: "Inverter self-test fault",
    45: "PV1 boost circuit fault",
    46: "PV2 boost circuit fault",
    47: "PV inputs error",
    48: "Phase current sampling fault",
    50: "Device abnormal",
    51: "Load overpower (off-grid mode)",
    52: "INV under-voltage (off-grid mode)",
    53: "Slave DSP: grid voltage exceeds limit",
    54: "Slave DSP: grid frequency exceeds limit",
    56: "Slave DSP: leakage current exceeds limit",
    59: "Master/slave DSP communication alarm",
    61: "No inverter model setting",
    62: "DI fault (backup box)",
    63: "CPLD version undetectable",
    64: "INV over-voltage (off-grid mode)",
    65: "INV under-frequency (off-grid mode)",
    66: "INV over-frequency (off-grid mode)",
    67: "Temporary grid over-voltage (off-grid)",
    70: "Fans defective",
    71: "SPD alarm AC",
    72: "SPD alarm DC",
    75: "RS485 communication error (parallel)",
    78: "PV1 string abnormal",
    79: "PV2 string abnormal",
    83: "Fan2 abnormal speed warning",
    84: "Energy Meter reverse cable warning",
    85: "Mismatched software version",
    87: "AFCI abnormal",
    88: "Arc fault",
    89: "AFCI function disabled",
    # =========================================================================
    # 1xx Series - AC Output and Grid Faults
    # =========================================================================
    100: "AC output current exceeds limit",
    101: "Grid over-frequency (higher threshold)",
    102: "Grid under-frequency (lower threshold)",
    105: "SPI auto test fault",
    106: "Abnormal grounding",
    107: "DC injection over-voltage (off-grid)",
    113: "Temporary bypass overcurrent",
    116: "Device abnormal",
    117: "Device abnormal",
    # =========================================================================
    # 2xx Series - Bus and PV Hardware Faults
    # =========================================================================
    200: "Bus hardware over-voltage fault",
    201: "Bus voltage too low",
    202: "PV hardware over-current fault",
    203: "PV input voltage exceeds bus voltage",
    204: "PV1 boost short-circuit fault",
    205: "PV2 boost short-circuit fault",
    # =========================================================================
    # 3xx Series - System and Sampling Faults
    # =========================================================================
    300: "INV over-temperature fault",
    302: "PV insulation resistance fault",
    303: "Bypass relay fault",
    304: "Off-grid relay fault",
    306: "Input/output power mismatching",
    308: "Slave DSP redundant fault",
    309: "Phase voltage sampling fault",
    312: "DC injection sampling fault",
    315: "PV1 current sampling fault",
    316: "PV2 current sampling fault",
    317: "PV1 MPPT current sampling fault",
    318: "PV2 MPPT current sampling fault",
    319: "System power supply failure",
    320: "Leakage current sensor fault",
    321: "SPI communication failure",
    322: "Master DSP communication fault",
    # =========================================================================
    # 4xx Series - Permanent Faults and Grid Issues
    # =========================================================================
    401: "Grid frequency too high",
    402: "Grid frequency too low",
    403: "Grid voltage too high",
    404: "Grid voltage too low",
    405: "No utility",
    406: "Permanent fault",
    407: "Permanent fault",
    408: "Permanent fault",
    409: "All temperature sensors fail",
    432: "PID resistance abnormal",
    433: "PID function abnormal",
    434: "PID overvoltage/overcurrent protection",
    # =========================================================================
    # 5xx Series - Sensor and String Faults
    # =========================================================================
    501: "FRAM1 reading warning",
    503: "Ambient temperature sensor open circuit",
    504: "Ambient temperature sensor short circuit",
    505: "Radiator temperature sensor open circuit",
    506: "Radiator temperature sensor short circuit",
    507: "Error alarm: DO power settings",
    509: "Clock reset fault",
    510: "PV over-voltage fault",
    511: "Ambient temperature sensor open circuit",
    513: "Fan1 abnormal speed warning",
    514: "Energy Meter communication warning",
    532: "String 1 reverse connection",
    533: "String 2 reverse connection",
    534: "String 3 reverse connection",
    535: "String 4 reverse connection",
    548: "Abnormal PV string 1 current",
    549: "Abnormal PV string 2 current",
    550: "Abnormal PV string 3 current",
    551: "Abnormal PV string 4 current",
    # =========================================================================
    # 6xx Series - Single-Phase Hybrid BDC Faults
    # =========================================================================
    600: "Temporary BDC charging over-current",
    601: "Temporary BDC discharging over-current",
    602: "Clamping capacitor under-voltage",
    603: "Temporary clamping capacitor over-voltage",
    608: "BDC circuit self-check fault",
    612: "BDC over-temperature fault",
    616: "BDC hardware over-current",
    620: "BDC current sampling fault",
    623: "Slave DSP communication fault",
    624: "BDC soft-start fault",
    # =========================================================================
    # 7xx Series - Battery Side Faults (Single-Phase Hybrid)
    # =========================================================================
    703: "Battery average under-voltage fault",
    707: "Battery over-temperature fault",
    708: "Battery under-temperature fault",
    711: "Instantaneous battery over-voltage",
    712: "Battery average over-voltage fault",
    714: "Abnormal battery-inverter communication",
    715: "Battery hardware over-voltage fault",
    732: "Battery over-voltage protection",
    733: "Battery over-temperature protection",
    734: "Battery under-temperature protection",
    735: "Battery charging/discharging over-current",
    739: "Battery under-voltage protection",
    # =========================================================================
    # 8xx Series - Permanent BDC and Battery Faults
    # =========================================================================
    800: "BDC internal permanent fault",
    802: "BDC internal permanent fault",
    804: "BDC internal permanent fault",
    807: "BDC internal permanent fault",
    832: "Battery FET fault/electrical switch failure",
    834: "Battery charging/discharging over-current (permanent)",
    836: "ID competing failure",
    839: "Mismatched software version",
    844: "Software self-verifying failure",
    864: "Battery cell over-voltage fault",
    866: "Battery pre-charge voltage fault",
    867: "Battery under-voltage fault",
    868: "Battery cell voltage imbalance",
    870: "Battery cable connection fault",
    # =========================================================================
    # 9xx Series - Warnings (BDC and Battery)
    # =========================================================================
    900: "BDC temperature sensor warning",
    901: "BDC temperature sensor warning",
    906: "Transformer direction recognition error",
    909: "Low SOH (State of Health) warning",
    910: "FRAM2 warning",
    932: "Battery over-voltage warning",
    933: "Battery over-temperature warning",
    934: "Battery under-temperature warning",
    935: "Battery charging/discharging over-current warning",
    937: "Battery tray voltage imbalance warning",
    939: "Battery under-voltage warning",
    964: "Battery internal warning",
    # =========================================================================
    # Three-Phase Hybrid Specific Codes (overlapping with 0xx but different meaning)
    # These are used when detected on three-phase hybrid inverters
    # =========================================================================
    # Note: Three-phase hybrids may use different code meanings
    # The base 0xx codes above are generally applicable
    # =========================================================================
    # 41xx Series - Extended Fault Codes (from status_mapping.py)
    # =========================================================================
    4100: "Control off-Grid",
    4110: "Grid overvoltage",
    4111: "Grid undervoltage",
    4112: "Grid overfrequency",
    4113: "Grid underfrequency",
    4114: "Grid impedance is too large",
    4115: "No Grid",
    4116: "Grid imbalance",
    4117: "Grid frequency jitter",
    4118: "Grid overcurrent",
    4119: "Grid current tracking fault",
    4120: "DC overvoltage",
    4121: "DC bus overvoltage",
    4122: "DC busbar uneven voltage",
    4123: "DC bus undervoltage",
    4124: "DC busbar uneven voltage 2",
    4125: "DC A way overcurrent",
    4126: "DC B path overcurrent",
    4127: "DC input disturbance",
    4130: "Grid disturbance",
    4131: "DSP initialization malfunction protection",
    4132: "Temperature protection",
    4133: "Ground protection",
    4134: "Leakage current fault",
    4135: "Relay failure",
    4136: "DSP_B failure protection",
    4137: "DC component is too large",
    4138: "12V undervoltage fault protection",
    4139: "Leakage current self-test protection",
    4140: "Under temperature protection",
    4141: "Arc self-test protection",
    4142: "Arc malfunction protection",
    4143: "DSP on-chip SRAM exception",
    4144: "DSP on-chip FLASH exception",
    4145: "DSP on-chip PC pointer is abnormal",
    4146: "DSP key register exception",
    4147: "Grid disturbance 02",
    4148: "Grid current sampling abnormality",
    4149: "IGBT overcurrent",
    4150: "Network side current transient",
    4151: "Battery overvoltage hardware failure",
    4152: "LLC hardware overcurrent",
    4153: "Battery overvoltage detection",
    4154: "Battery undervoltage detection",
    4155: "Battery not connected",
    4156: "Bypass overvoltage fault",
    4157: "Bypass overload fault",
}


# =============================================================================
# RUNNING STATE CODES
# =============================================================================

RUNNING_STATE_CODES = {
    0x0000: "Run",
    0x8000: "Stop",
    0x1300: "Key Stop",
    0x1500: "Emergency Stop",
    0x1400: "Standby",
    0x1200: "Initial Standby",
    0x1600: "Starting",
    0x9100: "Alarm Run",
    0x8100: "Derating Run",
    0x8200: "Dispatch Run",
    0x5500: "Fault",
    0x2500: "Communication Fault",
    # Numeric equivalents for work_state_2 (note: 0 is same as 0x0000, already defined above)
    1: "Stop",
    2: "Initial Standby",
    3: "Key Stop",
    4: "Standby",
    5: "Emergency Stop",
    6: "Starting",
    9: "Fault",
    10: "Alarm Run",
    11: "Derating Run",
    12: "Dispatch Run",
    13: "Communication Fault",
    17: "Total Run Bit",
    18: "Total Fault Bit",
}


# =============================================================================
# SYSTEM STATE CODES (Hybrid Inverters)
# =============================================================================

SYSTEM_STATE_CODES = {
    0x0002: "Stop",
    0x0008: "Standby",
    0x0010: "Initial Standby",
    0x0020: "Starting",
    0x0040: "Running",
    0x0100: "Fault",
    0x0400: "Maintain Run",
    0x0800: "Forced Mode Run",
    0x1000: "Off-grid Run",
    0x2501: "Off-grid Charge",
    0x4001: "EMS Run",
}


# =============================================================================
# PID STATE CODES
# =============================================================================

PID_STATE_CODES = {
    2: "PID Recover Operation",
    4: "Anti-PID Operation",
    8: "PID Abnormity",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_alarm_description(code: int) -> str:
    """
    Get human-readable description for an alarm code.

    Args:
        code: Numeric alarm code

    Returns:
        Description string, or "Unknown alarm (XXX)" if not found
    """
    if code == 0:
        return "No alarm"
    return ALARM_CODES.get(code, f"Unknown alarm ({code})")


def get_running_state(code: int) -> str:
    """
    Get human-readable description for a running state code.

    Args:
        code: Numeric state code

    Returns:
        Description string, or "Unknown state (XXX)" if not found
    """
    return RUNNING_STATE_CODES.get(code, f"Unknown state ({code})")


def get_system_state(code: int) -> str:
    """
    Get human-readable description for a system state code.

    Args:
        code: Numeric system state code

    Returns:
        Description string, or "Unknown state (0xXXXX)" if not found
    """
    return SYSTEM_STATE_CODES.get(code, f"Unknown state (0x{code:04X})")


def get_pid_state(code: int) -> str:
    """
    Get human-readable description for a PID state code.

    Args:
        code: Numeric PID state code

    Returns:
        Description string, or "Unknown PID state (XXX)" if not found
    """
    if code == 0:
        return "Normal"
    return PID_STATE_CODES.get(code, f"Unknown PID state ({code})")


def is_fault_code(code: int) -> bool:
    """
    Check if an alarm code represents a fault (vs warning).

    Faults are generally:
    - Codes ending in 00-99 in the 2xx, 3xx, 4xx, 6xx, 8xx series
    - Codes with "fault" in their description

    Args:
        code: Numeric alarm code

    Returns:
        True if the code represents a fault, False otherwise
    """
    if code == 0:
        return False

    description = ALARM_CODES.get(code, "").lower()
    if "fault" in description or "permanent" in description:
        return True

    # Fault series: 2xx, 3xx, 4xx (except 4xx warnings), 6xx, 8xx
    series = code // 100
    return series in [2, 3, 6, 8] or (series == 4 and code < 500)
