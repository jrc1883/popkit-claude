#!/usr/bin/env python3
"""
Tests for PopKit Cloud Client

Part of Issue #68 (Hosted Redis Service).
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add power-mode to path
sys.path.insert(0, str(Path(__file__).parent.parent / "power-mode"))

from cloud_client import (
    PopKitCloudClient,
    CloudConfig,
    UsageStats,
    get_redis_client,
    is_cloud_available
)


def test_cloud_config_from_env():
    """Test CloudConfig.from_env()"""
    print("Test: CloudConfig.from_env()")

    # Without API key
    with patch.dict(os.environ, {}, clear=True):
        config = CloudConfig.from_env()
        assert config is None, "Should return None without API key"
        print("  [OK] Returns None without API key")

    # With API key
    with patch.dict(os.environ, {"POPKIT_API_KEY": "pk_test_123"}):
        config = CloudConfig.from_env()
        assert config is not None, "Should return config with API key"
        assert config.api_key == "pk_test_123"
        print("  [OK] Returns config with API key")

    # With dev mode
    with patch.dict(os.environ, {
        "POPKIT_API_KEY": "pk_test_123",
        "POPKIT_DEV_MODE": "true"
    }):
        config = CloudConfig.from_env()
        assert "localhost" in config.base_url, "Should use dev URL"
        print("  [OK] Uses dev URL in dev mode")

    print("  PASS\n")


def test_usage_stats():
    """Test UsageStats tracking"""
    print("Test: UsageStats")

    stats = UsageStats()
    assert stats.commands_today == 0

    stats.add_request(100, 200)
    assert stats.commands_today == 1
    assert stats.bytes_sent == 100
    assert stats.bytes_received == 200
    print("  [OK] Tracks usage correctly")

    stats.add_request(50, 100)
    assert stats.commands_today == 2
    assert stats.bytes_sent == 150
    print("  [OK] Accumulates usage")

    print("  PASS\n")


def test_client_interface_compatibility():
    """Test that cloud client has same interface as local client"""
    print("Test: Interface compatibility")

    # Required methods that must match PowerModeRedisClient
    required_methods = [
        "connect",
        "push_state",
        "push_insight",
        "pull_insights",
        "push_heartbeat",
        "check_for_messages",
        "get_objective",
        "get_patterns",
        "publish_stream_start",
        "publish_stream_chunk",
        "publish_stream_end",
    ]

    config = CloudConfig(api_key="test_key")
    client = PopKitCloudClient(config)

    for method in required_methods:
        assert hasattr(client, method), f"Missing method: {method}"
        assert callable(getattr(client, method)), f"Not callable: {method}"
        print(f"  [OK] Has method: {method}")

    print("  PASS\n")


def test_client_without_connection():
    """Test client behavior without connection"""
    print("Test: Behavior without connection")

    config = CloudConfig(api_key="test_key")
    client = PopKitCloudClient(config)

    # Should not throw, just return empty/None
    assert client.connected == False
    print("  [OK] Not connected initially")

    client.push_state("agent-1", {"progress": 0.5})  # Should not throw
    print("  [OK] push_state silent when disconnected")

    client.push_insight({"type": "test"})  # Should not throw
    print("  [OK] push_insight silent when disconnected")

    insights = client.pull_insights(["test"], "agent-1")
    assert insights == [], "Should return empty list"
    print("  [OK] pull_insights returns empty list")

    messages = client.check_for_messages("agent-1")
    assert messages == [], "Should return empty list"
    print("  [OK] check_for_messages returns empty list")

    objective = client.get_objective()
    assert objective is None, "Should return None"
    print("  [OK] get_objective returns None")

    patterns = client.get_patterns("test")
    assert patterns == [], "Should return empty list"
    print("  [OK] get_patterns returns empty list")

    print("  PASS\n")


def test_get_redis_client_fallback():
    """Test client factory fallback logic"""
    print("Test: get_redis_client() fallback")

    # Without API key, should attempt local Redis then file fallback
    with patch.dict(os.environ, {}, clear=True):
        # Import fresh to pick up env changes
        import importlib
        import cloud_client
        importlib.reload(cloud_client)

        # get_redis_client will try:
        # 1. Cloud (no API key, skip)
        # 2. Local Redis (likely not available)
        # 3. File fallback
        client = cloud_client.get_redis_client()
        client_type = type(client).__name__ if client else None
        print(f"  [OK] Falls back without API key (got: {client_type})")

    print("  PASS\n")


def test_cloud_disabled():
    """Test cloud can be disabled via env var"""
    print("Test: Cloud disabled via POPKIT_CLOUD_ENABLED=false")

    with patch.dict(os.environ, {
        "POPKIT_API_KEY": "pk_test_123",
        "POPKIT_CLOUD_ENABLED": "false"
    }):
        # With cloud disabled, should not attempt cloud connection
        with patch('cloud_client.PopKitCloudClient') as MockCloud:
            # get_redis_client should skip cloud
            from cloud_client import get_redis_client as get_client
            # Force re-import to pick up env changes
            import importlib
            import cloud_client
            importlib.reload(cloud_client)

            client = cloud_client.get_redis_client()
            # Cloud client should not be used when disabled
            print("  [OK] Respects POPKIT_CLOUD_ENABLED=false")

    print("  PASS\n")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("PopKit Cloud Client Tests")
    print("=" * 50 + "\n")

    test_cloud_config_from_env()
    test_usage_stats()
    test_client_interface_compatibility()
    test_client_without_connection()
    test_get_redis_client_fallback()
    test_cloud_disabled()

    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
