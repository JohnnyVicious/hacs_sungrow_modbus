"""Tests for the RegisterCache TTL-based caching system."""

import time
from unittest.mock import MagicMock, patch

from custom_components.sungrow_modbus.helpers import (
    CachedValue,
    RegisterCache,
    get_register_cache,
)


class TestCachedValue:
    """Tests for the CachedValue dataclass."""

    def test_cached_value_creation(self):
        """Test creating a CachedValue."""
        now = time.monotonic()
        cached = CachedValue(value=42, expires_at=now + 100)
        assert cached.value == 42
        assert cached.expires_at > now


class TestRegisterCache:
    """Tests for the RegisterCache class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = RegisterCache()
        self.controller_key = "192.168.1.100:502_1"

    def test_set_and_get(self):
        """Test basic set and get operations."""
        self.cache.set(self.controller_key, 5000, 1234, ttl_seconds=60)
        value = self.cache.get(self.controller_key, 5000)
        assert value == 1234

    def test_get_missing_returns_none(self):
        """Test that getting a missing key returns None."""
        value = self.cache.get(self.controller_key, 9999)
        assert value is None

    def test_get_expired_returns_none(self):
        """Test that getting an expired value returns None."""
        # Use a mock to simulate time passing
        with patch("custom_components.sungrow_modbus.helpers.time.monotonic") as mock_time:
            # Set value at time 0
            mock_time.return_value = 0
            self.cache.set(self.controller_key, 5000, 1234, ttl_seconds=60)

            # Get value at time 30 (not expired)
            mock_time.return_value = 30
            assert self.cache.get(self.controller_key, 5000) == 1234

            # Get value at time 61 (expired)
            mock_time.return_value = 61
            assert self.cache.get(self.controller_key, 5000) is None

    def test_expired_value_is_removed(self):
        """Test that expired values are removed from cache on access."""
        with patch("custom_components.sungrow_modbus.helpers.time.monotonic") as mock_time:
            mock_time.return_value = 0
            self.cache.set(self.controller_key, 5000, 1234, ttl_seconds=60)
            assert len(self.cache._cache) == 1

            # Access after expiry should remove from cache
            mock_time.return_value = 61
            self.cache.get(self.controller_key, 5000)
            assert len(self.cache._cache) == 0

    def test_set_range_and_get_range(self):
        """Test range operations."""
        values = [100, 200, 300, 400, 500]
        self.cache.set_range(self.controller_key, 5000, values, ttl_seconds=60)

        result = self.cache.get_range(self.controller_key, 5000, 5)
        assert result == values

    def test_get_range_partial_missing_returns_none(self):
        """Test that get_range returns None if any value is missing."""
        values = [100, 200, 300]
        self.cache.set_range(self.controller_key, 5000, values, ttl_seconds=60)

        # Request more registers than cached
        result = self.cache.get_range(self.controller_key, 5000, 5)
        assert result is None

    def test_get_range_partial_expired_returns_none(self):
        """Test that get_range returns None if any value is expired."""
        with patch("custom_components.sungrow_modbus.helpers.time.monotonic") as mock_time:
            mock_time.return_value = 0

            # Set first 3 registers
            self.cache.set_range(self.controller_key, 5000, [100, 200, 300], ttl_seconds=60)

            # Set register 5003 with shorter TTL
            mock_time.return_value = 10
            self.cache.set(self.controller_key, 5003, 400, ttl_seconds=30)
            self.cache.set(self.controller_key, 5004, 500, ttl_seconds=60)

            # At time 50, register 5003 is expired (set at 10 with 30s TTL)
            mock_time.return_value = 50
            result = self.cache.get_range(self.controller_key, 5000, 5)
            assert result is None

    def test_is_range_cached(self):
        """Test checking if a range is cached."""
        values = [100, 200, 300]
        self.cache.set_range(self.controller_key, 5000, values, ttl_seconds=60)

        assert self.cache.is_range_cached(self.controller_key, 5000, 3) is True
        assert self.cache.is_range_cached(self.controller_key, 5000, 4) is False
        assert self.cache.is_range_cached(self.controller_key, 5001, 3) is False

    def test_invalidate(self):
        """Test invalidating a single register."""
        self.cache.set(self.controller_key, 5000, 1234, ttl_seconds=60)
        assert self.cache.get(self.controller_key, 5000) == 1234

        self.cache.invalidate(self.controller_key, 5000)
        assert self.cache.get(self.controller_key, 5000) is None

    def test_invalidate_nonexistent_is_safe(self):
        """Test that invalidating a nonexistent key doesn't raise."""
        self.cache.invalidate(self.controller_key, 9999)  # Should not raise

    def test_invalidate_range(self):
        """Test invalidating a range of registers."""
        values = [100, 200, 300, 400, 500]
        self.cache.set_range(self.controller_key, 5000, values, ttl_seconds=60)
        assert self.cache.is_range_cached(self.controller_key, 5000, 5) is True

        self.cache.invalidate_range(self.controller_key, 5001, 3)

        # 5000 and 5004 should still be cached
        assert self.cache.get(self.controller_key, 5000) == 100
        assert self.cache.get(self.controller_key, 5004) == 500
        # 5001-5003 should be invalidated
        assert self.cache.get(self.controller_key, 5001) is None
        assert self.cache.get(self.controller_key, 5002) is None
        assert self.cache.get(self.controller_key, 5003) is None

    def test_clear_all(self):
        """Test clearing the entire cache."""
        self.cache.set(self.controller_key, 5000, 100, ttl_seconds=60)
        self.cache.set("other_controller", 5000, 200, ttl_seconds=60)
        assert len(self.cache._cache) == 2

        self.cache.clear()
        assert len(self.cache._cache) == 0

    def test_clear_by_controller(self):
        """Test clearing cache for a specific controller only."""
        self.cache.set(self.controller_key, 5000, 100, ttl_seconds=60)
        self.cache.set(self.controller_key, 5001, 101, ttl_seconds=60)
        self.cache.set("other_controller", 5000, 200, ttl_seconds=60)
        assert len(self.cache._cache) == 3

        self.cache.clear(self.controller_key)

        # Only other_controller entry should remain
        assert len(self.cache._cache) == 1
        assert self.cache.get("other_controller", 5000) == 200

    def test_stats(self):
        """Test getting cache statistics."""
        with patch("custom_components.sungrow_modbus.helpers.time.monotonic") as mock_time:
            mock_time.return_value = 0

            # Add 3 entries
            self.cache.set(self.controller_key, 5000, 100, ttl_seconds=60)
            self.cache.set(self.controller_key, 5001, 101, ttl_seconds=30)
            self.cache.set(self.controller_key, 5002, 102, ttl_seconds=90)

            stats = self.cache.stats()
            assert stats["total_entries"] == 3
            assert stats["expired_entries"] == 0

            # At time 40, one entry is expired
            mock_time.return_value = 40
            stats = self.cache.stats()
            assert stats["total_entries"] == 3
            assert stats["expired_entries"] == 1

    def test_different_controllers_isolated(self):
        """Test that different controllers have isolated caches."""
        self.cache.set("controller_a", 5000, 100, ttl_seconds=60)
        self.cache.set("controller_b", 5000, 200, ttl_seconds=60)

        assert self.cache.get("controller_a", 5000) == 100
        assert self.cache.get("controller_b", 5000) == 200

    def test_overwrite_value(self):
        """Test that setting a value overwrites the previous one."""
        self.cache.set(self.controller_key, 5000, 100, ttl_seconds=60)
        assert self.cache.get(self.controller_key, 5000) == 100

        self.cache.set(self.controller_key, 5000, 200, ttl_seconds=60)
        assert self.cache.get(self.controller_key, 5000) == 200


class TestGetRegisterCache:
    """Tests for the get_register_cache helper function."""

    def test_creates_cache_if_not_exists(self):
        """Test that get_register_cache creates a cache if none exists."""
        from custom_components.sungrow_modbus.const import DOMAIN, REGISTER_CACHE

        hass = MagicMock()
        hass.data = {}

        cache = get_register_cache(hass)

        assert isinstance(cache, RegisterCache)
        assert DOMAIN in hass.data
        assert REGISTER_CACHE in hass.data[DOMAIN]
        assert hass.data[DOMAIN][REGISTER_CACHE] is cache

    def test_returns_existing_cache(self):
        """Test that get_register_cache returns existing cache instance."""
        from custom_components.sungrow_modbus.const import DOMAIN, REGISTER_CACHE

        existing_cache = RegisterCache()
        hass = MagicMock()
        hass.data = {DOMAIN: {REGISTER_CACHE: existing_cache}}

        cache = get_register_cache(hass)

        assert cache is existing_cache

    def test_preserves_other_domain_data(self):
        """Test that get_register_cache doesn't overwrite other domain data."""
        from custom_components.sungrow_modbus.const import DOMAIN, REGISTER_CACHE

        hass = MagicMock()
        hass.data = {DOMAIN: {"other_key": "other_value"}}

        get_register_cache(hass)

        assert hass.data[DOMAIN]["other_key"] == "other_value"
        assert REGISTER_CACHE in hass.data[DOMAIN]
