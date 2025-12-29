"""Tests for the CircuitBreaker class."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from custom_components.sungrow_modbus.modbus_controller import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_MINUTES,
    CircuitBreaker,
    CircuitState,
)


class TestCircuitBreaker(unittest.TestCase):
    """Test the CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()

        self.assertEqual(CircuitState.CLOSED, breaker.state)
        self.assertEqual(0, breaker.failure_count)
        self.assertIsNone(breaker.last_failure_time)
        self.assertTrue(breaker.can_attempt())
        self.assertFalse(breaker.is_open)

    def test_single_failure_does_not_open_circuit(self):
        """Test that a single failure doesn't open the circuit."""
        breaker = CircuitBreaker()

        breaker.record_failure()

        self.assertEqual(CircuitState.CLOSED, breaker.state)
        self.assertEqual(1, breaker.failure_count)
        self.assertTrue(breaker.can_attempt())

    def test_threshold_failures_opens_circuit(self):
        """Test that reaching the failure threshold opens the circuit."""
        breaker = CircuitBreaker(failure_threshold=3)

        # Record failures up to threshold
        breaker.record_failure()  # 1
        breaker.record_failure()  # 2
        self.assertEqual(CircuitState.CLOSED, breaker.state)

        breaker.record_failure()  # 3 - should open

        self.assertEqual(CircuitState.OPEN, breaker.state)
        self.assertEqual(3, breaker.failure_count)
        self.assertFalse(breaker.can_attempt())
        self.assertTrue(breaker.is_open)

    def test_success_resets_circuit(self):
        """Test that success resets the circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=3)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()
        self.assertEqual(CircuitState.OPEN, breaker.state)

        # Fast forward time to allow recovery
        breaker.last_failure_time = datetime.now(UTC) - timedelta(minutes=10)

        # Now can_attempt should return True and set state to HALF_OPEN
        self.assertTrue(breaker.can_attempt())
        self.assertEqual(CircuitState.HALF_OPEN, breaker.state)

        # Record success
        breaker.record_success()

        self.assertEqual(CircuitState.CLOSED, breaker.state)
        self.assertEqual(0, breaker.failure_count)
        self.assertIsNone(breaker.last_failure_time)
        self.assertTrue(breaker.can_attempt())

    def test_success_during_closed_state(self):
        """Test that success during CLOSED state keeps it closed."""
        breaker = CircuitBreaker()
        breaker.record_failure()  # One failure

        breaker.record_success()

        self.assertEqual(CircuitState.CLOSED, breaker.state)
        self.assertEqual(0, breaker.failure_count)

    def test_recovery_timeout_allows_half_open(self):
        """Test that after recovery timeout, circuit moves to HALF_OPEN."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=1),
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        self.assertEqual(CircuitState.OPEN, breaker.state)
        self.assertFalse(breaker.can_attempt())

        # Simulate time passing
        breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)

        # Now should allow attempt and move to HALF_OPEN
        self.assertTrue(breaker.can_attempt())
        self.assertEqual(CircuitState.HALF_OPEN, breaker.state)

    def test_half_open_failure_returns_to_open(self):
        """Test that failure in HALF_OPEN state returns to OPEN."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=1),
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Fast forward to allow recovery attempt
        breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
        breaker.can_attempt()  # Moves to HALF_OPEN

        self.assertEqual(CircuitState.HALF_OPEN, breaker.state)

        # Fail during HALF_OPEN
        breaker.record_failure()

        self.assertEqual(CircuitState.OPEN, breaker.state)
        self.assertFalse(breaker.can_attempt())

    def test_half_open_success_closes_circuit(self):
        """Test that success in HALF_OPEN state closes the circuit."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=1),
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Fast forward to allow recovery attempt
        breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
        breaker.can_attempt()  # Moves to HALF_OPEN

        self.assertEqual(CircuitState.HALF_OPEN, breaker.state)

        # Succeed during HALF_OPEN
        breaker.record_success()

        self.assertEqual(CircuitState.CLOSED, breaker.state)
        self.assertEqual(0, breaker.failure_count)

    def test_time_until_retry_when_open(self):
        """Test time_until_retry returns correct value when open."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(minutes=5),
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Should have time remaining
        remaining = breaker.time_until_retry
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining.total_seconds(), 0)
        self.assertLessEqual(remaining.total_seconds(), 300)  # 5 minutes

    def test_time_until_retry_when_closed(self):
        """Test time_until_retry returns None when closed."""
        breaker = CircuitBreaker()

        self.assertIsNone(breaker.time_until_retry)

    def test_time_until_retry_when_expired(self):
        """Test time_until_retry returns None when timeout has passed."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(seconds=1),
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Fast forward past recovery timeout
        breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)

        self.assertIsNone(breaker.time_until_retry)

    def test_is_open_property(self):
        """Test is_open property correctly reflects state."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=timedelta(minutes=5),
        )

        # Initially not open
        self.assertFalse(breaker.is_open)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Now should be open
        self.assertTrue(breaker.is_open)

        # Fast forward past recovery
        breaker.last_failure_time = datetime.now(UTC) - timedelta(minutes=10)

        # Should no longer be "open" (ready to attempt)
        self.assertFalse(breaker.is_open)

    def test_default_values_match_constants(self):
        """Test that default values match the module constants."""
        breaker = CircuitBreaker()

        self.assertEqual(CIRCUIT_BREAKER_FAILURE_THRESHOLD, breaker.failure_threshold)
        self.assertEqual(
            timedelta(minutes=CIRCUIT_BREAKER_RECOVERY_MINUTES),
            breaker.recovery_timeout,
        )

    def test_logger_prefix_in_messages(self):
        """Test that logger prefix is used in log messages."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            _logger_prefix="(test.1) ",
        )

        # We just verify the prefix is stored, actual logging tested via integration
        self.assertEqual("(test.1) ", breaker._logger_prefix)


class TestCircuitBreakerIntegration(unittest.TestCase):
    """Test CircuitBreaker integration with ModbusController."""

    def test_controller_has_circuit_breaker(self):
        """Test that ModbusController initializes with a CircuitBreaker."""
        from unittest.mock import MagicMock

        with patch("custom_components.sungrow_modbus.modbus_controller.ModbusClientManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager
            mock_manager.get_tcp_client.return_value = MagicMock()
            mock_manager.get_client_lock.return_value = MagicMock()

            from custom_components.sungrow_modbus.modbus_controller import ModbusController

            inverter_config = MagicMock()
            inverter_config.model = "Test"

            controller = ModbusController(
                hass=MagicMock(),
                inverter_config=inverter_config,
                host="192.168.1.1",
                port=502,
            )

            self.assertIsInstance(controller.circuit_breaker, CircuitBreaker)
            self.assertEqual(CircuitState.CLOSED, controller.circuit_breaker.state)


if __name__ == "__main__":
    unittest.main()
