#!/usr/bin/env python3
"""
Deploy Configuration Creation Script.

Generates deploy.json configuration file from detection results and user input.

Usage:
    python create_config.py --project-type TYPE --targets TARGET1,TARGET2 --state STATE [--detection FILE]

Output:
    Creates .claude/popkit/deploy.json
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def get_git_user() -> str:
    """Get git user.name for history tracking."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_popkit_version() -> str:
    """Get PopKit version from plugin.json."""
    try:
        # Try to find plugin.json
        plugin_paths = [
            Path(".claude-plugin/plugin.json"),
            Path("packages/plugin/.claude-plugin/plugin.json"),
            Path("../.claude-plugin/plugin.json"),
        ]

        for plugin_path in plugin_paths:
            if plugin_path.exists():
                plugin_data = json.loads(plugin_path.read_text())
                return f"popkit-{plugin_data.get('version', '1.0.0')}"
    except Exception:
        pass
    return "popkit-1.0.0"


def create_deploy_config(
    project_type: str,
    targets: List[str],
    state: str,
    detection: Dict[str, Any],
    output_path: Path
) -> Dict[str, Any]:
    """Create deploy.json configuration."""

    timestamp = datetime.utcnow().isoformat() + "Z"
    user = get_git_user()
    version = get_popkit_version()

    config = {
        "version": "1.0",
        "project_type": project_type,
        "language": detection.get("language", "unknown"),
        "framework": detection.get("framework", "generic"),
        "targets": targets,
        "state": state,
        "initialized_at": timestamp,
        "initialized_by": version,
        "github": detection.get("github", {
            "initialized": False,
            "repo": None,
            "default_branch": None,
            "has_actions": False
        }),
        "cicd": detection.get("cicd", {
            "detected": False,
            "platform": None,
            "workflow_count": 0
        }),
        "gaps": detection.get("gaps", {
            "needs_github": True,
            "needs_cicd": True,
            "needs_target_configs": True
        }),
        "history": [
            {
                "action": "init",
                "timestamp": timestamp,
                "user": user,
                "version": version
            }
        ]
    }

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write configuration
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    return config


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create deploy.json configuration")
    parser.add_argument("--project-type", required=True, help="Project type (web-app, backend-api, etc.)")
    parser.add_argument("--targets", required=True, help="Comma-separated deployment targets")
    parser.add_argument("--state", required=True, help="Project state (fresh, needs-cicd, needs-targets, ready)")
    parser.add_argument("--detection", help="Path to detection JSON file")
    parser.add_argument("--output", default=".claude/popkit/deploy.json", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Print config without writing")
    args = parser.parse_args()

    # Parse targets
    targets = [t.strip() for t in args.targets.split(",")]

    # Load detection results if provided
    detection = {}
    if args.detection:
        detection_path = Path(args.detection)
        if detection_path.exists():
            try:
                detection = json.loads(detection_path.read_text())
            except Exception as e:
                print(f"Error loading detection file: {e}", file=sys.stderr)
                return 1

    output_path = Path(args.output)

    # Check if file already exists
    if output_path.exists() and not args.dry_run:
        print(f"Error: Configuration already exists at {output_path}", file=sys.stderr)
        print("Use --force to overwrite or run /popkit:deploy init --force", file=sys.stderr)
        return 1

    # Create configuration
    try:
        config = create_deploy_config(
            project_type=args.project_type,
            targets=targets,
            state=args.state,
            detection=detection,
            output_path=output_path if not args.dry_run else Path("/tmp/deploy.json")
        )

        if args.dry_run:
            print("Dry run - configuration not written")
            print(json.dumps(config, indent=2))
        else:
            print(f"✅ Deploy configuration created: {output_path}")
            print(json.dumps(config, indent=2))

        return 0

    except Exception as e:
        print(f"Error creating configuration: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
