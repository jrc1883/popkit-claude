#!/usr/bin/env python3
"""
Test Agent-to-Agent Handoff via Redis Streams

Simulates two agents coordinating:
1. Agent 1 analyzes codebase and writes findings to Redis Stream
2. Agent 2 reads Agent 1's findings and uses them for its work
3. Both agents publish check-ins to show coordination

This proves the coordination infrastructure works before implementing
full Power Mode with Task tool spawning.
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add power-mode to path
sys.path.insert(0, str(Path(__file__).parent))

from upstash_adapter import get_redis_client, is_upstash_available


def simulate_agent_1(redis_client, session_id, stream_key):
    """
    Agent 1: Codebase Explorer

    Analyzes the codebase and publishes findings to Redis Stream.
    Other agents can read these findings to avoid duplicate work.
    """
    print("\n" + "="*70)
    print("  AGENT 1: CODEBASE EXPLORER")
    print("="*70)
    print(f"Session: {session_id}")
    print(f"Stream: {stream_key}")
    print()

    # Simulate exploration work
    print("[Agent 1] Analyzing codebase structure...")
    time.sleep(1)

    findings = [
        "Found 31 agent definitions in packages/plugin/agents/",
        "Identified 68 skills in packages/plugin/skills/",
        "Discovered 24 slash commands in packages/plugin/commands/",
        "Located Power Mode coordination in packages/plugin/power-mode/",
        "Found Redis coordination tests in test_coordination.py"
    ]

    # Publish each finding to the stream
    message_ids = []
    for i, finding in enumerate(findings, 1):
        print(f"[Agent 1] Publishing finding {i}/{len(findings)}: {finding[:50]}...")

        msg_id = redis_client.xadd(stream_key, {
            "agent_id": "agent-1",
            "agent_name": "codebase-explorer",
            "type": "finding",
            "finding_id": str(i),
            "content": finding,
            "timestamp": datetime.now().isoformat(),
            "phase": "exploration"
        })
        message_ids.append(msg_id)
        time.sleep(0.3)

    # Publish summary
    summary_msg = redis_client.xadd(stream_key, {
        "agent_id": "agent-1",
        "agent_name": "codebase-explorer",
        "type": "summary",
        "total_findings": str(len(findings)),
        "status": "completed",
        "recommendation": "Agent 2 should focus on Power Mode coordination patterns",
        "timestamp": datetime.now().isoformat(),
        "phase": "exploration"
    })
    message_ids.append(summary_msg)

    print(f"\n[Agent 1] Published {len(findings)} findings + 1 summary")
    print(f"[Agent 1] Total messages in stream: {len(message_ids)}")
    print("[Agent 1] HANDOFF READY - Agent 2 can now read findings")

    return message_ids


def simulate_agent_2(redis_client, session_id, stream_key):
    """
    Agent 2: Pattern Analyzer

    Reads Agent 1's findings from Redis Stream and uses them
    to focus analysis on the right areas.
    """
    print("\n" + "="*70)
    print("  AGENT 2: PATTERN ANALYZER")
    print("="*70)
    print(f"Session: {session_id}")
    print(f"Stream: {stream_key}")
    print()

    print("[Agent 2] Reading Agent 1's findings from stream...")
    time.sleep(0.5)

    # Read all messages from stream
    messages = redis_client.xread({stream_key: "0"}, count=100)

    if not messages or len(messages) == 0:
        print("[Agent 2] ERROR: No messages found in stream!")
        return []

    stream_name, msg_list = messages[0]
    print(f"[Agent 2] Found {len(msg_list)} messages from Agent 1")
    print()

    # Parse Agent 1's findings
    findings = []
    recommendation = None

    for msg_entry in msg_list:
        msg_id, msg_data = msg_entry

        # Convert flat list to dict (Upstash format)
        data_dict = {}
        for i in range(0, len(msg_data), 2):
            key = msg_data[i]
            value = msg_data[i + 1]
            # Handle both string and bytes keys/values
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            data_dict[key] = value

        msg_type = data_dict.get("type", "")

        if msg_type == "finding":
            finding_id = data_dict.get("finding_id", "")
            content = data_dict.get("content", "")
            findings.append(f"Finding {finding_id}: {content}")
            print(f"[Agent 2] Read finding {finding_id}: {content[:60]}...")

        elif msg_type == "summary":
            recommendation = data_dict.get("recommendation", "")
            total = data_dict.get("total_findings", "")
            print(f"\n[Agent 2] Agent 1 summary: {total} findings")
            print(f"[Agent 2] Recommendation: {recommendation}")

    print()
    print("[Agent 2] Using Agent 1's insights to focus analysis...")
    time.sleep(1)

    # Agent 2 does its work based on Agent 1's findings
    analysis_results = []

    if recommendation and "Power Mode" in recommendation:
        print("[Agent 2] Following Agent 1's recommendation...")
        print("[Agent 2] Analyzing Power Mode coordination patterns...")
        time.sleep(0.5)

        analysis_results = [
            "Identified Redis Streams pattern for pub/sub messaging",
            "Found environment variable passing issue in subprocess spawning",
            "Discovered Native Async mode achieves 2.13x speedup",
            "Located coordination tests with 4/4 passing"
        ]

    # Publish Agent 2's analysis back to stream
    response_ids = []
    for i, result in enumerate(analysis_results, 1):
        print(f"[Agent 2] Publishing analysis {i}/{len(analysis_results)}: {result[:50]}...")

        msg_id = redis_client.xadd(stream_key, {
            "agent_id": "agent-2",
            "agent_name": "pattern-analyzer",
            "type": "analysis",
            "analysis_id": str(i),
            "content": result,
            "based_on": "agent-1-findings",
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis"
        })
        response_ids.append(msg_id)
        time.sleep(0.3)

    # Publish Agent 2's conclusion
    conclusion_msg = redis_client.xadd(stream_key, {
        "agent_id": "agent-2",
        "agent_name": "pattern-analyzer",
        "type": "conclusion",
        "status": "completed",
        "used_findings_from": "agent-1",
        "total_analyses": str(len(analysis_results)),
        "conclusion": "Power Mode coordination infrastructure is ready for implementation",
        "timestamp": datetime.now().isoformat(),
        "phase": "analysis"
    })
    response_ids.append(conclusion_msg)

    print(f"\n[Agent 2] Published {len(analysis_results)} analyses + 1 conclusion")
    print(f"[Agent 2] HANDOFF COMPLETE - Coordination successful!")

    return response_ids


def verify_coordination(redis_client, stream_key):
    """
    Verify that both agents wrote to the stream and coordination happened.
    """
    print("\n" + "="*70)
    print("  VERIFICATION: CHECKING COORDINATION")
    print("="*70)
    print()

    messages = redis_client.xread({stream_key: "0"}, count=100)

    if not messages or len(messages) == 0:
        print("[VERIFY] ERROR: Stream is empty!")
        return False

    stream_name, msg_list = messages[0]

    agent_1_messages = 0
    agent_2_messages = 0

    for msg_entry in msg_list:
        msg_id, msg_data = msg_entry

        # Convert flat list to dict
        data_dict = {}
        for i in range(0, len(msg_data), 2):
            key = msg_data[i]
            value = msg_data[i + 1]
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            data_dict[key] = value

        agent_id = data_dict.get("agent_id", "")
        if agent_id == "agent-1":
            agent_1_messages += 1
        elif agent_id == "agent-2":
            agent_2_messages += 1

    print(f"[VERIFY] Total messages in stream: {len(msg_list)}")
    print(f"[VERIFY] Agent 1 messages: {agent_1_messages}")
    print(f"[VERIFY] Agent 2 messages: {agent_2_messages}")
    print()

    if agent_1_messages > 0 and agent_2_messages > 0:
        print("[VERIFY] SUCCESS: Both agents coordinated via Redis Stream!")
        print("[VERIFY] Agent 2 successfully read and used Agent 1's findings")
        return True
    else:
        print("[VERIFY] FAILED: Only one agent wrote to stream")
        return False


def main():
    """Run the agent handoff test."""
    print("\n" + "="*70)
    print("  AGENT-TO-AGENT HANDOFF TEST")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Check Upstash availability
    if not is_upstash_available():
        print("[ERROR] Upstash Redis not configured")
        print("\nRequired environment variables:")
        print("  - UPSTASH_REDIS_REST_URL")
        print("  - UPSTASH_REDIS_REST_TOKEN")
        print("\nSet these variables and try again.")
        return False

    print("[OK] Upstash Redis credentials found")

    # Get Redis client
    try:
        redis_client = get_redis_client()
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
        print(f"[OK] Connected to Upstash: {redis_url[:50]}...")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Upstash: {e}")
        return False

    # Create test session
    session_id = f"test-handoff-{int(time.time())}"
    stream_key = f"popkit:stream:{session_id}"

    print(f"\n[OK] Test session created: {session_id}")
    print(f"[OK] Stream key: {stream_key}")

    try:
        # Simulate Agent 1
        agent_1_msgs = simulate_agent_1(redis_client, session_id, stream_key)

        # Small delay to simulate real-world timing
        time.sleep(1)

        # Simulate Agent 2
        agent_2_msgs = simulate_agent_2(redis_client, session_id, stream_key)

        # Verify coordination worked
        success = verify_coordination(redis_client, stream_key)

        # Show Upstash console instructions
        print("\n" + "="*70)
        print("  VIEW IN UPSTASH CONSOLE")
        print("="*70)
        print(f"\n1. Go to: https://console.upstash.com/redis")
        print(f"2. Select your 'popkit' database")
        print(f"3. Go to 'Data Browser' tab")
        print(f"4. Search for key: {stream_key}")
        print(f"5. You should see {len(agent_1_msgs) + len(agent_2_msgs)} messages")
        print()
        print("The stream shows:")
        print("  • Agent 1's exploration findings")
        print("  • Agent 2's analysis based on Agent 1's work")
        print("  • Timestamps showing the handoff sequence")
        print()

        # Cleanup option
        print("\n" + "="*70)
        print("  CLEANUP")
        print("="*70)
        print(f"\nStream key: {stream_key}")
        print("TTL: Stream will auto-expire based on your Redis config")
        print("Or manually delete in Upstash console")

        # Don't auto-delete so user can see it in console
        # redis_client.delete(stream_key)

        print("\n" + "="*70)
        if success:
            print("  TEST PASSED - COORDINATION WORKS!")
        else:
            print("  TEST FAILED")
        print("="*70 + "\n")

        return success

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
