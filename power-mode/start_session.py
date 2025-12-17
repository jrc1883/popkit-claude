#!/usr/bin/env python3
"""
Start Power Mode session with Upstash coordination
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add power-mode to path
sys.path.insert(0, str(Path(__file__).parent))

from upstash_adapter import get_redis_client, is_upstash_available
from protocol import create_objective, AgentIdentity, MessageFactory, MessageType

def start_power_mode_session(objective_text: str, issues: list):
    """Initialize Power Mode session with Upstash Redis."""

    print("\n" + "="*70)
    print("  STARTING POWER MODE SESSION (UPSTASH REDIS)")
    print("="*70)

    # Check Upstash availability
    if not is_upstash_available():
        print("\n[ERROR] Upstash Redis not configured")
        print("\nRequired environment variables:")
        print("  - UPSTASH_REDIS_REST_URL")
        print("  - UPSTASH_REDIS_REST_TOKEN")
        return False

    print("\n[OK] Upstash Redis credentials found")

    # Get Redis client
    try:
        redis_client = get_redis_client()
        print(f"[OK] Connected to Upstash: {os.getenv('UPSTASH_REDIS_REST_URL')}")
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to Upstash: {e}")
        return False

    # Create session ID
    session_id = f"power-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Create objective
    objective = create_objective(
        description=objective_text,
        success_criteria=[
            "All issues completed",
            "Documentation updated",
            "Tests passing"
        ],
        phases=["explore", "design", "implement", "test", "review"],
        file_patterns=["packages/plugin/**/*.md", "docs/**/*.md"],
        restricted_tools=["Write:.env", "Edit:secrets/"]
    )

    # Initialize session in Redis
    # Convert objective to JSON-serializable dict
    objective_dict = {
        "description": objective.description,
        "success_criteria": objective.success_criteria,
        "phases": objective.phases
    }

    session_data = {
        "session_id": session_id,
        "objective": objective_dict,
        "issues": issues,
        "started_at": datetime.now().isoformat(),
        "mode": "upstash_redis",
        "agents": [],
        "insights": [],
        "phase": "initializing"
    }

    # Store session in Redis
    try:
        redis_client.set(
            f"popkit:session:{session_id}",
            json.dumps(session_data),
            ex=7200  # 2 hour expiry
        )
        print(f"\n[OK] Session created: {session_id}")
    except Exception as e:
        print(f"\n[ERROR] Failed to create session in Redis: {e}")
        return False

    # Create coordination channels
    channels = [
        "popkit:broadcast",
        "popkit:heartbeat",
        "popkit:results",
        "popkit:insights",
        "popkit:coordinator"
    ]

    for channel in channels:
        try:
            # Publish init message to each channel
            init_msg = MessageFactory.create_broadcast(
                sender_id="coordinator",
                content=f"Session {session_id} initialized",
                metadata={"session_id": session_id, "issues": issues}
            )
            redis_client.publish(channel, init_msg.to_json())
        except Exception as e:
            print(f"[WARN] Could not init channel {channel}: {e}")

    print(f"\n[OK] Coordination channels initialized")

    # Save session state locally
    state_file = Path.home() / ".claude" / "popkit" / "power-mode-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)

    local_state = {
        "active": True,
        "mode": "upstash_redis",
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "objective": objective_text,
        "issues": issues,
        "phases": objective.phases,
        "current_phase": "explore",
        "agents": [],
        "upstash_url": os.getenv('UPSTASH_REDIS_REST_URL'),
        "last_updated": datetime.now().isoformat()
    }

    with open(state_file, 'w') as f:
        json.dump(local_state, f, indent=2)

    print(f"[OK] Local state saved: {state_file}")

    print("\n" + "="*70)
    print("  POWER MODE SESSION READY")
    print("="*70)
    print(f"\nSession ID: {session_id}")
    print(f"Objective: {objective_text}")
    print(f"Issues: {', '.join(f'#{i}' for i in issues)}")
    print(f"Mode: Upstash Redis")
    print(f"Coordination: {len(channels)} channels active")
    print("\nNext: Spawn parallel agents with Task tool")
    print("="*70 + "\n")

    return {
        "session_id": session_id,
        "redis_client": redis_client,
        "channels": channels
    }


if __name__ == "__main__":
    # Test session start
    result = start_power_mode_session(
        objective_text="Parallel documentation development with 3 agents",
        issues=[269, 261, 260]
    )

    if result:
        print("\n[SUCCESS] Power Mode session started successfully!")
        print(f"Session ID: {result['session_id']}")
    else:
        print("\n[FAILED] Failed to start Power Mode session")
        sys.exit(1)
