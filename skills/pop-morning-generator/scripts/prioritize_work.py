#!/usr/bin/env python3
"""
Work Prioritization Script.

Analyze tasks and issues to determine priorities for the day.

Usage:
    python prioritize_work.py [--source SOURCE] [--mode MODE]

Sources:
    tasks   - From STATUS.json tasks
    issues  - From GitHub issues
    all     - All sources

Modes:
    list - List pending work
    rank - Rank by priority

Output:
    JSON object with prioritized work items
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def run_command(cmd: str, timeout: int = 30) -> Tuple[str, bool]:
    """Run a shell command and return output and success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.returncode == 0
    except subprocess.TimeoutExpired:
        return "Command timed out", False
    except Exception as e:
        return str(e), False


def load_tasks_from_status() -> List[Dict[str, Any]]:
    """Load tasks from STATUS.json."""
    tasks = []

    status_paths = [
        Path(".claude/STATUS.json"),
        Path("STATUS.json"),
    ]

    for path in status_paths:
        if path.exists():
            try:
                status = json.loads(path.read_text())
                task_data = status.get("tasks", {})

                # In-progress tasks (highest priority)
                for task in task_data.get("inProgress", []):
                    tasks.append({
                        "title": task,
                        "source": "STATUS.json",
                        "status": "in_progress",
                        "priority_score": 100
                    })

                # Blocked tasks (need attention)
                for task in task_data.get("blocked", []):
                    tasks.append({
                        "title": task,
                        "source": "STATUS.json",
                        "status": "blocked",
                        "priority_score": 90
                    })

                break
            except Exception as e:
                pass

    return tasks


def load_issues_from_github(limit: int = 10) -> List[Dict[str, Any]]:
    """Load open issues from GitHub."""
    issues = []

    # Try to get issues using gh CLI
    cmd = f"gh issue list --state open --limit {limit} --json number,title,labels"
    output, ok = run_command(cmd)

    if ok and output:
        try:
            gh_issues = json.loads(output)
            for issue in gh_issues:
                # Calculate priority score based on labels
                priority_score = 50  # Default

                labels = [l.get("name", "") for l in issue.get("labels", [])]
                if "P0-critical" in labels:
                    priority_score = 95
                elif "P1-high" in labels:
                    priority_score = 80
                elif "P2-medium" in labels:
                    priority_score = 60
                elif "P3-low" in labels:
                    priority_score = 40

                # Boost for phase:now
                if "phase:now" in labels:
                    priority_score += 5

                issues.append({
                    "number": issue["number"],
                    "title": issue["title"],
                    "source": "GitHub",
                    "status": "open",
                    "labels": labels,
                    "priority_score": priority_score
                })
        except json.JSONDecodeError:
            pass

    return issues


def load_context_hints() -> Dict[str, Any]:
    """Load context hints from STATUS.json."""
    hints = {
        "focus_area": "",
        "next_action": "",
        "blocker": None
    }

    status_paths = [
        Path(".claude/STATUS.json"),
        Path("STATUS.json"),
    ]

    for path in status_paths:
        if path.exists():
            try:
                status = json.loads(path.read_text())
                context = status.get("context", {})
                hints["focus_area"] = context.get("focusArea", "")
                hints["next_action"] = context.get("nextAction", "")
                hints["blocker"] = context.get("blocker")
                break
            except Exception:
                pass

    return hints


def rank_priorities(tasks: List[Dict], issues: List[Dict], context: Dict) -> List[Dict[str, Any]]:
    """Rank all work items by priority."""
    all_items = []

    # Add tasks
    for task in tasks:
        item = {
            "type": "task",
            "title": task["title"],
            "source": task["source"],
            "status": task["status"],
            "priority_score": task["priority_score"]
        }

        # Boost if matches focus area
        if context.get("focus_area") and context["focus_area"].lower() in task["title"].lower():
            item["priority_score"] += 10
            item["focus_match"] = True

        all_items.append(item)

    # Add issues
    for issue in issues:
        item = {
            "type": "issue",
            "number": issue["number"],
            "title": issue["title"],
            "source": issue["source"],
            "status": issue["status"],
            "labels": issue.get("labels", []),
            "priority_score": issue["priority_score"]
        }

        # Boost if matches focus area
        if context.get("focus_area") and context["focus_area"].lower() in issue["title"].lower():
            item["priority_score"] += 10
            item["focus_match"] = True

        all_items.append(item)

    # Sort by priority score (descending)
    all_items.sort(key=lambda x: x["priority_score"], reverse=True)

    return all_items


def suggest_first_action(ranked_items: List[Dict], context: Dict) -> Dict[str, Any]:
    """Suggest what to work on first."""
    suggestion = {
        "action": "",
        "reason": "",
        "command": ""
    }

    # If there's a next action from last session, prioritize it
    if context.get("next_action"):
        suggestion["action"] = context["next_action"]
        suggestion["reason"] = "Continuing from last session"
        suggestion["source"] = "STATUS.json"
        return suggestion

    # If there's a blocker, address it first
    if context.get("blocker"):
        suggestion["action"] = f"Address blocker: {context['blocker']}"
        suggestion["reason"] = "Blocker preventing progress"
        suggestion["source"] = "STATUS.json"
        return suggestion

    # Otherwise, pick top priority item
    if ranked_items:
        top_item = ranked_items[0]
        if top_item["type"] == "issue":
            suggestion["action"] = f"#{top_item['number']}: {top_item['title']}"
            suggestion["reason"] = f"Highest priority issue (score: {top_item['priority_score']})"
            suggestion["command"] = f"/popkit:dev work #{top_item['number']}"
        else:
            suggestion["action"] = top_item["title"]
            suggestion["reason"] = f"Highest priority task (score: {top_item['priority_score']})"

    return suggestion


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prioritize work for the day")
    parser.add_argument("--source", choices=["tasks", "issues", "all"],
                        default="all", help="Source to load")
    parser.add_argument("--mode", choices=["list", "rank", "suggest"],
                        default="rank", help="Output mode")
    parser.add_argument("--limit", type=int, default=10, help="Max issues to load")
    args = parser.parse_args()

    result = {
        "operation": "prioritize_work",
        "source": args.source,
        "timestamp": datetime.now().isoformat()
    }

    tasks = []
    issues = []
    context = load_context_hints()

    if args.source in ["tasks", "all"]:
        tasks = load_tasks_from_status()
        result["tasks"] = {
            "count": len(tasks),
            "items": tasks
        }

    if args.source in ["issues", "all"]:
        issues = load_issues_from_github(args.limit)
        result["issues"] = {
            "count": len(issues),
            "items": issues
        }

    result["context"] = context

    if args.mode in ["rank", "suggest"]:
        ranked = rank_priorities(tasks, issues, context)
        result["ranked"] = {
            "count": len(ranked),
            "items": ranked[:10]  # Top 10
        }

    if args.mode == "suggest":
        suggestion = suggest_first_action(
            result.get("ranked", {}).get("items", []),
            context
        )
        result["suggestion"] = suggestion

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
