import sys
import os

# Add the project root to sys.path so that custom_components can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Python 3.13+ asyncio compatibility fix
# This must be done before any other imports that might interact with asyncio
import asyncio

# Store the original get_event_loop
_original_get_event_loop = asyncio.get_event_loop

def _patched_get_event_loop():
    """Patched get_event_loop that creates a loop if none exists (Python 3.13 compat)."""
    try:
        return _original_get_event_loop()
    except RuntimeError:
        # Python 3.13+ raises RuntimeError when no event loop exists
        # Create a new event loop and set it as the current one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Apply the patch
asyncio.get_event_loop = _patched_get_event_loop

try:
    from homeassistant import runner
    asyncio.set_event_loop_policy(runner.HassEventLoopPolicy(False))
except ImportError:
    pass  # Fallback if runner is not available

import pytest


# Live device testing configuration
DEFAULT_INVERTER_IP = "192.168.11.6"
DEFAULT_INVERTER_PORT = 502
DEFAULT_SLAVE_ID = 1


def pytest_addoption(parser):
    """Add command line options for live device testing."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live device tests (requires actual inverter connection)"
    )
    parser.addoption(
        "--inverter-ip",
        action="store",
        default=DEFAULT_INVERTER_IP,
        help=f"Inverter IP address (default: {DEFAULT_INVERTER_IP})"
    )
    parser.addoption(
        "--inverter-port",
        action="store",
        type=int,
        default=DEFAULT_INVERTER_PORT,
        help=f"Inverter Modbus port (default: {DEFAULT_INVERTER_PORT})"
    )
    parser.addoption(
        "--slave-id",
        action="store",
        type=int,
        default=DEFAULT_SLAVE_ID,
        help=f"Modbus slave ID (default: {DEFAULT_SLAVE_ID})"
    )
