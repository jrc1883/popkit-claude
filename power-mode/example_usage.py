#!/usr/bin/env python3
"""
Power Mode Usage Examples
Shows how to use both Redis and file-based modes.
"""

import time
from coordinator_auto import create_coordinator, get_mode_info
from protocol import create_objective, MessageFactory, InsightType, Insight


def example_1_basic_usage():
    """Example 1: Basic coordinator with auto-detection."""
    print("=== Example 1: Basic Auto-Detection ===\n")

    # Check which mode will be used
    info = get_mode_info()
    print(f"Mode: {info['mode']}")
    print(f"Recommendation: {info['recommendation']}\n")

    # Create objective
    objective = create_objective(
        description="Add login feature",
        success_criteria=["Login endpoint works", "Tests pass"],
        phases=["explore", "implement", "test"]
    )

    # Create coordinator (auto-detects Redis vs file)
    coordinator = create_coordinator(objective)

    if coordinator.start():
        print(f"✓ Coordinator started in {info['mode']} mode\n")

        # Register a couple agents
        agent1 = coordinator.register_agent("code-explorer")
        agent2 = coordinator.register_agent("test-writer")

        print(f"✓ Registered agents:")
        print(f"  - {agent1.name} ({agent1.id})")
        print(f"  - {agent2.name} ({agent2.id})")

        # Get status
        status = coordinator.get_status()
        print(f"\nStatus: {status}")

        coordinator.stop()
    else:
        print("✗ Failed to start coordinator")


def example_2_force_file_mode():
    """Example 2: Force file-based mode even if Redis is available."""
    print("\n=== Example 2: Force File-Based Mode ===\n")

    objective = create_objective(
        description="Refactor auth module",
        success_criteria=["Code is cleaner", "Tests still pass"],
        phases=["analyze", "refactor", "verify"]
    )

    # Force file mode
    coordinator = create_coordinator(objective, force_file_mode=True)

    if coordinator.start():
        print(f"✓ Running in file mode: {coordinator.is_file_mode}")
        print(f"✓ State file: .claude/popkit/power-mode-state.json\n")

        # You can peek at the state file during execution!
        import json
        from pathlib import Path

        state_file = Path(".claude/popkit/power-mode-state.json")
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                print(f"Keys in state: {list(state.keys())}")

        coordinator.stop()
    else:
        print("✗ Failed to start")


def example_3_pub_sub_demo():
    """Example 3: Demonstrate pub/sub with file-based mode."""
    print("\n=== Example 3: Pub/Sub Demo ===\n")

    from file_fallback import FileBasedPowerMode
    import json
    from datetime import datetime

    # Create two clients
    publisher = FileBasedPowerMode()
    subscriber = FileBasedPowerMode()

    # Subscribe
    pubsub = subscriber.pubsub()
    pubsub.subscribe("demo:channel")
    print("✓ Subscribed to demo:channel")

    # Publish messages
    for i in range(3):
        msg = {
            "id": i,
            "content": f"Message {i}",
            "timestamp": datetime.now().isoformat()
        }
        count = publisher.publish("demo:channel", json.dumps(msg))
        print(f"✓ Published message {i} (reached {count} subscribers)")
        time.sleep(0.2)  # Give polling time to catch up

    # Receive messages
    print("\nReceiving messages:")
    for i in range(3):
        msg = pubsub.get_message(timeout=1)
        if msg:
            data = json.loads(msg['data'])
            print(f"  [{i}] {data['content']}")
        else:
            print(f"  [{i}] No message (timeout)")

    print()


def example_4_key_value_ops():
    """Example 4: Key-value and hash operations."""
    print("\n=== Example 4: Key-Value Operations ===\n")

    from file_fallback import FileBasedPowerMode

    client = FileBasedPowerMode()

    # Simple key-value
    client.set("session:123", "active")
    status = client.get("session:123")
    print(f"Session status: {status}")

    # Hash operations (like agent state)
    client.hset("agent:reviewer", mapping={
        "name": "code-reviewer",
        "status": "active",
        "progress": "0.75",
        "current_file": "src/auth.py"
    })

    agent_state = client.hgetall("agent:reviewer")
    print(f"Agent state: {agent_state}")

    # List operations (like task queue)
    client.lpush("tasks:pending", "task-1", "task-2", "task-3")
    tasks = client.lrange("tasks:pending", 0, -1)
    print(f"Pending tasks: {tasks}")

    print()


def example_5_insight_sharing():
    """Example 5: Agents sharing insights."""
    print("\n=== Example 5: Insight Sharing ===\n")

    objective = create_objective(
        description="Fix authentication bugs",
        success_criteria=["All tests pass", "No security issues"],
        phases=["investigate", "fix", "verify"]
    )

    coordinator = create_coordinator(objective)

    if coordinator.start():
        # Register agents
        explorer = coordinator.register_agent("code-explorer")
        reviewer = coordinator.register_agent("code-reviewer")

        print(f"Agents: {explorer.name}, {reviewer.name}\n")

        # Explorer shares an insight
        insight = Insight(
            id="insight-1",
            type=InsightType.DISCOVERY,
            content="Found that auth.py uses deprecated hash function",
            from_agent=explorer.id,
            relevance_tags=["auth", "security", "deprecated"],
            confidence=0.9
        )

        coordinator.insight_pool.add(insight)
        print(f"✓ {explorer.name} shared insight")

        # Reviewer queries for relevant insights
        relevant = coordinator.get_insights_for_agent(
            reviewer.id,
            tags=["auth", "security"]
        )

        print(f"✓ {reviewer.name} found {len(relevant)} relevant insights:")
        for ins in relevant:
            print(f"  - {ins['content'][:50]}... (confidence: {ins['confidence']})")

        coordinator.stop()
        print()


def example_6_cleanup():
    """Example 6: Cleanup old messages."""
    print("\n=== Example 6: State File Cleanup ===\n")

    from file_fallback import get_stats, cleanup_old_messages
    from pathlib import Path

    state_file = Path(".claude/popkit/power-mode-state.json")

    if not state_file.exists():
        print("No state file found (run example 3 first)")
        return

    # Before cleanup
    print("Before cleanup:")
    stats = get_stats(state_file)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Cleanup
    cleanup_old_messages(state_file, max_age_hours=0)  # Remove everything

    # After cleanup
    print("\nAfter cleanup:")
    stats = get_stats(state_file)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print()


def example_7_mode_comparison():
    """Example 7: Compare Redis vs file-based performance."""
    print("\n=== Example 7: Performance Comparison ===\n")

    import time

    # Test file-based
    from file_fallback import FileBasedPowerMode

    client = FileBasedPowerMode()
    pubsub = client.pubsub()
    pubsub.subscribe("perf:test")

    # Measure publish latency
    start = time.time()
    for i in range(10):
        client.publish("perf:test", f"message-{i}")
    file_publish_time = (time.time() - start) / 10

    # Measure receive latency
    start = time.time()
    for i in range(10):
        msg = pubsub.get_message(timeout=0.5)
    file_receive_time = (time.time() - start) / 10

    print("File-based mode:")
    print(f"  Publish latency: {file_publish_time*1000:.2f}ms")
    print(f"  Receive latency: {file_receive_time*1000:.2f}ms")

    # Test Redis if available
    info = get_mode_info()
    if info['redis_running']:
        import redis
        r = redis.Redis(decode_responses=True)
        ps = r.pubsub()
        ps.subscribe("perf:test")

        start = time.time()
        for i in range(10):
            r.publish("perf:test", f"message-{i}")
        redis_publish_time = (time.time() - start) / 10

        start = time.time()
        for i in range(10):
            msg = ps.get_message(timeout=0.5)
        redis_receive_time = (time.time() - start) / 10

        print("\nRedis mode:")
        print(f"  Publish latency: {redis_publish_time*1000:.2f}ms")
        print(f"  Receive latency: {redis_receive_time*1000:.2f}ms")

        print(f"\nSpeedup: {file_publish_time/redis_publish_time:.1f}x faster with Redis")
    else:
        print("\nRedis not running - start it to compare performance")

    print()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    examples = {
        "1": ("Basic auto-detection", example_1_basic_usage),
        "2": ("Force file mode", example_2_force_file_mode),
        "3": ("Pub/sub demo", example_3_pub_sub_demo),
        "4": ("Key-value operations", example_4_key_value_ops),
        "5": ("Insight sharing", example_5_insight_sharing),
        "6": ("Cleanup", example_6_cleanup),
        "7": ("Performance comparison", example_7_mode_comparison),
    }

    if len(sys.argv) > 1:
        # Run specific example
        example_num = sys.argv[1]
        if example_num in examples:
            name, func = examples[example_num]
            print(f"\nRunning: {name}\n")
            func()
        else:
            print(f"Unknown example: {example_num}")
            print(f"Available: {', '.join(examples.keys())}")
    else:
        # Run all examples
        print("=" * 60)
        print("Power Mode Usage Examples")
        print("=" * 60)

        for num, (name, func) in examples.items():
            try:
                func()
            except Exception as e:
                print(f"✗ Example {num} failed: {e}\n")

        print("=" * 60)
        print("Done! Check .claude/popkit/power-mode-state.json to see the state")
        print("=" * 60)
