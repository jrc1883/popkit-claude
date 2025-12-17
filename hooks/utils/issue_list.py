#!/usr/bin/env python3
"""
Issue List Utility
Lists GitHub issues with Power Mode recommendations parsed from PopKit Guidance.

Used by /popkit:issues command to display issues with their orchestration status.

Part of the popkit plugin system.
"""

import subprocess
import json
import re
from typing import Dict, List, Optional, Any

from github_issues import parse_popkit_guidance, infer_issue_type


def fetch_issues(
    state: str = "open",
    label: str = None,
    assignee: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Fetch issues from GitHub.

    Args:
        state: Issue state filter (open, closed, all)
        label: Filter by label
        assignee: Filter by assignee
        limit: Maximum issues to return

    Returns:
        List of issue dicts or empty list on error
    """
    cmd = [
        "gh", "issue", "list",
        "--state", state,
        "--json", "number,title,body,labels,createdAt,author,state",
        "--limit", str(limit)
    ]

    if label:
        cmd.extend(["--label", label])

    if assignee:
        cmd.extend(["--assignee", assignee])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []


def get_power_mode_status(guidance: Dict[str, Any]) -> str:
    """Determine Power Mode status from parsed guidance.

    Args:
        guidance: Parsed PopKit Guidance dict

    Returns:
        "RECOMMENDED", "optional", "not_needed", or "(unknown)"
    """
    power_mode = guidance.get("power_mode", "not_needed")
    complexity = guidance.get("complexity", "medium")

    # Check explicit recommendation
    if power_mode == "recommended":
        return "RECOMMENDED"

    # Check complexity-based recommendation
    if complexity in ["epic", "large"]:
        return "RECOMMENDED"

    if power_mode == "optional":
        return "optional"

    if power_mode == "not_needed":
        return "not_needed"

    return "(unknown)"


def get_phase_count(guidance: Dict[str, Any]) -> int:
    """Count phases from guidance.

    Args:
        guidance: Parsed PopKit Guidance dict

    Returns:
        Number of phases
    """
    phases = guidance.get("phases", [])
    return len(phases) if phases else 0


def infer_complexity_from_labels(labels: List[str]) -> str:
    """Infer complexity from issue labels.

    Args:
        labels: List of label names

    Returns:
        "small", "medium", "large", "epic", or "unknown"
    """
    label_set = set(l.lower() for l in labels)

    if "epic" in label_set:
        return "epic"
    if "architecture" in label_set:
        return "large"
    if "feature" in label_set or "enhancement" in label_set:
        return "medium"
    if "bug" in label_set:
        return "small"
    if "docs" in label_set or "documentation" in label_set:
        return "small"

    return "unknown"


def list_issues_with_power_mode_status(
    filter_power: bool = False,
    label: str = None,
    state: str = "open",
    assignee: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """List issues with Power Mode recommendations.

    Args:
        filter_power: If True, only show issues recommending Power Mode
        label: Filter by label
        state: Filter by state (open, closed, all)
        assignee: Filter by assignee
        limit: Maximum issues

    Returns:
        Dict with:
        - issues: List of issue dicts with power_mode_status
        - total: Total count
        - filtered: Whether filtering was applied
    """
    result = {
        "issues": [],
        "total": 0,
        "filtered": filter_power,
        "error": None
    }

    # Fetch issues
    issues = fetch_issues(
        state=state,
        label=label,
        assignee=assignee,
        limit=limit * 2 if filter_power else limit  # Fetch more if filtering
    )

    if not issues:
        return result

    # Process each issue
    processed = []
    for issue in issues:
        # Extract labels as list of names
        labels = [l.get("name", "") for l in issue.get("labels", [])]

        # Parse PopKit Guidance from body
        body = issue.get("body", "") or ""
        guidance = parse_popkit_guidance(body)

        # Determine Power Mode status
        power_status = get_power_mode_status(guidance)

        # Infer complexity if not in guidance
        complexity = guidance.get("complexity", "unknown")
        if complexity == "medium" and not guidance.get("raw_section"):
            # No guidance section, infer from labels
            complexity = infer_complexity_from_labels(labels)
            # Re-evaluate power status based on inferred complexity
            if complexity in ["epic", "large"]:
                power_status = "RECOMMENDED"
            elif complexity == "unknown":
                power_status = "(unknown)"

        # Get phase count
        phase_count = get_phase_count(guidance)
        if phase_count == 0 and not guidance.get("raw_section"):
            # Estimate phases from issue type
            issue_type = infer_issue_type({"labels": labels, "title": issue.get("title", "")})
            if issue_type == "bug":
                phase_count = 3  # investigate, fix, test
            elif issue_type == "feature":
                phase_count = 5  # discover, design, implement, test, review
            elif issue_type == "architecture":
                phase_count = 6  # all phases
            else:
                phase_count = 3  # default

        processed_issue = {
            "number": issue.get("number"),
            "title": issue.get("title", ""),
            "labels": labels,
            "complexity": complexity,
            "power_mode_status": power_status,
            "phase_count": phase_count,
            "has_guidance": bool(guidance.get("raw_section")),
            "created_at": issue.get("createdAt", ""),
            "author": issue.get("author", {}).get("login", "")
        }

        # Apply power filter if requested
        if filter_power:
            if power_status == "RECOMMENDED":
                processed.append(processed_issue)
        else:
            processed.append(processed_issue)

        # Stop if we have enough
        if len(processed) >= limit:
            break

    result["issues"] = processed
    result["total"] = len(processed)

    return result


def format_issues_table(data: Dict[str, Any]) -> str:
    """Format issues as ASCII table.

    Args:
        data: Result from list_issues_with_power_mode_status

    Returns:
        Formatted table string
    """
    issues = data.get("issues", [])

    if not issues:
        return "No issues found."

    # Header
    lines = []

    if data.get("filtered"):
        lines.append("Issues Recommending Power Mode:")
    else:
        lines.append("Open Issues with Power Mode Recommendations:")

    lines.append("")
    lines.append("| #   | Title                              | Complexity | Power Mode  | Phases |")
    lines.append("|-----|-------------------------------------|------------|-------------|--------|")

    # Rows
    for issue in issues:
        num = str(issue["number"]).ljust(3)
        title = issue["title"][:35].ljust(35)
        complexity = issue["complexity"].ljust(10)
        power = issue["power_mode_status"].ljust(11)
        phases = str(issue["phase_count"]).ljust(6)

        lines.append(f"| {num} | {title} | {complexity} | {power} | {phases} |")

    lines.append("")
    lines.append(f"Total: {data['total']} issues")

    if not data.get("filtered"):
        lines.append("")
        lines.append("Legend:")
        lines.append("  RECOMMENDED = Power Mode beneficial for this issue")
        lines.append("  optional    = Power Mode available but not required")
        lines.append("  not_needed  = Sequential execution preferred")
        lines.append("  (unknown)   = No PopKit Guidance, inferred from labels")

    lines.append("")
    lines.append("Hint: Use /popkit:work #N to start working on an issue")
    lines.append("      Use /popkit:work #N -p to force Power Mode")

    return '\n'.join(lines)


if __name__ == "__main__":
    import sys
    from flag_parser import parse_issues_args

    # CLI mode for testing
    if len(sys.argv) > 1:
        args = " ".join(sys.argv[1:])
        flags = parse_issues_args(args)

        data = list_issues_with_power_mode_status(
            filter_power=flags.get("filter_power", False),
            label=flags.get("label"),
            state=flags.get("state", "open"),
            assignee=flags.get("assignee"),
            limit=flags.get("limit", 20)
        )

        print(format_issues_table(data))
    else:
        # Default: list open issues
        data = list_issues_with_power_mode_status()
        print(format_issues_table(data))
