#!/usr/bin/env python3
"""
Action Recommendation Script.

Score, rank, and recommend next actions based on project state.

Usage:
    python recommend_action.py [--mode MODE] [--state-file FILE]

Modes:
    score  - Calculate scores for all possible actions
    rank   - Rank actions by score
    report - Generate recommendation report

Output:
    JSON object with scored and ranked recommendations
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Base priority scores
BASE_PRIORITIES = {
    "fix_build_errors": 90,
    "process_research": 85,
    "commit_work": 80,
    "push_changes": 60,
    "work_on_issue": 50,
    "tackle_tech_debt": 40,
    "start_new_feature": 30,
    "health_check": 20
}

# Context multipliers
MULTIPLIERS = {
    "uncommitted_changes": 20,
    "typescript_errors": 30,
    "research_branches": 25,
    "many_open_issues": 10,
    "high_priority_issue": 15
}


def load_state(state_file: Optional[str] = None) -> Dict[str, Any]:
    """Load project state from file or analyze."""
    if state_file and Path(state_file).exists():
        return json.loads(Path(state_file).read_text())

    # Default empty state
    return {
        "git": {"uncommitted_count": 0, "ahead_count": 0, "urgency": "LOW"},
        "code": {"typescript_errors": 0, "urgency": "LOW"},
        "issues": {"open_count": 0, "issues": [], "urgency": "LOW"},
        "research": {"has_research_branches": False, "branches": [], "urgency": "LOW"}
    }


def calculate_action_scores(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculate scores for all possible actions."""
    actions = []

    git = state.get("git", {})
    code = state.get("code", {})
    issues = state.get("issues", {})
    research = state.get("research", {})

    # Fix build errors
    if code.get("typescript_errors", 0) > 0:
        score = BASE_PRIORITIES["fix_build_errors"] + MULTIPLIERS["typescript_errors"]
        actions.append({
            "id": "fix_build_errors",
            "name": "Fix Build Errors",
            "command": "/popkit:debug",
            "score": score,
            "why": f"TypeScript has {code['typescript_errors']} errors blocking build",
            "what": "Systematic debugging with root cause analysis",
            "benefit": "Unblocked development, passing CI"
        })

    # Process research branches
    if research.get("has_research_branches") and research.get("branches"):
        score = BASE_PRIORITIES["process_research"] + MULTIPLIERS["research_branches"]
        branch_count = len(research["branches"])
        actions.append({
            "id": "process_research",
            "name": "Process Research Branches",
            "command": "Invoke pop-research-merge skill",
            "score": score,
            "why": f"Found {branch_count} research branch(es) from Claude Code Web sessions",
            "what": "Merges research content, organizes docs, creates GitHub issues",
            "benefit": "Research findings become actionable issues in your backlog",
            "branches": research["branches"]
        })

    # Commit uncommitted work
    if git.get("uncommitted_count", 0) > 0:
        score = BASE_PRIORITIES["commit_work"] + MULTIPLIERS["uncommitted_changes"]
        actions.append({
            "id": "commit_work",
            "name": "Commit Current Work",
            "command": "/popkit:git commit",
            "score": score,
            "why": f"You have {git['uncommitted_count']} uncommitted files",
            "what": "Auto-generates commit message matching repo style",
            "benefit": "Clean working directory, changes safely versioned"
        })

    # Push changes
    if git.get("ahead_count", 0) > 0:
        score = BASE_PRIORITIES["push_changes"]
        actions.append({
            "id": "push_changes",
            "name": "Push Changes",
            "command": "/popkit:git push",
            "score": score,
            "why": f"You have {git['ahead_count']} commits ahead of remote",
            "what": "Push changes to remote repository",
            "benefit": "Work backed up and visible to team"
        })

    # Work on issue
    if issues.get("open_count", 0) > 0 and issues.get("issues"):
        top_issue = issues["issues"][0]
        score = BASE_PRIORITIES["work_on_issue"]

        # Boost for priority labels
        labels = [l.get("name", "") for l in top_issue.get("labels", [])]
        if "P0-critical" in labels or "P1-high" in labels:
            score += MULTIPLIERS["high_priority_issue"]

        if issues["open_count"] >= 5:
            score += MULTIPLIERS["many_open_issues"]

        actions.append({
            "id": "work_on_issue",
            "name": "Work on Open Issue",
            "command": f"/popkit:dev work #{top_issue['number']}",
            "score": score,
            "why": f"Issue #{top_issue['number']} \"{top_issue['title']}\" is high priority",
            "what": "Issue-driven development workflow",
            "benefit": "Structured progress on prioritized work",
            "issue": top_issue
        })

    # Health check (always available)
    if not actions or all(a["score"] < 50 for a in actions):
        score = BASE_PRIORITIES["health_check"]
        actions.append({
            "id": "health_check",
            "name": "Check Project Health",
            "command": "/popkit:routine morning",
            "score": score,
            "why": "No urgent items - good time for health check",
            "what": "Comprehensive project status with Ready to Code score",
            "benefit": "Identify hidden issues before they become urgent"
        })

    return actions


def rank_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank actions by score (highest first)."""
    return sorted(actions, key=lambda x: x["score"], reverse=True)


def generate_report(ranked_actions: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate recommendation report."""
    report = {
        "state_summary": {
            "uncommitted": state.get("git", {}).get("uncommitted_count", 0),
            "branch_sync": "ahead" if state.get("git", {}).get("ahead_count", 0) > 0 else "synced",
            "typescript": "errors" if state.get("code", {}).get("typescript_errors", 0) > 0 else "clean",
            "open_issues": state.get("issues", {}).get("open_count", 0),
            "research_branches": len(state.get("research", {}).get("branches", []))
        },
        "recommendations": ranked_actions[:5],  # Top 5
        "quick_reference": [
            {"goal": "Commit changes", "command": "/popkit:git commit"},
            {"goal": "Review code", "command": "/popkit:git review"},
            {"goal": "Project health", "command": "/popkit:routine morning"},
            {"goal": "Plan a feature", "command": "/popkit:dev brainstorm"},
            {"goal": "Debug an issue", "command": "/popkit:debug"}
        ]
    }

    return report


def format_report_display(report: Dict[str, Any]) -> str:
    """Format report for display."""
    lines = []
    state = report["state_summary"]

    lines.append("## Current State\n")
    lines.append("| Indicator | Status | Urgency |")
    lines.append("|-----------|--------|---------|")
    lines.append(f"| Uncommitted | {state['uncommitted']} files | {'HIGH' if state['uncommitted'] > 0 else 'OK'} |")
    lines.append(f"| Branch Sync | {state['branch_sync']} | {'MEDIUM' if state['branch_sync'] == 'ahead' else 'OK'} |")
    lines.append(f"| TypeScript | {state['typescript']} | {'HIGH' if state['typescript'] == 'errors' else 'OK'} |")
    lines.append(f"| Open Issues | {state['open_issues']} | {'MEDIUM' if state['open_issues'] > 3 else 'LOW'} |")
    if state['research_branches'] > 0:
        lines.append(f"| Research Branches | {state['research_branches']} | HIGH |")

    lines.append("\n## Recommended Actions\n")

    for i, action in enumerate(report["recommendations"][:3], 1):
        lines.append(f"### {i}. {action['name']} (Score: {action['score']})")
        lines.append(f"**Command:** `{action['command']}`")
        lines.append(f"**Why:** {action['why']}")
        lines.append(f"**What it does:** {action['what']}")
        lines.append(f"**Benefit:** {action['benefit']}")
        lines.append("")

    lines.append("## Quick Reference\n")
    lines.append("| If you want to... | Use this command |")
    lines.append("|-------------------|------------------|")
    for item in report["quick_reference"]:
        lines.append(f"| {item['goal']} | `{item['command']}` |")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Recommend next action")
    parser.add_argument("--mode", choices=["score", "rank", "report"],
                        default="report", help="Output mode")
    parser.add_argument("--state-file", help="Path to state JSON file")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    args = parser.parse_args()

    result = {
        "operation": f"recommend_action_{args.mode}",
        "timestamp": datetime.now().isoformat()
    }

    # Load state
    state = load_state(args.state_file)
    result["state"] = state

    # Calculate scores
    actions = calculate_action_scores(state)

    if args.mode == "score":
        result["actions"] = actions

    elif args.mode in ["rank", "report"]:
        ranked = rank_actions(actions)
        result["ranked_actions"] = ranked

        if args.mode == "report":
            report = generate_report(ranked, state)
            result["report"] = report

            if args.format == "display":
                print(format_report_display(report))
                return 0

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
