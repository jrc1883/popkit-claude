#!/usr/bin/env python3
"""
Deployment Notification Script.

Send notifications about deployment status.

Usage:
    python notify_deploy.py --status SUCCESS|FAILURE --version VERSION [--platform PLATFORM]

Output:
    JSON object with notification results
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def send_slack_notification(
    webhook_url: str,
    status: str,
    version: str,
    platform: str,
    details: Dict[str, Any]
) -> bool:
    """Send Slack webhook notification."""
    color = "#36a64f" if status == "SUCCESS" else "#ff0000"
    emoji = ":white_check_mark:" if status == "SUCCESS" else ":x:"

    payload = {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Deployment {status}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Version:*\n{version}"},
                        {"type": "mrkdwn", "text": f"*Platform:*\n{platform}"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
                        {"type": "mrkdwn", "text": f"*Environment:*\n{details.get('environment', 'production')}"}
                    ]
                }
            ]
        }]
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        return False


def send_discord_notification(
    webhook_url: str,
    status: str,
    version: str,
    platform: str,
    details: Dict[str, Any]
) -> bool:
    """Send Discord webhook notification."""
    color = 3066993 if status == "SUCCESS" else 15158332  # Green or red

    payload = {
        "embeds": [{
            "title": f"Deployment {status}",
            "color": color,
            "fields": [
                {"name": "Version", "value": version, "inline": True},
                {"name": "Platform", "value": platform, "inline": True},
                {"name": "Environment", "value": details.get("environment", "production"), "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }]
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        return False


def create_github_deployment_status(
    repo: str,
    deployment_id: str,
    status: str,
    environment: str
) -> bool:
    """Create GitHub deployment status."""
    gh_status = "success" if status == "SUCCESS" else "failure"

    try:
        result = subprocess.run(
            [
                "gh", "api",
                f"/repos/{repo}/deployments/{deployment_id}/statuses",
                "-X", "POST",
                "-f", f"state={gh_status}",
                "-f", f"environment={environment}"
            ],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def log_deployment(
    project_dir: Path,
    status: str,
    version: str,
    platform: str,
    details: Dict[str, Any]
) -> bool:
    """Log deployment to local file."""
    log_dir = project_dir / ".popkit" / "deployments"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "history.jsonl"

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": status,
        "version": version,
        "platform": platform,
        "environment": details.get("environment", "production"),
        "details": details
    }

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Send deployment notifications")
    parser.add_argument("--status", required=True, choices=["SUCCESS", "FAILURE"],
                       help="Deployment status")
    parser.add_argument("--version", required=True, help="Version deployed")
    parser.add_argument("--platform", default="unknown", help="Deployment platform")
    parser.add_argument("--environment", default="production", help="Target environment")
    parser.add_argument("--slack-webhook", help="Slack webhook URL")
    parser.add_argument("--discord-webhook", help="Discord webhook URL")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()

    details = {
        "environment": args.environment
    }

    results = {
        "notifications_sent": [],
        "notifications_failed": []
    }

    # Try environment variables for webhooks
    slack_url = args.slack_webhook or os.environ.get("SLACK_WEBHOOK_URL")
    discord_url = args.discord_webhook or os.environ.get("DISCORD_WEBHOOK_URL")

    # Send Slack notification
    if slack_url:
        success = send_slack_notification(
            slack_url, args.status, args.version, args.platform, details
        )
        if success:
            results["notifications_sent"].append("slack")
        else:
            results["notifications_failed"].append("slack")

    # Send Discord notification
    if discord_url:
        success = send_discord_notification(
            discord_url, args.status, args.version, args.platform, details
        )
        if success:
            results["notifications_sent"].append("discord")
        else:
            results["notifications_failed"].append("discord")

    # Log locally
    log_deployment(project_dir, args.status, args.version, args.platform, details)
    results["notifications_sent"].append("local_log")

    report = {
        "operation": "notify_deploy",
        "status": args.status,
        "version": args.version,
        "platform": args.platform,
        "environment": args.environment,
        **results
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
