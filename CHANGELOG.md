# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [0.1.15] - 2024-12-XX

### Fixed

- **Controller namespacing** (`helpers.py`, `__init__.py`) - Events now emit the full `connection_id` and `is_correct_controller` matches on that key, preventing cross-talk between controllers on the same host but different ports/paths.
- **Config flow cleanup** (`config_flow.py`) - Modbus clients are closed via `finally` in `_detect_device`, avoiding dangling transports on connection failure.
- **AsyncMock warnings** (`tests/`) - Test helpers close coroutines created by mocked `hass.create_task`, eliminating unawaited coroutine warnings.

## [0.1.12] - 2024-12-XX

### Fixed

- Formatted modbus_controller.py with ruff
- Use connection_id in events to prevent multi-inverter cross-talk
- Address 11 issues from code review

## [0.1.8] - 2024-12-XX

### Fixed

- Service schema and switch entity namespacing for multi-inverter support
- Test suite pollution from live script and async warnings
- Critical pymodbus 3.x compatibility and entity cleanup bugs

## [0.1.6] - 2024-12-XX

### Added

- CI: Add ruff linting and format all files
- Sungrow logo

### Fixed

- Low priority fixes and README update
- Moderate priority bugs for robustness
- High priority bugs in derived sensors and entity writes
