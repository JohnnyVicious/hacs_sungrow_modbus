# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Sungrow SHx hybrid inverters. It communicates via Modbus protocol (TCP or Serial/RS485) to read sensor data and control inverter settings.

## Commands

### Running Tests
```bash
# Run all tests (use venv)
.venv/bin/python -m pytest

# Run a specific test file
.venv/bin/python -m pytest tests/test_config_flow.py

# Run a specific test with verbose output
.venv/bin/python -m pytest tests/test_config_flow.py::test_tcp_connection_flow -v

# Run with short traceback for faster debugging
.venv/bin/python -m pytest --tb=short
```

### Commit Hygiene
- Fix **one issue per commit**. Do not batch multiple bug fixes into a single commit; each issue should have its own commit to keep history and rollbacks clear.

### Issue Tracking (ISSUES.md)

**NEVER delete ISSUES.md.** This file tracks known issues and technical debt. When issues are resolved, remove them from the file but keep the scaffolding structure intact for future issues.

When discovering new issues during code review:
1. Add them to the appropriate section (Critical, Important, or Minor)
2. Use the template format provided in the file
3. Include: severity, file, line, symptom, current code, root cause, suggested fix, and impact

When fixing issues:
1. Remove the resolved issue from ISSUES.md
2. Add the fix to CHANGELOG.md
3. Keep one issue per commit

### Changelog Maintenance (REQUIRED)

**ALWAYS update CHANGELOG.md when making fixes or changes.** This prevents regression by tracking what was fixed and why.

After each fix commit, add an entry to `CHANGELOG.md` under the `[Unreleased]` section:

```markdown
## [Unreleased]

### Fixed
- **Brief description** - Detailed explanation of what was broken and how it was fixed. Include file names and the root cause.
```

**Why this matters:**
- Prevents fixing the same bug multiple times
- Documents the reasoning behind changes
- Makes code review easier
- Helps identify patterns in recurring issues

**What to include in each entry:**
1. What was broken (the symptom)
2. Why it was broken (the root cause)
3. How it was fixed (the solution)
4. Which files were affected

Example:
```markdown
- **Signed integer handling for single registers** - Single-register values with `signed: true` were displayed as large positive numbers instead of negative values (e.g., -5°C showed as 6553.1°C). Root cause: `SungrowBaseSensor` accepted but never used the `signed` parameter. Fixed by storing the attribute and applying U16→S16 conversion in `_convert_raw_value()`. Affects `sensors/sungrow_base_sensor.py`.
```

### Testing Guidelines

**ALWAYS run tests after making code changes.** Before committing, verify all tests pass.

#### When to Update Tests

When changing code, check if tests need updating:
- **Fixing a bug**: Update tests that expected the old (broken) behavior
- **Changing API/parameters**: Update mock assertions (e.g., `slave=` → `device_id=`)
- **Adding features**: Consider adding tests for new functionality
- **Changing storage structure**: Update tests that check data structures (e.g., namespacing by `entry_id`)

#### Common Test Pitfalls to AVOID

1. **NEVER use `async def` on `unittest.TestCase` methods**
   ```python
   # WRONG - coroutine never awaited, test silently passes
   class TestFoo(unittest.TestCase):
       async def test_something(self):  # BAD!
           await some_async_func()

   # CORRECT - use pytest style
   class TestFoo:
       @pytest.mark.asyncio
       async def test_something(self):
           await some_async_func()
   ```

2. **Close coroutines after inspection to prevent warnings**
   ```python
   # If you inspect a coroutine without awaiting it:
   task = mock_hass.create_task.call_args[0][0]
   assert inspect.iscoroutine(task)
   task.close()  # Prevent "coroutine was never awaited" warning
   ```

3. **Use `setup_method` not `setUp` for pytest-style classes**
   ```python
   class TestFoo:
       def setup_method(self):  # pytest style
           self.mock = MagicMock()

       def teardown_method(self):  # Clean up patchers
           self.patcher.stop()
   ```

4. **Keep patchers active across async tests**
   ```python
   # WRONG - patch exits before async code runs
   def setup_method(self):
       with patch("module.func") as self.mock:
           self.obj = SomeClass()  # Patch is gone after this!

   # CORRECT - start/stop pattern
   def setup_method(self):
       self.patcher = patch("module.func")
       self.mock = self.patcher.start()
       self.obj = SomeClass()

   def teardown_method(self):
       self.patcher.stop()
   ```

5. **Mock callbacks should match sync/async nature**
   ```python
   # If real function is sync, mock should be sync
   def capture_add_devices(entities, update):  # sync callback
       captured.extend(entities)

   # NOT async def - causes "coroutine never awaited"
   ```

### Linting (REQUIRED before committing)

**ALWAYS run Ruff before committing.** The CI workflow will fail if Ruff finds issues.

```bash
# Run Ruff linter AND formatter (REQUIRED - CI checks both)
.venv/bin/ruff check . && .venv/bin/ruff format .

# Or check without modifying (to see what would change)
.venv/bin/ruff check . && .venv/bin/ruff format --check .

# Auto-fix safe linting issues
.venv/bin/ruff check --fix .
```

Common Ruff rules to watch for:
- **SIM300**: Yoda conditions - use `value == CONSTANT` not `CONSTANT == value`
- **E501**: Line too long (handled by formatter, ignored)
- **I**: Import sorting issues

### Documentation
```bash
cd docs && pip install -r requirements.txt && sphinx-build -b html source build
```

### Creating a Release

When asked to create a release, follow these steps:

1. **Update version numbers** in both files:
   - `custom_components/sungrow_modbus/manifest.json`
   - `pyproject.toml`

2. **Run linting, formatting, and tests** (REQUIRED):
   ```bash
   .venv/bin/ruff check . && .venv/bin/ruff format . && .venv/bin/python -m pytest
   ```

3. **Commit and push** the version bump:
   ```bash
   git add -A && git commit -m "chore: Bump version to vX.Y.Z" && git push origin main
   ```

4. **Create an annotated git tag**:
   ```bash
   git tag -a vX.Y.Z -m "Release notes here"
   git push origin vX.Y.Z
   ```

5. **Create a GitHub Release** (this is the critical step often missed):
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z - Title" --notes "Release notes here"
   ```

**Important:** A git tag alone is NOT a GitHub Release. You MUST use `gh release create` to make the release visible on GitHub's Releases page and trigger HACS updates.

Release notes should include:
- Summary of changes grouped by category (Bug Fixes, Features, etc.)
- Impact statements explaining what was broken and how it's fixed
- Upgrade notes if any action is required

## Architecture

### Core Communication Flow
```
User Configuration → ConfigFlow → ModbusController → ClientManager
                                        ↓
                               DataRetrieval (polling)
                                        ↓
                               Sensor Groups → Home Assistant Entities
```

### Key Components

**ClientManager** (`client_manager.py`): Singleton that manages shared modbus connections. Uses reference counting so multiple controllers can share the same connection.

**ModbusController** (`modbus_controller.py`): Handles all modbus read/write operations. Implements a write queue to prevent overwhelming the device with simultaneous writes.

**DataRetrieval** (`data_retrieval.py`): Manages polling at different speeds (ONCE, FAST, NORMAL, SLOW). Caches register values in `hass.data[DOMAIN][VALUES]`.

### Sensor Definition Structure

Sensors are defined in `sensor_data/hybrid_sensors.py` as groups:

```python
{
    "register_start": 13019,           # First register in the group
    "poll_speed": PollSpeed.FAST,      # Polling frequency
    "holding": True,                   # Optional: use holding registers instead of input
    "feature_requirement": [InverterFeature.BATTERY],  # Optional: only for certain features
    "entities": [
        {
            "name": "Battery Voltage",
            "unique": "sungrow_modbus_battery_voltage",
            "register": ['13019'],
            "multiplier": 0.1,               # 0=string, 1=direct, 0.1=divide by 10
            "device_class": SensorDeviceClass.VOLTAGE,
            "unit_of_measurement": UnitOfElectricPotential.VOLT,
            "state_class": SensorStateClass.MEASUREMENT,
            "category": Category.BATTERY_INFORMATION,
            "signed": True,                  # Optional: treat as signed integer
            "editable": False                # True for writable holding registers
        }
    ]
}
```

### Sungrow Register Ranges

| Range | Type | Description |
|-------|------|-------------|
| 4989-5000 | Input | Device info (serial, type code) |
| 5002-5050 | Input | PV generation, MPPT data, inverter temp |
| 5018-5035 | Input | AC voltages, reactive power, power factor |
| 5241 | Input | Grid frequency |
| 5600-5650 | Input | Meter data, BMS info |
| 5722-5746 | Input | Backup power, meter voltages/currents |
| 12999-13050 | Input | System/running state, battery status, load/export power |
| 13049-13100 | Holding | EMS control, SoC limits, export limits |
| 13249-13294 | Input | Firmware versions |
| 33046-33150 | Holding | Battery power settings |

### Entity Types

| Type | File | Purpose |
|------|------|---------|
| Sensor | `sensor.py` | Read-only measurements |
| Number | `number.py` | Writable numeric registers |
| Switch | `switch.py` | Bit-level control |
| Select | `select.py` | Multi-value selection |
| Time | `time.py` | Inverter clock setting |

### Inverter Configuration

`data/sungrow_config.py` defines `InverterConfig` with 39 Sungrow models:
- RS series (single-phase): SH3.0RS to SH10RS
- RT series (three-phase): SH5.0RT to SH10RT with variants (-20, -V112, -V122)
- T series (three-phase large): SH5T to SH25T
- MG series: MG5RL, MG6RL

### Poll Speeds

- **ONCE**: Single read after startup (firmware versions, serial)
- **FAST**: 5-10 second intervals (power, voltage, current, battery status)
- **NORMAL**: 15 second intervals (EMS settings, limits)
- **SLOW**: 30+ second intervals (energy totals, temperatures)

## Reference Material

- `example-sungrow/`: Working YAML-based Sungrow integration with modbus register definitions
- `example-solax-modbus/`: Parent project documentation
