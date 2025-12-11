#!/usr/bin/env python3
"""
Session Start Hook
Handles session initialization, setup, and update notifications.

Responsibilities:
1. Log session start
2. Check for PopKit updates
3. Register project with PopKit Cloud
4. Ensure PopKit directories exist (auto-init)
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Import version check utility
try:
    from utils.version import check_for_updates, format_update_notification, get_current_version
    HAS_VERSION_CHECK = True
except ImportError:
    HAS_VERSION_CHECK = False

# Import project registration client
try:
    from utils.project_client import ProjectClient, ProjectRegistration
    HAS_PROJECT_CLIENT = True
except ImportError:
    HAS_PROJECT_CLIENT = False

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


def register_project():
    """Register this project with PopKit Cloud.

    This is non-blocking - any errors are silently ignored.
    Enables cross-project observability via /popkit:project observe.
    """
    if not HAS_PROJECT_CLIENT:
        return None

    try:
        client = ProjectClient()

        if not client.is_available:
            return None

        result = client.register_project()

        if result:
            print(f"Project registered with PopKit Cloud (session #{result.session_count})", file=sys.stderr)
            return {
                'project_id': result.project_id,
                'session_count': result.session_count,
                'status': result.status
            }
    except Exception:
        pass  # Silent failure - never block session start

    return None


def ensure_popkit_directories():
    """Ensure PopKit runtime directories exist.

    This is idempotent and fast - creates directories only if missing.
    Part of the skill automation architecture (Issue #173).

    Created directories:
    - .claude/popkit/           - PopKit runtime state
    - .claude/popkit/routines/  - Custom morning/nightly routines

    Returns:
        dict: Status of directory creation, or None on error
    """
    try:
        cwd = Path(os.getcwd())

        # Skip if not in a git repo or project directory
        # (Don't auto-create in random directories)
        if not (cwd / ".git").exists() and not (cwd / "CLAUDE.md").exists():
            return None

        base = cwd / ".claude" / "popkit"
        dirs_to_create = [
            base,
            base / "routines" / "morning",
            base / "routines" / "nightly",
        ]

        created = []
        for d in dirs_to_create:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(str(d.relative_to(cwd)))

                # Add .gitkeep for empty directories
                gitkeep = d / ".gitkeep"
                if not gitkeep.exists():
                    gitkeep.touch()

        # Create config.json if missing
        config_path = base / "config.json"
        config_created = False
        if not config_path.exists() and base.exists():
            project_name = cwd.name

            # Generate prefix from project name
            words = project_name.replace('-', ' ').replace('_', ' ').split()
            if len(words) == 1:
                prefix = words[0][:2].lower()
            else:
                prefix = ''.join(word[0].lower() for word in words[:3])

            config = {
                "version": "1.0",
                "project_name": project_name,
                "project_prefix": prefix,
                "default_routines": {
                    "morning": "pk",
                    "nightly": "pk"
                },
                "initialized_at": datetime.now().isoformat(),
                "popkit_version": "1.2.0",
                "tier": "free",
                "features": {
                    "power_mode": "not_configured",
                    "deployments": [],
                    "custom_routines": []
                }
            }

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            config_created = True

        if created or config_created:
            return {
                'directories_created': created,
                'config_created': config_created
            }

        return None  # Nothing needed

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

        # Register project with PopKit Cloud (non-blocking)
        project_info = register_project()

        # Ensure PopKit directories exist (auto-init, non-blocking)
        popkit_init = ensure_popkit_directories()
        if popkit_init:
            dirs = popkit_init.get('directories_created', [])
            config = popkit_init.get('config_created', False)
            if dirs or config:
                parts = []
                if dirs:
                    parts.append(f"directories: {len(dirs)}")
                if config:
                    parts.append("config.json")
                print(f"PopKit auto-init: {', '.join(parts)}", file=sys.stderr)

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

        # Include project registration info if available
        if project_info:
            response["project_registration"] = project_info

        # Include popkit init info if directories were created
        if popkit_init:
            response["popkit_init"] = popkit_init

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