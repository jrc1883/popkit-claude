#!/usr/bin/env python3
"""
Notification Hook
Handles notifications with logging and optional TTS.
"""

import sys
import json
from pathlib import Path

def create_logs_directory():
    """Create logs directory if it doesn't exist."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def log_notification(data):
    """Log notification data to JSON file."""
    logs_dir = create_logs_directory()
    log_file = logs_dir / "notification.json"
    
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

def announce_notification(message):
    """Announce notification using TTS if available and requested."""
    try:
        import os
        import subprocess
        
        # Simple TTS using system capabilities (Windows)
        if os.name == 'nt':
            subprocess.run([
                'powershell', '-Command', 
                f'Add-Type -AssemblyName System.Speech; '
                f'$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                f'$synth.Speak("{message}")'
            ], check=False, capture_output=True)
    except Exception:
        pass  # Silent failure for TTS

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Log the notification
        log_notification(data)

        # Check if TTS notification is requested via data
        should_notify = data.get("notify", data.get("tts", False))
        if should_notify:
            message = data.get('message', 'Notification')
            announce_notification(message)

        # Output JSON response to stdout
        from datetime import datetime
        response = {
            "status": "success",
            "message": "Notification logged",
            "timestamp": datetime.now().isoformat(),
            "tts_announced": should_notify
        }
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in notification hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()