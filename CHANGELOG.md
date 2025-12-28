# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

#### Critical Fixes

- **Signed integer handling for single registers** - Previously, the `signed` attribute in sensor definitions was ignored for single-register (S16) values. Negative values like temperatures below 0°C were incorrectly displayed as large positive numbers (e.g., -5°C showed as 6553.1°C). Now properly converts U16 to S16 when `signed: true` is set. Affects 30+ sensors including battery and internal temperatures.

- **asyncio.Lock event loop binding** - Fixed potential `RuntimeError` during Home Assistant startup by creating asyncio locks lazily on first access instead of during client registration. This ensures locks are bound to the correct event loop when used from async context.

#### Important Fixes

- **Connection retry loop now has max limit** - Added maximum retry count (20 attempts, ~10 minutes with exponential backoff) to prevent infinite retry loops when a device is permanently offline. Connection will be reattempted on the next scheduled check_connection cycle.

- **Exception logging upgraded to WARNING level** - Exceptions during Modbus polling are now logged at WARNING level with full stack traces instead of DEBUG level, making troubleshooting easier.

- **Write queue graceful shutdown** - The write queue processor now handles `CancelledError` properly, draining any pending write requests before exiting during integration unload.

- **Warning for unvalidated register writes** - The `sungrow_write_holding_register` service now warns when writing to registers outside known safe ranges, helping prevent accidental writes to read-only or critical system registers.

- **Controller state encapsulation** - Added proper methods (`mark_data_received()`, `remove_sensor_groups()`) to ModbusController instead of directly manipulating private attributes from DataRetrieval.

- **Clock drift correction rate limiting** - Added 1-hour cooldown between clock corrections to prevent spam if the inverter's RTC is faulty and immediately drifts after correction.

### Changed

- **Removed duplicate TCP/Serial code** - Eliminated redundant branching in 4 Modbus methods where TCP and Serial code paths were identical (pymodbus 3.x uses the same API for both).

## [0.1.15] - 2024-12-XX

### Fixed

- Controller namespacing: Events now emit the full `connection_id` and `is_correct_controller` matches on that key, preventing cross-talk between controllers on the same host but different ports/paths.
- Config flow cleanup: Modbus clients are closed via `finally` in `_detect_device`, avoiding dangling transports on connection failure.
- AsyncMock warnings: Test helpers close coroutines created by mocked `hass.create_task`, eliminating unawaited coroutine warnings.

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
