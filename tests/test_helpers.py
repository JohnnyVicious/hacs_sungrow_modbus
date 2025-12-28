"""Tests for helper functions."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from custom_components.sungrow_modbus.const import DOMAIN, DRIFT_COUNTER, VALUES
from custom_components.sungrow_modbus.helpers import (
    _any_in,
    cache_get,
    cache_save,
    clock_drift_test,
    decode_inverter_model,
    extract_serial_number,
    hex_to_ascii,
    split_s32,
)


class TestHexToAscii:
    """Test hex_to_ascii conversion."""

    def test_single_characters(self):
        """Test conversion of hex values to ASCII pairs."""
        # 0x4142 = 'AB'
        result = hex_to_ascii(0x4142)
        assert result == "AB"

    def test_numeric_characters(self):
        """Test conversion with numeric ASCII values."""
        # 0x3132 = '12'
        result = hex_to_ascii(0x3132)
        assert result == "12"

    def test_mixed_characters(self):
        """Test conversion with mixed ASCII values."""
        # 0x4131 = 'A1'
        result = hex_to_ascii(0x4131)
        assert result == "A1"


class TestExtractSerialNumber:
    """Test serial number extraction from register values."""

    def test_extract_simple_serial(self):
        """Test extracting a simple serial number."""
        # 'AB' 'CD' 'EF' = [0x4142, 0x4344, 0x4546]
        values = [0x4142, 0x4344, 0x4546]
        result = extract_serial_number(values)
        assert result == "ABCDEF"

    def test_extract_with_null_padding(self):
        """Test extracting serial with null padding."""
        # 'AB' '\x00\x00' = serial ends with nulls
        values = [0x4142, 0x0000]
        result = extract_serial_number(values)
        assert result == "AB"

    def test_extract_numeric_serial(self):
        """Test extracting numeric serial number."""
        # '12' '34' = [0x3132, 0x3334]
        values = [0x3132, 0x3334]
        result = extract_serial_number(values)
        assert result == "1234"


class TestClockDriftTest:
    """Test clock drift detection and correction."""

    def test_no_drift_within_tolerance(self):
        """Test no drift action when drift is small."""
        hass = MagicMock()
        hass.data = {DOMAIN: {DRIFT_COUNTER: 0}}

        controller = MagicMock()
        controller.connected.return_value = True

        # Use mock to control dt_utils.now()
        with patch("custom_components.sungrow_modbus.helpers.dt_utils") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 30)
            mock_dt.now.return_value = mock_now

            # Device time within 60 seconds (acceptable)
            result = clock_drift_test(hass, controller, 12, 0, 25)

            assert result is False
            assert hass.data[DOMAIN][DRIFT_COUNTER] == 0

    def test_drift_accumulation(self):
        """Test drift counter increments on drift detection."""
        hass = MagicMock()
        hass.data = {DOMAIN: {DRIFT_COUNTER: 0}}

        controller = MagicMock()
        controller.connected.return_value = True

        with patch("custom_components.sungrow_modbus.helpers.dt_utils") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 5, 0)
            mock_dt.now.return_value = mock_now

            # Device time 5 minutes behind (exceeds 60 second tolerance)
            result = clock_drift_test(hass, controller, 12, 0, 0)

            assert result is False
            assert hass.data[DOMAIN][DRIFT_COUNTER] == 1

    def test_drift_correction_after_threshold(self):
        """Test clock correction after more than 5 consecutive drift detections."""
        hass = MagicMock()
        hass.data = {DOMAIN: {DRIFT_COUNTER: 6}}  # Past threshold (> 5)
        hass.create_task = MagicMock()

        controller = MagicMock()
        controller.connected.return_value = True

        with patch("custom_components.sungrow_modbus.helpers.dt_utils") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 5, 0)
            mock_dt.now.return_value = mock_now

            # Device time 5 minutes behind
            result = clock_drift_test(hass, controller, 12, 0, 0)

            assert result is True
            hass.create_task.assert_called_once()

    def test_drift_reset_on_good_time(self):
        """Test drift counter resets when time is good."""
        hass = MagicMock()
        hass.data = {DOMAIN: {DRIFT_COUNTER: 3}}  # Had some drift

        controller = MagicMock()
        controller.connected.return_value = True

        with patch("custom_components.sungrow_modbus.helpers.dt_utils") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 30)
            mock_dt.now.return_value = mock_now

            # Device time within tolerance
            result = clock_drift_test(hass, controller, 12, 0, 25)

            assert result is False
            assert hass.data[DOMAIN][DRIFT_COUNTER] == 0

    def test_no_correction_when_disconnected(self):
        """Test no correction attempted when controller disconnected."""
        hass = MagicMock()
        hass.data = {DOMAIN: {DRIFT_COUNTER: 5}}
        hass.create_task = MagicMock()

        controller = MagicMock()
        controller.connected.return_value = False

        with patch("custom_components.sungrow_modbus.helpers.dt_utils") as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 5, 0)
            mock_dt.now.return_value = mock_now

            # Device time 5 minutes behind
            result = clock_drift_test(hass, controller, 12, 0, 0)

            # No task should be created (disconnected)
            assert result is False


class TestDecodeInverterModel:
    """Test inverter model decoding.

    The format is: high byte = protocol version, low byte = model code.
    E.g., 0x3010 = protocol 0x30, model 0x10 (1-Phase Grid-Tied)
    """

    def test_1phase_grid_tied(self):
        """Test decoding 1-Phase Grid-Tied Inverter (model code 0x10)."""
        # 0x3010: protocol=0x30, model=0x10
        protocol, description = decode_inverter_model(0x3010)
        assert protocol == 0x30
        assert "1-Phase Grid-Tied" in description

    def test_3phase_grid_tied_large(self):
        """Test decoding 3-Phase Grid-Tied large (model code 0x21)."""
        # 0x1021: protocol=0x10, model=0x21
        protocol, description = decode_inverter_model(0x1021)
        assert protocol == 0x10
        assert "3-Phase Grid-Tied" in description

    def test_hybrid_lv_1phase(self):
        """Test decoding 1-Phase LV Hybrid (model code 0x30)."""
        # 0x1030: protocol=0x10, model=0x30
        protocol, description = decode_inverter_model(0x1030)
        assert protocol == 0x10
        assert "1-Phase LV Hybrid" in description

    def test_hybrid_hv_3phase_5g(self):
        """Test decoding 3-Phase HV Hybrid 5G (model code 0x60)."""
        # 0x1060: protocol=0x10, model=0x60
        protocol, description = decode_inverter_model(0x1060)
        assert protocol == 0x10
        assert "3-Phase HV Hybrid" in description

    def test_s6_hybrid(self):
        """Test decoding S6 3-Phase HV Hybrid (model code 0x70)."""
        # 0x1070: protocol=0x10, model=0x70
        protocol, description = decode_inverter_model(0x1070)
        assert protocol == 0x10
        assert "S6 3-Phase HV Hybrid" in description

    def test_unknown_model(self):
        """Test handling of unknown model code."""
        # 0x10FF: protocol=0x10, model=0xFF (unknown)
        protocol, description = decode_inverter_model(0x10FF)
        assert protocol == 0x10
        assert "Unknown" in description

    def test_hex_string_input(self):
        """Test handling of hex string input."""
        protocol, description = decode_inverter_model("0x3010")
        assert protocol == 0x30

    def test_no_definition(self):
        """Test model code 0x00 returns 'No definition'."""
        protocol, description = decode_inverter_model(0x1000)
        assert protocol == 0x10
        assert "No definition" in description


class TestCacheOperations:
    """Test cache save and get operations."""

    def test_cache_save_without_controller(self):
        """Test saving to cache without controller key."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        cache_save(hass, 33000, 100)

        assert hass.data[DOMAIN][VALUES]["33000"] == 100

    def test_cache_get_without_controller(self):
        """Test getting from cache without controller key."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"33000": 100}}}

        result = cache_get(hass, 33000)

        assert result == 100

    def test_cache_save_with_controller(self):
        """Test saving to cache with controller key."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        cache_save(hass, 33000, 100, "192.168.1.100:502_1")

        assert hass.data[DOMAIN][VALUES]["192.168.1.100:502_1:33000"] == 100

    def test_cache_get_with_controller(self):
        """Test getting from cache with controller key."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"192.168.1.100:502_1:33000": 100}}}

        result = cache_get(hass, 33000, "192.168.1.100:502_1")

        assert result == 100

    def test_cache_get_missing(self):
        """Test getting missing value returns None."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        result = cache_get(hass, 99999)

        assert result is None

    def test_cache_isolation_between_controllers(self):
        """Test cache values are isolated between controllers."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        cache_save(hass, 33000, 100, "controller1")
        cache_save(hass, 33000, 200, "controller2")

        assert cache_get(hass, 33000, "controller1") == 100
        assert cache_get(hass, 33000, "controller2") == 200


class TestSplitS32:
    """Test signed 32-bit integer splitting."""

    def test_positive_value(self):
        """Test splitting positive 32-bit value."""
        # 0x00010002 = 65538
        values = [0x0001, 0x0002]
        result = split_s32(values)
        assert result == 65538

    def test_negative_value(self):
        """Test splitting negative 32-bit value."""
        # -1 in signed 32-bit = 0xFFFFFFFF
        values = [0xFFFF, 0xFFFF]
        result = split_s32(values)
        assert result == -1

    def test_zero_value(self):
        """Test splitting zero value."""
        values = [0x0000, 0x0000]
        result = split_s32(values)
        assert result == 0

    def test_large_positive(self):
        """Test splitting large positive value."""
        # 0x7FFFFFFF = 2147483647 (max signed 32-bit)
        values = [0x7FFF, 0xFFFF]
        result = split_s32(values)
        assert result == 2147483647


class TestAnyIn:
    """Test _any_in helper function."""

    def test_any_match(self):
        """Test returns True when any item matches."""
        target = [1, 2, 3]
        collection = {2, 5, 6}
        assert _any_in(target, collection) is True

    def test_no_match(self):
        """Test returns False when no items match."""
        target = [1, 2, 3]
        collection = {4, 5, 6}
        assert _any_in(target, collection) is False

    def test_empty_target(self):
        """Test returns False for empty target."""
        target = []
        collection = {1, 2, 3}
        assert _any_in(target, collection) is False

    def test_empty_collection(self):
        """Test returns False for empty collection."""
        target = [1, 2, 3]
        collection = set()
        assert _any_in(target, collection) is False

    def test_all_match(self):
        """Test returns True when all items match."""
        target = [1, 2, 3]
        collection = {1, 2, 3, 4, 5}
        assert _any_in(target, collection) is True
