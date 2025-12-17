#!/usr/bin/env python3
"""
OPTIMUS Agent Observability Hook
Sends agent telemetry data to OPTIMUS Command Center
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# OPTIMUS WebSocket server endpoint
OPTIMUS_WS_URL = "http://localhost:3051"
OPTIMUS_TELEMETRY_ENDPOINT = f"{OPTIMUS_WS_URL}/api/agent/activity"
OPTIMUS_COLLABORATION_ENDPOINT = f"{OPTIMUS_WS_URL}/api/agent/collaboration"

def send_to_optimus(endpoint, data):
    """Send data to OPTIMUS telemetry endpoint"""
    try:
        response = requests.post(
            endpoint,
            json=data,
            timeout=2,
            headers={'Content-Type': 'application/json'}
        )
        return response.status_code == 200
    except Exception as e:
        # Fail silently to not disrupt Claude's workflow
        return False

def track_tool_use(tool_name, tool_args, tool_result=None, execution_time=0):
    """Track tool usage in OPTIMUS"""
    activity_data = {
        "agentName": os.environ.get('CLAUDE_AGENT_NAME', 'claude'),
        "activity": f"tool_use:{tool_name}",
        "metadata": {
            "toolName": tool_name,
            "toolArgs": tool_args,
            "executionTime": execution_time,
            "success": tool_result is not None,
            "sessionId": os.environ.get('CLAUDE_SESSION_ID', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "projectPath": os.getcwd()
        }
    }
    
    send_to_optimus(OPTIMUS_TELEMETRY_ENDPOINT, activity_data)

def track_agent_activation(agent_name, task_type, context=None):
    """Track agent activation in OPTIMUS"""
    activity_data = {
        "agentName": agent_name,
        "activity": f"activation:{task_type}",
        "metadata": {
            "taskType": task_type,
            "context": context or {},
            "sessionId": os.environ.get('CLAUDE_SESSION_ID', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "projectPath": os.getcwd()
        }
    }
    
    send_to_optimus(OPTIMUS_TELEMETRY_ENDPOINT, activity_data)

def track_collaboration(from_agent, to_agent, collaboration_type, metadata=None):
    """Track agent collaboration in OPTIMUS"""
    collab_data = {
        "agentName": from_agent,
        "partnerAgent": to_agent,
        "collaborationType": collaboration_type,
        "metadata": metadata or {}
    }
    
    send_to_optimus(OPTIMUS_COLLABORATION_ENDPOINT, collab_data)

def main():
    """Main hook entry point - JSON stdin/stdout protocol"""
    try:
        # Read JSON input from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Determine event type
        event_type = data.get("event_type", data.get("type", "post-tool-use"))

        if event_type == "post-tool-use" or "tool_name" in data:
            tool_name = data.get("tool_name", "")
            tool_args = data.get("tool_input", data.get("tool_args", {}))
            tool_result = data.get("tool_response", data.get("tool_result"))
            execution_time = data.get("execution_time", 0)

            if tool_name:
                track_tool_use(tool_name, tool_args, tool_result, execution_time)

        elif event_type == "agent-activation":
            agent_name = data.get("agent_name", "")
            task_type = data.get("task_type", "")
            context = data.get("context")

            if agent_name:
                track_agent_activation(agent_name, task_type, context)

        elif event_type == "agent-collaboration":
            from_agent = data.get("from_agent", "")
            to_agent = data.get("to_agent", "")
            collab_type = data.get("collaboration_type", "")
            metadata = data.get("metadata")

            if from_agent and to_agent:
                track_collaboration(from_agent, to_agent, collab_type, metadata)

        # Output JSON response
        response = {
            "status": "success",
            "event_type": event_type,
            "tracked": True,
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))

if __name__ == "__main__":
    main()