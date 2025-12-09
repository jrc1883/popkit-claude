#!/usr/bin/env python3
"""
Session Start Hook
Handles session initialization, setup, and update notifications.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Import version check utility
try:
    from utils.version import check_for_updates, format_update_notification, get_current_version
    HAS_VERSION_CHECK = True
except ImportError:
    HAS_VERSION_CHECK = False

def create_logs_directory():
    """Create logs directory if it doesn't exist."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def log_session_start(data):
    """Log session start data to JSON file."""
    logs_dir = create_logs_directory()
    log_file = logs_dir / "session_start.json"
    
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


def check_plugin_updates():
    """Check for popkit updates and display notification if available.

    This is non-blocking - any errors are silently ignored.
    """
    if not HAS_VERSION_CHECK:
        return None

    try:
        has_update, release_info = check_for_updates()

        if has_update and release_info:
            current = get_current_version()
            notification = format_update_notification(release_info, current)
            print(notification, file=sys.stderr)

            return {
                'update_available': True,
                'current_version': current,
                'latest_version': release_info.get('version'),
                'release_url': release_info.get('url')
            }
    except Exception:
        pass  # Silent failure - never block session start

    return None


def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Log the session start
        log_session_start(data)

        # Check for updates (non-blocking)
        update_info = check_plugin_updates()

        # Print welcome message to stderr
        print("Session started - hooks system active", file=sys.stderr)

        # Output JSON response to stdout
        response = {
            "status": "success",
            "message": "Session started - hooks system active",
            "timestamp": datetime.now().isoformat(),
            "session_data": data
        }

        # Include update info if available
        if update_info:
            response["update_check"] = update_info

        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in session_start hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()