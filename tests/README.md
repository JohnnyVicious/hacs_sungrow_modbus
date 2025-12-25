# Test Suite for Sungrow Modbus Integration

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all unit tests (excludes live device tests)
pytest tests/ -v

# Run all tests with verbose output
pytest tests/ -v --tb=short
```

## Prerequisites

### Virtual Environment Setup

The project uses a Python virtual environment. Activate it before running tests:

```bash
source .venv/bin/activate
```

### Required Packages

The virtual environment includes:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-homeassistant-custom-component` - Home Assistant test fixtures
- `pymodbus` - Modbus client library
- `python-dotenv` - Environment variable loading (optional, for live tests)

## Running Tests

### Standard Unit Tests (No Hardware Required)

```bash
# Run all unit tests
pytest tests/ -v

# Run with short traceback format
pytest tests/ -v --tb=short

# Run a specific test file
pytest tests/test_modbus_controller.py -v

# Run a specific test class
pytest tests/test_multi_inverter.py::TestControllerKeyGeneration -v

# Run a specific test
pytest tests/test_config_flow.py::test_flow_user_success -v
```

### Live Device Tests (Requires Real Inverter)

Live tests connect to an actual Sungrow inverter and perform **READ-ONLY** operations.

```bash
# Run live tests with default IP (192.168.11.6)
pytest tests/test_live_device.py -v --run-live -p no:socket

# Run live tests with custom IP
pytest tests/test_live_device.py -v --run-live -p no:socket --inverter-ip=192.168.1.100

# Run live tests with custom port
pytest tests/test_live_device.py -v --run-live -p no:socket --inverter-port=1502

# Run live tests with custom slave ID
pytest tests/test_live_device.py -v --run-live -p no:socket --slave-id=2
```

**Command Line Options for Live Tests:**

| Option | Default | Description |
|--------|---------|-------------|
| `--run-live` | `False` | Enable live device tests (required) |
| `--inverter-ip` | `192.168.11.6` | Inverter IP address |
| `--inverter-port` | `502` | Modbus TCP port |
| `--slave-id` | `1` | Modbus slave/unit ID |
| `-p no:socket` | - | Disable socket blocking (required for network access) |

### Standalone Live Connection Script

For quick validation without pytest:

```bash
# Using environment variable
export SUNGROW_IP=192.168.11.6
python scripts/test_live_connection.py

# Or create a .env file
echo "SUNGROW_IP=192.168.11.6" > .env
python scripts/test_live_connection.py

# Or pass IP directly
python scripts/test_live_connection.py --ip 192.168.1.100

# Scan all registers
python scripts/test_live_connection.py --scan
```

## Test File Overview

### Core Integration Tests

| File | Description |
|------|-------------|
| `test_integration_setup.py` | Tests integration setup/unload lifecycle |
| `test_config_flow.py` | Tests configuration flow (TCP, Serial, Options) |
| `test_modbus_controller.py` | Tests ModbusController read/write operations |
| `test_client_manager.py` | Tests shared Modbus client management |
| `test_data_retrieval.py` | Tests polling and data retrieval logic |
| `test_helpers.py` | Tests utility functions (caching, controller lookup) |

### Entity Platform Tests

| File | Description |
|------|-------------|
| `test_sensor_platform.py` | Tests sensor entity creation and updates |
| `test_sensor_definitions.py` | Tests sensor group definitions are valid |
| `test_derived_sensor.py` | Tests computed/derived sensor logic |
| `test_number_entity.py` / `test_number.py` | Tests number entity read/write |
| `test_switch_definitions_from_code.py` | Tests switch entity definitions |
| `test_switch_conflicts_requires.py` | Tests switch mutual exclusion logic |
| `test_select_entity.py` / `test_sungrow_select_entity.py` | Tests select entity behavior |
| `test_select_definitions_from_code.py` | Tests select entity definitions |
| `test_time_entity.py` | Tests time entity behavior |
| `test_binary_sensor.py` | Tests binary sensor behavior |
| `test_services.py` | Tests custom service handlers |

### Multi-Inverter & Configuration Tests

| File | Description |
|------|-------------|
| `test_multi_inverter.py` | Tests multi-inverter isolation and registry |
| `test_model_overrides.py` | Tests per-model register overrides |
| `test_unique_id_collision.py` | Tests entity unique ID uniqueness |
| `test_unique_id_migration.py` | Tests unique ID migration for existing configs |

### Live Device Tests

| File | Description |
|------|-------------|
| `test_live_device.py` | Pytest-based live device tests (requires `--run-live`) |

### Utility Scripts

| File | Description |
|------|-------------|
| `decode_serial.py` | Helper to decode serial number from registers |
| `decode_grid_serial.py` | Helper to decode grid meter serial |
| `conftest.py` | Pytest configuration and fixtures |

## Configuration

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

### conftest.py Features

- Python 3.13+ asyncio compatibility patch
- Home Assistant event loop policy setup
- Command line options for live device testing
- Default inverter connection parameters

## Test Patterns

### Mocking the Modbus Controller

```python
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.mark.asyncio
async def test_example(hass):
    with patch("custom_components.sungrow_modbus.modbus_controller.ModbusController.connect", return_value=True), \
         patch("custom_components.sungrow_modbus.modbus_controller.ModbusController.async_read_input_register", return_value=[1,2,3]):
        # Test code here
        pass
```

### Using Home Assistant Test Fixtures

```python
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.sungrow_modbus.const import DOMAIN

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield

@pytest.mark.asyncio
async def test_example(hass: HomeAssistant):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.2.3.4",
            "port": 502,
            "slave": 1,
            "inverter_serial": "SN123456",
            "model": "SH10RT",
        },
    )
    config_entry.add_to_hass(hass)
    # Test code here
```

### Creating Mock Controllers

```python
def create_mock_controller(host="10.0.0.1", port=502, slave=1):
    controller = MagicMock()
    controller.host = host
    controller.port = port
    controller.device_id = slave
    controller.connection_id = f"{host}:{port}"
    controller.connected.return_value = True
    controller.async_write_holding_register = AsyncMock(return_value=None)
    return controller
```

## Expected Results

- **Total tests:** ~281 collected
- **Skipped:** ~16 (live device tests when `--run-live` not provided)
- **Expected pass rate:** 100% for unit tests

```bash
# Typical output
264 passed, 16 skipped in 3.45s
```

## Troubleshooting

### "No module named pytest"

Ensure the virtual environment is activated:
```bash
source .venv/bin/activate
```

### Live tests skipped

Add the `--run-live` flag and ensure the inverter is reachable:
```bash
pytest tests/test_live_device.py -v --run-live -p no:socket
```

### Socket/network blocked errors

Add `-p no:socket` to disable the socket blocking plugin:
```bash
pytest tests/test_live_device.py -v --run-live -p no:socket
```

### Connection timeout

- Verify inverter IP is correct
- Check network connectivity: `ping <inverter-ip>`
- Ensure port 502 is open: `nc -zv <inverter-ip> 502`
- Verify Modbus is enabled on the inverter

### Tests failing after code changes

Run the full suite to catch regressions:
```bash
pytest tests/ -v --tb=short
```

## Important Notes

1. **Live tests are READ-ONLY** - They never write to the inverter
2. **Multi-inverter support** - Tests validate isolation between controllers
3. **Async by default** - All tests use `pytest.mark.asyncio` with auto mode
4. **Home Assistant fixtures** - Tests use `pytest-homeassistant-custom-component` for realistic HA environment
