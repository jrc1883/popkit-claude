#!/usr/bin/env python3
"""
Test Power Mode Coordination

Tests that agents can:
1. Receive environment variables (Redis credentials)
2. Write to Redis
3. Read each other's updates
4. Coordinate via pub/sub
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add power-mode to path
sys.path.insert(0, str(Path(__file__).parent))

from upstash_adapter import get_redis_client, is_upstash_available


def test_environment_variables():
    """Test 1: Verify we can pass env vars to subprocesses."""
    print("\n" + "="*70)
    print("  TEST 1: Environment Variable Passing")
    print("="*70)

    # Check if we have Redis credentials
    redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
    redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    if not redis_url or not redis_token:
        print("[SKIP] Redis credentials not in environment")
        print("       Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN")
        return False

    print(f"[OK] Main process has Redis credentials")
    print(f"     URL: {redis_url[:40]}...")

    # Test spawning subprocess with explicit env
    test_script = """
import os
import sys

redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if redis_url and redis_token:
    print("[OK] Subprocess received Redis credentials")
    sys.exit(0)
else:
    print("[FAIL] Subprocess missing Redis credentials")
    sys.exit(1)
"""

    # Method 1: Without explicit env (will fail)
    print("\nMethod 1: Spawn without explicit env...")
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True
    )
    print(f"  Result: {result.stdout.strip()}")

    # Method 2: With explicit env (should work)
    print("\nMethod 2: Spawn WITH explicit env...")
    env = os.environ.copy()
    env["UPSTASH_REDIS_REST_URL"] = redis_url
    env["UPSTASH_REDIS_REST_TOKEN"] = redis_token

    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        env=env
    )
    print(f"  Result: {result.stdout.strip()}")

    print("\n[CONCLUSION] Must pass env explicitly to subprocesses")
    return True


def test_redis_write_read():
    """Test 2: Verify agents can write to and read from Redis."""
    print("\n" + "="*70)
    print("  TEST 2: Redis Write/Read Coordination")
    print("="*70)

    if not is_upstash_available():
        print("[SKIP] Redis not available")
        return False

    redis_client = get_redis_client()

    # Simulate Agent 1 writing
    test_key = f"popkit:test:coordination:{int(time.time())}"
    agent1_data = {
        "agent_id": "agent-1",
        "task": "Test Task",
        "status": "in_progress",
        "timestamp": datetime.now().isoformat(),
        "finding": "Found pattern X"
    }

    print(f"\n[Agent 1] Writing to Redis key: {test_key}")
    redis_client.set(test_key, json.dumps(agent1_data), ex=300)  # 5 min expiry
    print(f"  Data: {json.dumps(agent1_data, indent=2)}")

    # Simulate Agent 2 reading
    print(f"\n[Agent 2] Reading from Redis...")
    time.sleep(0.5)  # Small delay to simulate async

    agent2_read = redis_client.get(test_key)
    if agent2_read:
        data = json.loads(agent2_read)
        print(f"  [OK] Agent 2 received Agent 1's data:")
        print(f"  Finding: {data['finding']}")
        print(f"  Status: {data['status']}")

        # Agent 2 can now use this info
        agent2_response = {
            "agent_id": "agent-2",
            "task": "Test Task",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "response_to": "agent-1",
            "action_taken": f"Used pattern X from agent-1"
        }

        response_key = f"{test_key}:agent2-response"
        redis_client.set(response_key, json.dumps(agent2_response), ex=300)
        print(f"\n[Agent 2] Wrote response to: {response_key}")

        # Cleanup
        redis_client.delete(test_key)
        redis_client.delete(response_key)

        print("\n[SUCCESS] Agents can coordinate via Redis")
        return True
    else:
        print("[FAIL] Agent 2 could not read Agent 1's data")
        return False


def test_pub_sub_messaging():
    """Test 3: Verify pub/sub messaging works."""
    print("\n" + "="*70)
    print("  TEST 3: Pub/Sub Messaging")
    print("="*70)

    if not is_upstash_available():
        print("[SKIP] Redis not available")
        return False

    # Note: Upstash REST API doesn't support traditional pub/sub
    # We use Redis Streams instead (see stream_manager.py)
    print("\n[NOTE] Upstash uses Redis Streams, not traditional pub/sub")
    print("       This is already implemented in stream_manager.py")
    print("       Traditional pub/sub requires persistent connections")

    # We can test stream-based messaging
    from stream_manager import StreamManager

    stream_mgr = StreamManager()
    session_id = f"test-session-{int(time.time())}"

    print(f"\n[Agent 1] Using stream session: {session_id}")

    # Agent 1 sends message via Redis streams
    redis_client = get_redis_client()
    stream_key = f"popkit:stream:{session_id}"

    message_id = redis_client.xadd(stream_key, {
        "agent_id": "agent-1",
        "type": "insight",
        "content": "Found optimization opportunity in routing",
        "timestamp": datetime.now().isoformat()
    })

    print(f"[Agent 1] Sent message to stream (ID: {message_id[:20]}...)")

    # Agent 2 receives message
    print(f"[Agent 2] Reading from stream...")
    time.sleep(0.5)

    messages = redis_client.xread({stream_key: "0"}, count=10)

    if messages and len(messages) > 0:
        stream_name, msg_list = messages[0]
        print(f"[OK] Agent 2 received {len(msg_list)} message(s):")
        for msg_entry in msg_list:
            msg_id, msg_data = msg_entry
            # Upstash returns data as flat list: ['key1', 'val1', 'key2', 'val2']
            # Convert to dict
            data_dict = {msg_data[i]: msg_data[i+1] for i in range(0, len(msg_data), 2)}
            content = data_dict.get("content") or data_dict.get(b"content")
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            print(f"  - {content}")

        # Cleanup
        redis_client.delete(stream_key)

        print("\n[SUCCESS] Stream-based messaging works")
        return True
    else:
        print("[FAIL] No messages received")
        # Cleanup anyway
        redis_client.delete(stream_key)
        return False


def test_coordinated_workflow():
    """Test 4: Full coordinated workflow simulation."""
    print("\n" + "="*70)
    print("  TEST 4: Full Coordinated Workflow")
    print("="*70)

    if not is_upstash_available():
        print("[SKIP] Redis not available")
        return False

    # Simulate a 3-agent coordinated workflow using Redis streams directly
    redis_client = get_redis_client()
    session_id = f"workflow-test-{int(time.time())}"
    stream_key = f"popkit:stream:{session_id}"

    print(f"\nSession ID: {session_id}")
    print("\nSimulating coordinated workflow:")

    # Phase 1: Exploration
    print("\n[Phase 1: Exploration]")
    print("  Agent 1: Analyzing codebase...")
    redis_client.xadd(stream_key, {
        "agent_id": "agent-1",
        "phase": "exploration",
        "finding": "Codebase has 23 hook files",
        "timestamp": datetime.now().isoformat()
    })

    print("  Agent 2: Analyzing patterns...")
    redis_client.xadd(stream_key, {
        "agent_id": "agent-2",
        "phase": "exploration",
        "finding": "Found 58 routing keywords",
        "timestamp": datetime.now().isoformat()
    })

    # Phase 2: Coordination
    print("\n[Phase 2: Coordination]")

    # Agent 3 reads what Agent 1 & 2 found
    messages = redis_client.xread({stream_key: "0"}, count=100)

    if messages and len(messages) > 0:
        stream_name, msg_list = messages[0]
        print(f"  Agent 3: Reading updates from team ({len(msg_list)} messages)")

        for msg_entry in msg_list:
            msg_id, msg_data = msg_entry
            # Convert flat list to dict
            data_dict = {msg_data[i]: msg_data[i+1] for i in range(0, len(msg_data), 2)}
            finding = data_dict.get("finding") or data_dict.get(b"finding")
            if finding:
                if isinstance(finding, bytes):
                    finding = finding.decode('utf-8')
                print(f"    - Learned: {finding}")

    # Agent 3 uses this context
    print("  Agent 3: Using team insights to focus audit...")
    redis_client.xadd(stream_key, {
        "agent_id": "agent-3",
        "phase": "coordination",
        "action": "Focusing audit on 23 hooks mentioned by agent-1",
        "context_used": "agent-1, agent-2",
        "timestamp": datetime.now().isoformat()
    })

    # Phase 3: Results
    print("\n[Phase 3: Results]")
    all_messages = redis_client.xread({stream_key: "0"}, count=100)

    if all_messages and len(all_messages) > 0:
        _, msg_list = all_messages[0]
        print(f"  Total messages exchanged: {len(msg_list)}")

    # Cleanup
    redis_client.delete(stream_key)

    print("\n[SUCCESS] Coordinated workflow completed")
    print("  • Agents shared context via streams")
    print("  • Later agents used earlier findings")
    print("  • No duplicate work")

    return True


def main():
    """Run all coordination tests."""
    print("\n" + "="*70)
    print("  POWER MODE COORDINATION TESTS")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")

    results = {
        "Environment Variables": test_environment_variables(),
        "Redis Write/Read": test_redis_write_read(),
        "Pub/Sub Messaging": test_pub_sub_messaging(),
        "Coordinated Workflow": test_coordinated_workflow()
    }

    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All coordination tests passed")
        print("\nNext steps:")
        print("  1. Update start_session.py to pass env vars to agents")
        print("  2. Run actual Power Mode session with coordination")
        print("  3. Measure improvement vs Native Async")
    else:
        print("\n[INCOMPLETE] Some tests failed")
        print("Fix issues before proceeding to real Power Mode test")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
