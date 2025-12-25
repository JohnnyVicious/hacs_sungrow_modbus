"""
Model-specific register overrides for Sungrow inverters.

This module allows overriding base sensor definitions for specific models.
Different Sungrow models and firmware versions may have registers at different
addresses or with different scaling factors.

Usage:
    The override system works by matching model names and applying patches
    to the base sensor definitions at runtime.

Override Structure:
    Each override entry can specify:
    - "register": New register address(es)
    - "multiplier": Different scaling factor
    - "signed": Whether the value is signed
    - "disabled": True to disable this sensor for this model
    - Any other sensor property to override

Example:
    MODEL_OVERRIDES = {
        "SH25T": {
            "sensors": {
                "sungrow_modbus_nominal_power": {
                    "register": ['5001'],  # Different register for this model
                },
                "sungrow_modbus_some_sensor": {
                    "disabled": True,  # Not available on this model
                },
            },
            "additional_sensors": [
                # Extra sensors only available on this model
                {
                    "name": "Model Specific Sensor",
                    "unique": "sungrow_modbus_model_specific",
                    "register": ['9999'],
                    ...
                }
            ]
        }
    }
"""

from typing import Dict, List, Any, Optional
import copy
import logging

_LOGGER = logging.getLogger(__name__)


# Model override definitions
# Key: Model name (or pattern like "SH*T" for wildcards)
# Value: Override configuration
MODEL_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # ==========================================================================
    # SH25T overrides based on live device testing (2024-12)
    # Tested via WiNet-S dongle at 192.168.11.6
    # The SH25T has registers offset by -1 compared to residential SH-RT series
    # ==========================================================================
    "SH25T": {
        "description": "SH25T specific overrides based on live device testing",
        "sensors": {
            # MPPT registers are at -1 offset on SH25T
            # Base: 5011-5012, SH25T: 5010-5011
            "sungrow_modbus_mppt1_voltage": {
                "register": ['5010'],
            },
            "sungrow_modbus_mppt1_current": {
                "register": ['5011'],
            },
            "sungrow_modbus_mppt2_voltage": {
                "register": ['5012'],
            },
            "sungrow_modbus_mppt2_current": {
                "register": ['5013'],
            },
            "sungrow_modbus_mppt3_voltage": {
                "register": ['5014'],
            },
            "sungrow_modbus_mppt3_current": {
                "register": ['5015'],
            },
            "sungrow_modbus_total_dc_power": {
                "register": ['5016', '5017'],
            },

            # Daily/Total PV at -1 offset on SH25T
            # Live test: 13001 = 18.7 kWh (daily), 13002 = 1569.1 kWh (total)
            "sungrow_modbus_daily_pv_energy": {
                "register": ['13001'],
            },
            "sungrow_modbus_total_pv_energy": {
                "register": ['13002', '13003'],
            },

            # Battery registers at -1 offset on SH25T
            # Live test confirmed: 13022 = SOC, 13023 = SOH
            "sungrow_modbus_battery_voltage": {
                "register": ['13019'],
            },
            "sungrow_modbus_battery_current": {
                "register": ['13020'],
            },
            "sungrow_modbus_battery_power": {
                "register": ['13021'],
            },
            "sungrow_modbus_battery_level": {
                "register": ['13022'],
            },
            "sungrow_modbus_battery_soh": {
                "register": ['13023'],
            },
            "sungrow_modbus_battery_temperature": {
                "register": ['13024'],
            },
            "sungrow_modbus_daily_battery_discharge": {
                "register": ['13025'],
            },
            "sungrow_modbus_total_battery_discharge": {
                "register": ['13026', '13027'],
            },
        },
    },

    # ==========================================================================
    # SH-T series (larger three-phase hybrids: SH5T, SH6T, SH8T, SH10T, etc.)
    # These may share similar register maps with SH25T
    # ==========================================================================
    "SH*T": {
        "description": "SH-T series base overrides",
        "sensors": {
            # T-series typically uses same register layout
        },
    },

    # ==========================================================================
    # SH-RT series (three-phase residential hybrid)
    # ==========================================================================
    # "SH*RT*": {
    #     "description": "SH-RT series overrides",
    #     "sensors": {},
    # },

    # ==========================================================================
    # SH-RS series (single-phase residential hybrid)
    # ==========================================================================
    # "SH*RS": {
    #     "description": "SH-RS series overrides",
    #     "sensors": {},
    # },
}


def _match_model(model: str, pattern: str) -> bool:
    """
    Check if a model name matches a pattern.

    Supports:
    - Exact match: "SH25T" matches "SH25T"
    - Wildcard: "SH*T" matches "SH25T", "SH10T", etc.
    - Prefix: "SH*" matches any model starting with "SH"
    """
    if '*' not in pattern:
        return model == pattern

    # Simple wildcard matching
    parts = pattern.split('*')
    if len(parts) == 2:
        prefix, suffix = parts
        return model.startswith(prefix) and model.endswith(suffix)
    elif len(parts) == 1:
        return model.startswith(parts[0])
    else:
        # Multiple wildcards - use more complex matching
        import fnmatch
        return fnmatch.fnmatch(model, pattern)


def get_model_overrides(model: str) -> Optional[Dict[str, Any]]:
    """
    Get override configuration for a specific model.

    Args:
        model: The inverter model name (e.g., "SH25T", "SH10RT")

    Returns:
        Override configuration dict, or None if no overrides exist.
        If multiple patterns match, they are merged (later patterns override earlier).
    """
    merged_overrides: Dict[str, Any] = {}

    for pattern, overrides in MODEL_OVERRIDES.items():
        if _match_model(model, pattern):
            _LOGGER.debug(f"Model {model} matches override pattern {pattern}")
            # Deep merge the overrides
            _deep_merge(merged_overrides, overrides)

    return merged_overrides if merged_overrides else None


def _deep_merge(base: Dict, overlay: Dict) -> Dict:
    """Deep merge overlay into base dict, modifying base in place."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def apply_model_overrides(
    sensor_groups: List[Dict[str, Any]],
    model: str
) -> List[Dict[str, Any]]:
    """
    Apply model-specific overrides to sensor group definitions.

    Args:
        sensor_groups: The base sensor group definitions
        model: The inverter model name

    Returns:
        Modified sensor groups with overrides applied
    """
    overrides = get_model_overrides(model)
    if not overrides:
        return sensor_groups

    _LOGGER.info(f"Applying model overrides for {model}")

    # Deep copy to avoid modifying the original
    modified_groups = copy.deepcopy(sensor_groups)

    # Get sensor-specific overrides
    sensor_overrides = overrides.get("sensors", {})

    # Apply overrides to each sensor
    for group in modified_groups:
        entities = group.get("entities", [])
        filtered_entities = []

        for entity in entities:
            unique_id = entity.get("unique", "")

            if unique_id in sensor_overrides:
                override = sensor_overrides[unique_id]

                # Check if sensor should be disabled
                if override.get("disabled", False):
                    _LOGGER.debug(f"Disabling sensor {unique_id} for model {model}")
                    continue

                # Apply property overrides
                for key, value in override.items():
                    if key != "disabled":
                        _LOGGER.debug(f"Overriding {unique_id}.{key} = {value}")
                        entity[key] = value

            filtered_entities.append(entity)

        group["entities"] = filtered_entities

    # Add model-specific additional sensors
    additional = overrides.get("additional_sensors", [])
    if additional:
        # Add as a new sensor group
        modified_groups.append({
            "register_start": additional[0].get("register", ['0'])[0] if additional else 0,
            "poll_speed": additional[0].get("poll_speed", "NORMAL") if additional else "NORMAL",
            "entities": additional
        })

    return modified_groups


def apply_derived_overrides(
    derived_sensors: List[Dict[str, Any]],
    model: str
) -> List[Dict[str, Any]]:
    """
    Apply model-specific overrides to derived sensor definitions.

    Args:
        derived_sensors: The base derived sensor definitions
        model: The inverter model name

    Returns:
        Modified derived sensors with overrides applied
    """
    overrides = get_model_overrides(model)
    if not overrides:
        return derived_sensors

    # Deep copy to avoid modifying the original
    modified = copy.deepcopy(derived_sensors)

    # Get derived sensor overrides
    derived_overrides = overrides.get("derived_sensors", {})

    filtered = []
    for sensor in modified:
        unique_id = sensor.get("unique", "")

        if unique_id in derived_overrides:
            override = derived_overrides[unique_id]

            if override.get("disabled", False):
                _LOGGER.debug(f"Disabling derived sensor {unique_id} for model {model}")
                continue

            for key, value in override.items():
                if key != "disabled":
                    sensor[key] = value

        filtered.append(sensor)

    # Add model-specific additional derived sensors
    additional = overrides.get("additional_derived_sensors", [])
    filtered.extend(additional)

    return filtered


# Convenience function to get all overrides for debugging
def list_all_overrides() -> Dict[str, List[str]]:
    """List all model patterns and their override keys for debugging."""
    result = {}
    for pattern, overrides in MODEL_OVERRIDES.items():
        result[pattern] = list(overrides.get("sensors", {}).keys())
    return result
