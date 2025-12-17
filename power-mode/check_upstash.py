#!/usr/bin/env python3
"""
Check Upstash Redis session status
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from upstash_adapter import get_redis_client, is_upstash_available

def check_session_status(session_id: str):
    """Check Power Mode session in Upstash."""

    if not is_upstash_available():
        print("[ERROR] Upstash not configured")
        return False

    redis_client = get_redis_client()

    # Get session data
    session_key = f"popkit:session:{session_id}"
    session_data = redis_client.get(session_key)

    if not session_data:
        print(f"[NOT FOUND] Session {session_id} not found in Upstash")
        return False

    # Parse session data (might be nested due to how updates were made)
    session = json.loads(session_data)

    # Unwrap nested "value" keys if present
    while isinstance(session, dict) and 'value' in session and len(session) == 1:
        session = json.loads(session['value'])

    # If still has "value" but with other keys, extract it
    if isinstance(session, dict) and 'value' in session and isinstance(session['value'], str):
        try:
            inner = json.loads(session['value'])
            # Merge the inner data with any agent check-ins at the outer level
            for key in session:
                if key.startswith('agent_') and key not in inner:
                    inner[key] = session[key]
            session = inner
        except (json.JSONDecodeError, TypeError):
            pass  # Use session as-is if inner parse fails

    print("\n" + "="*70)
    print("  UPSTASH REDIS SESSION STATUS")
    print("="*70)

    # Robust field access with fallbacks
    session_id = session.get('session_id', 'unknown')
    mode = session.get('mode', 'unknown')
    started_at = session.get('started_at', 'unknown')
    phase = session.get('phase', 'unknown')

    print(f"\nSession ID: {session_id}")
    print(f"Mode: {mode}")
    print(f"Started: {started_at}")
    print(f"Phase: {phase}")

    # Handle objective (might be dict or already processed)
    objective = session.get('objective', {})
    if isinstance(objective, dict):
        obj_desc = objective.get('description', 'No description')
        obj_phases = objective.get('phases', [])
    else:
        obj_desc = str(objective)
        obj_phases = []

    print(f"\nObjective: {obj_desc}")

    issues = session.get('issues', [])
    print(f"Issues: {', '.join(f'#{i}' for i in issues)}")

    if obj_phases:
        print(f"\nPhases: {' -> '.join(obj_phases)}")

    agents = session.get('agents', [])
    print(f"\nAgents: {len(agents)} registered")
    for agent in agents:
        print(f"  - {agent}")

    # Check for agent check-ins (agent_1, agent_2, agent_3 keys)
    agent_checkins = [k for k in session.keys() if k.startswith('agent_')]
    if agent_checkins:
        print(f"\nAgent Check-ins: {len(agent_checkins)}")
        for agent_key in sorted(agent_checkins):
            agent_data = session[agent_key]
            status = agent_data.get('status', 'unknown')
            task = agent_data.get('task', 'unknown')
            print(f"  {agent_key}: {status} - {task}")

    insights = session.get('insights', [])
    print(f"\nInsights: {len(insights)} shared")
    for insight in insights:
        print(f"  - {insight}")

    # Check for agent heartbeats
    print("\n" + "-"*70)
    print("Checking for agent activity...")

    # List all keys matching pattern
    all_keys = redis_client.keys("popkit:*")
    print(f"\nActive Redis keys: {len(all_keys)}")
    for key in all_keys[:10]:  # Show first 10
        print(f"  - {key}")

    print("\n" + "="*70)
    print("[OK] Session verified in Upstash Redis")
    print("="*70 + "\n")

    return True

if __name__ == "__main__":
    check_session_status("power-20251216-213050")
