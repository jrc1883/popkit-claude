#!/usr/bin/env python3
"""
Stop Hook
Handles session termination and cleanup.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

def create_logs_directory():
    """Create logs directory if it doesn't exist."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def log_session_stop(data):
    """Log session stop data to JSON file."""
    logs_dir = create_logs_directory()
    log_file = logs_dir / "stop.json"
    
    # Add timestamp
    data['timestamp'] = datetime.now().isoformat()
    
    # Read existing log data
    log_data = []
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        except json.JSONDecodeError:
            log_data = []
    
    # Append new data
    log_data.append(data)
    
    # Write updated log
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)

def save_chat_transcript(data, chat_file):
    """Save chat transcript to specified file."""
    logs_dir = create_logs_directory()
    transcript_file = logs_dir / chat_file
    
    if 'transcript' in data:
        with open(transcript_file, 'w') as f:
            json.dump(data['transcript'], f, indent=2)

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Log the session stop
        log_session_stop(data)

        # Check if chat saving is requested via data
        save_chat = data.get("save_chat", data.get("chat", False))
        if save_chat and 'transcript' in data:
            save_chat_transcript(data, "chat.json")

        # Print completion message to stderr
        print("Session ended - logs saved", file=sys.stderr)

        # Output JSON response to stdout
        response = {
            "status": "success",
            "message": "Session ended - logs saved",
            "timestamp": datetime.now().isoformat(),
            "chat_saved": save_chat and 'transcript' in data
        }
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in stop hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()