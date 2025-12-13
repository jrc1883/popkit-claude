#!/usr/bin/env python3
"""
Analyze Command Naming and Structure.

Evaluates command naming conventions, consistency, and discoverability.

Usage:
    python analyze_commands.py [project_dir]

Output:
    JSON object with command analysis results
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def analyze_command_naming(project_dir: Path) -> Dict[str, Any]:
    """Analyze command naming patterns."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"commands": [], "issues": []}

    commands = []
    issues = []

    for cmd_file in commands_dir.glob("*.md"):
        name = cmd_file.stem
        content = cmd_file.read_text(encoding="utf-8", errors="ignore")

        cmd_data = {
            "name": name,
            "length": len(name),
            "has_description": "description:" in content.lower() or "## " in content,
            "has_examples": "```" in content
        }

        # Check naming conventions
        if len(name) > 20:
            issues.append({
                "command": name,
                "issue": "Command name too long (>20 chars)",
                "severity": "medium"
            })

        if name.startswith("-") or name.endswith("-"):
            issues.append({
                "command": name,
                "issue": "Name starts/ends with hyphen",
                "severity": "low"
            })

        # Check for unclear abbreviations
        unclear_patterns = ["mgr", "mgmt", "impl", "cfg", "init"]
        for abbr in unclear_patterns:
            if abbr in name.lower() and len(name) < 8:
                issues.append({
                    "command": name,
                    "issue": f"Unclear abbreviation '{abbr}' - consider full word",
                    "severity": "low"
                })

        # Check for consistent naming pattern
        if "-" not in name and "_" not in name and len(name) > 10:
            issues.append({
                "command": name,
                "issue": "Long name without word separators",
                "severity": "low"
            })

        commands.append(cmd_data)

    return {
        "total": len(commands),
        "commands": commands,
        "issues": issues
    }


def analyze_subcommand_consistency(project_dir: Path) -> Dict[str, Any]:
    """Analyze subcommand patterns for consistency."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"patterns": {}, "issues": []}

    subcommand_patterns = {}
    issues = []

    for cmd_file in commands_dir.glob("*.md"):
        content = cmd_file.read_text(encoding="utf-8", errors="ignore")

        # Find subcommands in tables
        subcommands = re.findall(r"\| `?(\w+)`? \|", content)

        for sub in subcommands:
            if sub.lower() not in ["subcommand", "command", "flag", "description"]:
                if sub not in subcommand_patterns:
                    subcommand_patterns[sub] = []
                subcommand_patterns[sub].append(cmd_file.stem)

    # Check for inconsistent naming
    common_verbs = {
        "create": ["add", "new", "make"],
        "delete": ["remove", "rm", "del"],
        "list": ["ls", "show", "get"],
        "update": ["edit", "modify", "change"],
    }

    for verb, alternatives in common_verbs.items():
        found = [alt for alt in alternatives if alt in subcommand_patterns]
        if verb in subcommand_patterns and found:
            issues.append({
                "type": "inconsistent_verb",
                "message": f"Mixed usage: '{verb}' and '{', '.join(found)}'",
                "severity": "medium"
            })

    return {
        "subcommand_counts": {k: len(v) for k, v in subcommand_patterns.items()},
        "issues": issues
    }


def analyze_discoverability(project_dir: Path) -> Dict[str, Any]:
    """Analyze command discoverability."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"score": 0, "issues": []}

    score = 100
    issues = []

    for cmd_file in commands_dir.glob("*.md"):
        content = cmd_file.read_text(encoding="utf-8", errors="ignore")
        name = cmd_file.stem

        # Check for description in frontmatter
        if not re.search(r"^description:", content, re.MULTILINE):
            issues.append({
                "command": name,
                "issue": "Missing description in frontmatter",
                "severity": "high"
            })
            score -= 5

        # Check for examples
        if content.count("```") < 2:
            issues.append({
                "command": name,
                "issue": "Missing or insufficient examples",
                "severity": "medium"
            })
            score -= 3

        # Check for related commands section
        if not re.search(r"related|see also", content, re.IGNORECASE):
            issues.append({
                "command": name,
                "issue": "No related commands section",
                "severity": "low"
            })
            score -= 1

    return {
        "score": max(0, score),
        "issues": issues[:20]
    }


def analyze_help_quality(project_dir: Path) -> Dict[str, Any]:
    """Analyze help text quality."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"score": 0, "issues": []}

    score = 100
    issues = []

    for cmd_file in commands_dir.glob("*.md"):
        content = cmd_file.read_text(encoding="utf-8", errors="ignore")
        name = cmd_file.stem

        # Check for flag documentation
        has_flags = re.search(r"##\s*Flags|##\s*Options|--\w+", content)
        if has_flags:
            # Check if flags have descriptions
            flag_table = re.search(r"\| `?--\w+`? \|", content)
            if not flag_table:
                issues.append({
                    "command": name,
                    "issue": "Flags not documented in table format",
                    "severity": "medium"
                })
                score -= 3

        # Check for common sections
        expected_sections = ["Example", "Usage"]
        for section in expected_sections:
            if not re.search(rf"##.*{section}", content, re.IGNORECASE):
                issues.append({
                    "command": name,
                    "issue": f"Missing '{section}' section",
                    "severity": "low"
                })
                score -= 2

    return {
        "score": max(0, score),
        "issues": issues[:20]
    }


def calculate_naming_score(
    naming: Dict,
    subcommands: Dict,
    discoverability: Dict,
    help_quality: Dict
) -> float:
    """Calculate overall command naming score."""
    score = 100

    # Deduct for naming issues
    for issue in naming.get("issues", []):
        if issue["severity"] == "high":
            score -= 8
        elif issue["severity"] == "medium":
            score -= 4
        else:
            score -= 2

    # Deduct for subcommand issues
    for issue in subcommands.get("issues", []):
        score -= 5

    # Factor in discoverability
    score = (score * 0.6) + (discoverability.get("score", 0) * 0.2) + (help_quality.get("score", 0) * 0.2)

    return max(0, min(100, round(score)))


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Run analyses
    naming = analyze_command_naming(project_dir)
    subcommands = analyze_subcommand_consistency(project_dir)
    discoverability = analyze_discoverability(project_dir)
    help_quality = analyze_help_quality(project_dir)

    # Calculate score
    naming_score = calculate_naming_score(naming, subcommands, discoverability, help_quality)

    # Determine status
    if naming_score >= 90:
        status = "excellent"
    elif naming_score >= 70:
        status = "good"
    elif naming_score >= 50:
        status = "needs_improvement"
    else:
        status = "poor"

    report = {
        "assessment": "command-analysis",
        "project_dir": str(project_dir),
        "naming_score": naming_score,
        "status": status,
        "command_naming": naming,
        "subcommand_consistency": subcommands,
        "discoverability": discoverability,
        "help_quality": help_quality,
        "all_issues": (
            naming.get("issues", []) +
            subcommands.get("issues", []) +
            discoverability.get("issues", []) +
            help_quality.get("issues", [])
        )[:30]
    }

    print(json.dumps(report, indent=2))
    return 0 if naming_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
