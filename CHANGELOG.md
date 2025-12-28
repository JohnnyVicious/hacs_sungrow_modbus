# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Service writes to all controllers when host omitted** (`__init__.py:118-135`) - The `sungrow_write_holding_register` service ignored the `slave` parameter when `host` was not specified, writing to ALL registered controllers instead of filtering by slave ID. In multi-inverter setups, this could write values to unintended devices. Root cause: The else branch iterated through all controllers without filtering by `device_id`. Fixed by adding a filter `[c for c in controllers.values() if c.device_id == slave]` to target only controllers matching the specified slave ID.

- **Writes silently dropped when controller disconnected** (`sensors/sungrow_binary_sensor.py:157-163`, `sensors/sungrow_select_entity.py:160-163`) - When the controller was disconnected, switch toggles and select changes were silently dropped, but the entity's local state was still updated, giving users false confirmation that their action succeeded. Root cause: The `controller.connected()` check gated the write, but local state updates happened unconditionally afterward. Fixed by removing the connected check (controller handles connection state internally) and only updating local state when a write is actually queued.

- **Missing async_write_ha_state for connection toggle** (`sensors/sungrow_binary_sensor.py:74-78`) - The connection toggle entity (register 90005) updated its internal state but never pushed the update to Home Assistant, so the UI didn't reflect the actual enabled/disabled status until the next poll. Root cause: The early `return` for register 90005 bypassed the `async_write_ha_state()` call. Fixed by adding the call before the return.

## [0.3.0] - 2025-12-28

### Added

- **Data validation for sensor values** (`sensors/sungrow_base_sensor.py`, `sensors/sungrow_number_sensor.py`, `sensors/sungrow_select_entity.py`) - Added comprehensive validation for both read and write operations:
  - **Read validation**: Logs warnings when sensor values exceed expected bounds (e.g., temperature reading of 999°C is clearly wrong). Values are still displayed for debugging purposes.
  - **Write validation**: Blocks writes that exceed min/max bounds with `HomeAssistantError`, preventing invalid values from being sent to the inverter.
  - **Default bounds by unit type**: Automatic sensible defaults based on unit of measurement (e.g., percentages: 0-100, temperatures: -40 to 100°C, frequencies: 45-65Hz). Explicit min/max in sensor definitions override these defaults.
  - **Select entity validation**: Validates that selected options are valid and that on_values are within u16 register range (0-65535).

## [0.2.1] - 2025-12-28

### Fixed

- **KeyError in get_controller when service called during startup** (`helpers.py:200-229`, `helpers.py:192-197`) - `get_controller()` and `get_controller_from_entry()` accessed `hass.data[DOMAIN][CONTROLLER]` without checking if keys exist, causing `KeyError` if the write service was called before any controllers were registered (e.g., during HA startup or if integration failed to load). Fixed by using `hass.data.get(DOMAIN, {}).get(CONTROLLER, {})` to safely retrieve the controllers dict, returning `None` early if empty.

- **Emoji in error log message** (`sensors/sungrow_base_sensor.py:286`) - Removed emoji character from registrar sequence error log message. Emojis may not render correctly in all logging environments (journald, Docker logs, syslog).

- **Magic numbers in grid inverter offline handling** (`sensors/sungrow_sensor.py:92-100`) - Extracted hardcoded register values (3014, 3043) and shutdown state (2) into named constants `REGISTER_DAILY_ENERGY_GENERATION`, `REGISTER_GRID_RUNNING_STATE`, and `GRID_STATE_SHUTDOWN` for improved readability.

- **Magic numbers in battery power calculations** (`sensors/sungrow_derived_sensor.py:173-193`) - Extracted power scaling factor (10) and battery direction value (0) into named constants `POWER_SCALE_FACTOR` and `BATTERY_DIRECTION_CHARGING` for improved readability.

## [0.2.0] - 2025-12-28

### Fixed

#### Critical Fixes

- **Signed integer handling for single registers** (`sensors/sungrow_base_sensor.py`) - Single-register values with `signed: true` were displayed as large positive numbers instead of negative values (e.g., -5°C showed as 6553.1°C). Root cause: `SungrowBaseSensor.__init__()` never accepted or stored the `signed` parameter from sensor definitions. Fixed by adding `signed` parameter, storing it as an attribute, and applying U16→S16 conversion in `_convert_raw_value()` when the flag is set. Affects 30+ sensors including battery temperatures, internal temperatures, and signed power readings.

- **asyncio.Lock event loop binding** (`client_manager.py`) - Potential `RuntimeError` during Home Assistant startup when asyncio.Lock was bound to the wrong event loop. Root cause: locks were created immediately in `get_tcp_client()`/`get_serial_client()` which could be called from sync context or a different event loop during HA startup. Fixed by storing `None` initially and creating locks lazily in `get_client_lock()` on first access from the correct async context.

#### Important Fixes

- **Connection retry loop infinite loop** (`data_retrieval.py:110-134`) - Connection retry loop would run indefinitely if device was permanently offline, causing resource consumption and log spam. Root cause: `while not self.controller.connected()` loop had no exit condition. Fixed by adding `max_retries=20` limit (~10 minutes with exponential backoff) and logging a warning when exceeded. Connection reattempted on next `check_connection` cycle (2 min).

- **Exception logging at DEBUG level** (`data_retrieval.py:344-345`) - Exceptions during Modbus polling were logged at DEBUG level, hiding errors from users. Root cause: overly defensive `except Exception` block used `_LOGGER.debug()`. Fixed by upgrading to `_LOGGER.warning()` with `exc_info=True` for full stack traces.

- **Write queue no graceful shutdown** (`modbus_controller.py:132-179`) - Write queue processor ran `while True` without handling `CancelledError`, potentially leaving writes incomplete on shutdown. Root cause: no exception handling for task cancellation. Fixed by wrapping loop in try/except, catching `CancelledError`, draining pending writes, and re-raising for proper cleanup.

- **No validation for register writes** (`__init__.py:61-103`) - `sungrow_write_holding_register` service allowed writing to any register without warning about potentially dangerous addresses. Root cause: only basic 0-65535 range check existed. Fixed by adding `SAFE_HOLDING_REGISTER_RANGES` list and `_is_safe_register()` helper that logs a warning for writes outside known safe ranges (writes still proceed).

- **Direct controller state manipulation** (`data_retrieval.py:335-339`, `modbus_controller.py:518-533`) - `DataRetrieval` directly modified `controller._data_received` and `controller._sensor_groups` private attributes, violating encapsulation. Root cause: no public API existed. Fixed by adding `data_received` property, `mark_data_received()` method, and `remove_sensor_groups()` method to `ModbusController`, then updating `DataRetrieval` to use them.

- **Clock drift correction spam** (`helpers.py:46-96`) - Clock correction could spam writes if inverter RTC immediately drifted after correction. Root cause: no cooldown between corrections, only a drift counter that reset after each write. Fixed by adding `CLOCK_CORRECTION_COOLDOWN = 3600` (1 hour), tracking `LAST_CLOCK_CORRECTION` timestamp, and skipping corrections during cooldown.

### Changed

- **Removed duplicate TCP/Serial code** (`modbus_controller.py`) - Eliminated redundant if/else branching in 4 methods where TCP and Serial code paths were identical. Root cause: historical code from pymodbus 2.x migration where APIs differed. In pymodbus 3.x, both use the same `device_id` parameter. Affected methods: `_execute_write_holding_register`, `_execute_write_holding_registers`, `_async_read_input_register_raw`, `async_read_holding_register`.

#### Minor Fixes

- **Invalid type annotation syntax** (`data/sungrow_config.py:33`) - Static type checkers flagged `[InverterFeature]` as an error. Root cause: `[InverterFeature]` creates a list literal, not a type hint. Fixed by changing to `list[InverterFeature]`.

- **Magic register numbers without constants** (`sensors/sungrow_derived_sensor.py`) - Hardcoded register numbers (0, 1, 90006, 90007, 33095, 33135, 33263, etc.) made code hard to understand and maintain. Root cause: no named constants existed. Fixed by adding descriptive constants at the top of the file: `REGISTER_PLACEHOLDER_0`, `REGISTER_PLACEHOLDER_1`, `REGISTER_CLOCK_DRIFT`, `REGISTER_LAST_SUCCESS`, `REGISTER_RUNNING_STATUS`, `REGISTER_PROTOCOL_VERSION`, `REGISTERS_PHASE_POWER`, `REGISTERS_POWER_FACTOR`, `REGISTER_BATTERY_POWER`, `REGISTER_POWER_TO_GRID`, `REGISTER_POWER_FROM_GRID`, `REGISTER_SIGN_INVERSION`.

- **Empty callback function (dead code)** (`sensor.py:67-70`) - An unused `update()` callback function with empty body was defined but never called. Root cause: leftover from a previous implementation. Fixed by removing the dead code and the now-unused `callback` import.

- **Defensive code with unclear purpose** (`sensors/sungrow_derived_sensor.py:44-45`) - Unnecessary fallback `hass if hass else sensor.hass` when `hass` parameter is typed as `HomeAssistant` (not Optional). Root cause: historical usage patterns that no longer exist. Fixed by simplifying to direct assignment `self._hass = hass`.

- **Unhelpful unknown device type message** (`config_flow.py:307`) - Users with unrecognized device type codes saw only "Unknown (0x...)" without guidance. Root cause: fallback message didn't explain what to do. Fixed by logging a WARNING with the GitHub issues URL and updating the display message to prompt users to report the device type.

- **Inconsistent emoji usage in log messages** (multiple files) - Log messages used emojis inconsistently (✅, ❌, ⚠️) which may not render correctly in all environments. Root cause: no consistent logging style guide. Fixed by removing all emojis from log messages in `sungrow_base_sensor.py`, `modbus_controller.py`, `sungrow_sensor.py`, `__init__.py`, `time.py`, and `data_retrieval.py`.

## [0.1.15] - 2025-12-XX

### Fixed

- **Controller namespacing for multi-inverter** (`helpers.py`, `__init__.py`) - Events now emit the full `connection_id` and `is_correct_controller` matches on that key, preventing cross-talk between controllers on the same host but different ports/paths.

- **Config flow client leak** (`config_flow.py`) - Modbus clients were not closed when `_detect_device` failed, causing socket/handle leaks. Fixed by adding try/finally to ensure client.close() is always called.

- **Serial connection logging AttributeError** (`modbus_controller.py`) - Serial Modbus connections crashed when logging failures due to accessing non-existent `port` attribute. Fixed by using `connection_id` instead.

- **AsyncMock coroutine warnings** (`tests/`) - Test helpers created unawaited coroutines from mocked `hass.create_task`. Fixed by properly closing coroutines after inspection in test assertions.

## [0.1.12] - 2025-12-XX

### Fixed

#### Critical

- **asyncio.Lock inside threading.Lock** (`client_manager.py`) - Creating asyncio.Lock while holding a threading.Lock could cause deadlocks. Fixed by moving asyncio.Lock creation outside the threading.Lock context.

#### High Priority

- **Direct registry_entry mutation** (`sensors/sungrow_number_sensor.py`) - Code directly mutated `registry_entry` instead of using `_attr_available`. Fixed to use proper Home Assistant patterns.

- **Power factor division by zero** (`sensors/sungrow_derived_sensor.py`) - Power factor calculation crashed when both active and reactive power were zero. Fixed by returning unity (1.0) as default when apparent power is zero.

- **Sync service handler blocking** (`__init__.py`) - `service_write_holding_register` was synchronous, blocking the event loop during Modbus writes. Fixed by making it async with proper error handling.

- **Clock drift midnight edge case** (`helpers.py`) - Clock drift calculation failed around midnight when hour wrapped from 23 to 0. Fixed by handling the wrap-around case properly.

#### Medium Priority

- **Event listener accumulation on reload** (`time.py`) - SungrowTimeEntity accumulated event listeners on each config reload, causing duplicate updates. Fixed by properly unsubscribing in `async_will_remove_from_hass`.

- **TimeEntity wrong base class** (`time.py`) - SungrowTimeEntity inherited from RestoreSensor instead of RestoreEntity. Fixed base class inheritance.

- **SelectEntity missing event listener** (`sensors/sungrow_select_entity.py`) - SungrowSelectEntity didn't register for Modbus update events. Added event listener registration matching other entity types.

- **Battery stack probe early exit** (`battery_controller.py`) - Battery stack probing stopped at first failure instead of continuing to check all stacks. Fixed to probe all stacks regardless of individual failures.

- **Hardcoded spike filter registers** (`data_retrieval.py`) - Spike-filtered registers were hardcoded. Made configurable via `SPIKE_FILTERED_REGISTERS` constant.

#### Low Priority

- **Unreachable dead code** (`sensor_data/model_overrides.py`) - `_match_model` contained unreachable code after return statement. Removed dead code.

- **Yoda conditions** (multiple files) - Fixed `CONSTANT == value` patterns to `value == CONSTANT` per Ruff SIM300.

## [0.1.8] - 2025-12-XX

### Fixed

#### Critical

- **pymodbus 3.x Serial incompatibility** (`modbus_controller.py`) - Serial Modbus read/write calls failed because pymodbus 3.x requires explicit `device_id=` parameter (ignores `client.slave` attribute). Fixed by passing `device_id=` on all Serial read/write calls.

- **pymodbus 3.x slave parameter rename** (`battery_controller.py`) - Battery controller used obsolete `slave=` parameter. Fixed to use `device_id=` per pymodbus 3.x API.

- **Binary sensor wrong register** (`sensors/sungrow_binary_sensor.py`) - Internal enable/disable switch checked register 5 instead of 90005 (matching switch.py definition). Fixed register address.

- **Entity cleanup on unload** (`__init__.py`) - Config entry unload didn't clean up `SENSOR_ENTITIES`, `SENSOR_DERIVED_ENTITIES`, `BATTERY_SENSORS`, `TIME_ENTITIES`, and `VALUES` caches, causing stale entities on reload. Added cleanup for all caches.

#### Important

- **Service schema missing slave field** (`__init__.py`) - `SCHEME_HOLDING_REGISTER` lacked `slave` field, preventing targeting of non-default slave IDs in multi-inverter setups. Added slave field to schema.

- **Switch entity namespace collision** (`switch.py`) - `SWITCH_ENTITIES` wasn't namespaced by `entry_id`, causing collisions in multi-inverter setups. Fixed by namespacing like other entity types.

- **Test suite pollution** (`pytest.ini`, `scripts/`) - pytest collected test functions from `scripts/test_live_connection.py`. Fixed by configuring `testpaths` in pytest.ini and renaming script to `live_connection_check.py`.

- **Async test warnings** (`tests/test_data_retrieval.py`) - Tests used `unittest.TestCase` with `async def` methods, causing coroutines to never be awaited. Converted to pytest style with `@pytest.mark.asyncio`.

## [0.1.6] - 2025-12-XX

### Added

- CI: Add ruff linting and format all files
- Sungrow logo

### Fixed

#### High Priority

- **Derived sensor mutating _register** (`sensors/sungrow_derived_sensor.py`) - Battery power calculation mutated `self._register` list during update, corrupting future calculations. Fixed by using local variable copy.

- **Duplicate schedule_update_ha_state** (`sensors/sungrow_derived_sensor.py`) - Derived sensor called `schedule_update_ha_state()` twice per update. Removed duplicate call.

- **Premature cache_save before write** (`sensors/sungrow_binary_sensor.py`, `sensors/sungrow_select_entity.py`) - Code called `cache_save` before write completed, potentially caching uncommitted values. Removed premature cache_save (controller handles it).

#### Medium Priority

- **Service handler missing validation** (`__init__.py`) - `service_write_holding_register` lacked register/value range validation and null checks. Added validation for register (0-65535), value (0-65535), and required fields.

- **Battery sensor race condition** (`data_retrieval.py`) - Iterating over battery sensor list while it could be modified caused race conditions. Fixed by iterating over a list copy.

- **Derived sensor index out of bounds** (`sensors/sungrow_derived_sensor.py`) - Accessing `self._register[0]`, `self._register[1]` etc. without length checks could crash. Added length guards before index access.

#### Low Priority

- **Number sensor ignoring register values** (`sensors/sungrow_number_sensor.py`) - Number sensor only used last received register value, ignoring multi-register values. Fixed to use all received values.

- **split_s32 signed overflow** (`helpers.py`) - `split_s32` helper didn't properly handle negative 32-bit integers. Fixed signed integer conversion.

- **split_s32 empty input crash** (`helpers.py`) - `split_s32` crashed on empty input list. Added length guard.

## [0.1.5] - 2025-12-XX

### Fixed

- **Thread-safe ClientManager** (`client_manager.py`) - `ClientManager` singleton and `_clients` dictionary had race conditions in multi-threaded access. Added `threading.Lock` for instance creation and all dictionary operations.

- **Cache None crash** (`sensors/sungrow_binary_sensor.py`, `sensors/sungrow_select_entity.py`) - Entity updates crashed when cache returned `None`. Added null checks before processing cached values.

- **Missing async_write_ha_state** (`sensors/sungrow_binary_sensor.py`, `sensors/sungrow_select_entity.py`) - State changes weren't pushed to Home Assistant immediately. Added `async_write_ha_state()` calls after state updates.

- **Sensor namespace collision** (`sensor.py`) - `SENSOR_ENTITIES` and `SENSOR_DERIVED_ENTITIES` weren't namespaced by `entry_id`, causing collisions with multiple inverters. Fixed by namespacing all sensor tracking.

## [0.1.4] - 2025-12-XX

### Fixed

- **Holding register flag ignored** (`data_retrieval.py`) - Data retrieval used address threshold `>= 40000` to determine holding vs input registers, causing 13xxx and 33xxx holding registers (EMS settings, SoC limits, battery power) to be read as input registers. Fixed by checking `sensor_group.is_holding` flag instead.

- **Off-by-one register addressing** (`sensor_data/hybrid_sensors.py`) - 9 holding registers used 0-indexed addresses instead of 1-indexed register numbers. The reference YAML uses `address: X # reg Y` format where address is 0-indexed. Fixed: EMS Mode Selection, Battery Forced Charge/Discharge, Max/Min SoC, Export Power Limit, Backup Mode, Export Power Limit Mode, Reserved SoC For Backup.

## [0.1.3] - 2025-12-XX

### Fixed

- **Entity ID collision in multi-inverter** (`modbus_controller.py`) - Multiple inverters of the same model had identical entity IDs. Fixed by including serial number in device name for unique entity IDs.

- **Switch/Select missing has_entity_name** (`sensors/sungrow_binary_sensor.py`, `sensors/sungrow_select_entity.py`) - Switch and select entities didn't set `_attr_has_entity_name = True`, causing entity naming issues. Added attribute.

### Changed

- **BREAKING: Entity ID format change** - Entity IDs now follow pattern `{platform}.sungrow_{model}_{serial}_{name}`. Users may need to update automations and dashboards after upgrading.

## [0.1.2] - 2025-12-XX

### Fixed

- **_attr_is_on not initialized** (`sensors/sungrow_binary_sensor.py`) - Binary sensor didn't initialize `_attr_is_on`, causing AttributeError on first access. Added initialization.

## [0.1.1] - 2025-12-XX

### Added

- MPPT3 and three-phase sensor filtering based on inverter model
- Human-readable alarm code mapping for fault/state sensors
- Device type code mapping expanded from 40 to 95 models
- Multi-battery stack monitoring scaffolding
- Firmware version support in inverter configuration

### Fixed

- Time entity setup for hybrid inverters

## [0.1.0] - 2025-12-XX

### Added

- Initial release
- Modbus TCP and Serial (RS485) communication
- Support for Sungrow SHx hybrid inverters
- Sensor entities for PV, battery, grid, and system data
- Number entities for writable settings
- Switch entities for binary controls
- Select entities for multi-value settings
- Time entities for inverter clock
- Multi-inverter support
- Config flow for easy setup
