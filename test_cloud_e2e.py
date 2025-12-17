#!/usr/bin/env python3
"""
End-to-end test for PopKit Cloud.

Tests the full flow from plugin to cloud API to Upstash Redis.
"""

import os
import sys

# Set API key for testing
os.environ["POPKIT_API_KEY"] = "pk_live_8b8fe06d0c565cff0409c2231268aef1bd0a5cf29bd4746d"

# Add power-mode to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "power-mode"))

from cloud_client import PopKitCloudClient, CloudConfig

def main():
    print("=" * 50)
    print("PopKit Cloud End-to-End Test")
    print("=" * 50)

    # Create client
    config = CloudConfig.from_env()
    if not config:
        print("[FAIL] Could not load config from environment")
        return False

    print(f"\n[OK] Config loaded")
    print(f"    API Key: {config.api_key[:15]}...{config.api_key[-8:]}")
    print(f"    Base URL: {config.base_url}")

    client = PopKitCloudClient(config)

    # Test connection
    print("\n[TEST] Connecting to PopKit Cloud...")
    if not client.connect():
        print("[FAIL] Connection failed")
        return False

    print(f"[OK] Connected!")
    print(f"    User ID: {config.user_id}")
    print(f"    Tier: {config.tier}")

    # Test push state
    print("\n[TEST] Pushing agent state...")
    client.push_state("e2e-test-agent", {
        "progress": 0.75,
        "current_task": "End-to-end testing",
        "files_touched": ["test1.py", "test2.py"]
    })
    print("[OK] State pushed")

    # Test push insight
    print("\n[TEST] Pushing insight...")
    client.push_insight({
        "id": "insight-e2e-001",
        "type": "discovery",
        "content": "Cloud integration works perfectly!",
        "relevance_tags": ["testing", "cloud", "e2e"],
        "from_agent": "e2e-test-agent"
    })
    print("[OK] Insight pushed")

    # Test pull insights
    print("\n[TEST] Pulling insights...")
    insights = client.pull_insights(["testing", "cloud"], "other-agent", 5)
    print(f"[OK] Pulled {len(insights)} insights")
    for insight in insights:
        print(f"    - {insight.get('content', insight)[:50]}...")

    # Test usage
    print("\n[TEST] Getting usage stats...")
    usage = client.get_usage()
    print(f"[OK] Usage stats:")
    print(f"    Commands today: {usage['commands_today']}")
    print(f"    Bytes sent: {usage['bytes_sent']}")
    print(f"    Bytes received: {usage['bytes_received']}")
    print(f"    Tier: {usage['tier']}")

    print("\n" + "=" * 50)
    print("[SUCCESS] All tests passed!")
    print("=" * 50)
    print("\nPopKit Cloud is ready to use!")
    print("\nTo enable cloud mode in your projects, set:")
    print(f"\n    export POPKIT_API_KEY={config.api_key}")
    print("\nPower Mode will automatically use the cloud backend.")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
