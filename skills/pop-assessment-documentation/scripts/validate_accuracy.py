#!/usr/bin/env python3
"""
Validate Documentation Accuracy.

Checks that documentation matches actual code reality.

Usage:
    python validate_accuracy.py [project_dir]

Output:
    JSON object with accuracy findings
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def validate_auto_generated_counts(project_dir: Path) -> List[Dict[str, Any]]:
    """Validate auto-generated count sections in CLAUDE.md."""
    issues = []
    claude_md = project_dir / "CLAUDE.md"

    if not claude_md.exists():
        return [{"type": "missing_file", "file": "CLAUDE.md", "severity": "critical"}]

    content = claude_md.read_text(encoding="utf-8", errors="ignore")

    # Check for AUTO-GEN markers
    auto_gen_pattern = r"<!-- AUTO-GEN:(\w+) START -->(.*?)<!-- AUTO-GEN:\1 END -->"
    matches = re.findall(auto_gen_pattern, content, re.DOTALL)

    for section_name, section_content in matches:
        if section_name == "TIER-COUNTS":
            # Validate tier counts
            tier1_match = re.search(r"Tier 1:.*?\((\d+)\)", section_content)
            tier2_match = re.search(r"Tier 2:.*?\((\d+)\)", section_content)
            skills_match = re.search(r"Skills:\s*(\d+)", section_content)
            commands_match = re.search(r"Commands:\s*(\d+)", section_content)

            # Count actual items
            actual_tier1 = len(list((project_dir / "agents" / "tier-1-always-active").glob("*/"))) if (project_dir / "agents" / "tier-1-always-active").exists() else 0
            actual_tier2 = len(list((project_dir / "agents" / "tier-2-on-demand").glob("*/"))) if (project_dir / "agents" / "tier-2-on-demand").exists() else 0
            actual_skills = len(list((project_dir / "skills").glob("pop-*/"))) if (project_dir / "skills").exists() else 0
            actual_commands = len(list((project_dir / "commands").glob("*.md"))) if (project_dir / "commands").exists() else 0

            if tier1_match and int(tier1_match.group(1)) != actual_tier1:
                issues.append({
                    "type": "count_mismatch",
                    "field": "Tier 1 agents",
                    "documented": int(tier1_match.group(1)),
                    "actual": actual_tier1,
                    "severity": "medium"
                })

            if tier2_match and int(tier2_match.group(1)) != actual_tier2:
                issues.append({
                    "type": "count_mismatch",
                    "field": "Tier 2 agents",
                    "documented": int(tier2_match.group(1)),
                    "actual": actual_tier2,
                    "severity": "medium"
                })

            if skills_match and int(skills_match.group(1)) != actual_skills:
                issues.append({
                    "type": "count_mismatch",
                    "field": "Skills",
                    "documented": int(skills_match.group(1)),
                    "actual": actual_skills,
                    "severity": "medium"
                })

            if commands_match and int(commands_match.group(1)) != actual_commands:
                issues.append({
                    "type": "count_mismatch",
                    "field": "Commands",
                    "documented": int(commands_match.group(1)),
                    "actual": actual_commands,
                    "severity": "medium"
                })

    return issues


def validate_file_references(project_dir: Path) -> List[Dict[str, Any]]:
    """Check that file references in docs point to existing files."""
    issues = []

    # Check CLAUDE.md key files table
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8", errors="ignore")

        # Find file paths in markdown tables and code blocks
        file_patterns = [
            r"\| `([^`]+)` \|",  # Table with backticks
            r"\| ([a-zA-Z0-9_/.-]+\.(?:py|ts|js|json|md)) \|",  # Table without backticks
        ]

        for pattern in file_patterns:
            for match in re.finditer(pattern, content):
                file_path = match.group(1)
                # Clean up path
                file_path = file_path.strip("`").strip()

                # Skip if it looks like a pattern or description
                if "*" in file_path or " " in file_path:
                    continue

                # Resolve relative to project
                full_path = project_dir / file_path
                if not full_path.exists() and not (project_dir.parent.parent / file_path).exists():
                    # Also check packages/plugin prefix
                    if not file_path.startswith("packages/plugin/"):
                        alt_path = project_dir / file_path.replace("packages/plugin/", "")
                        if not alt_path.exists():
                            issues.append({
                                "type": "missing_reference",
                                "file": "CLAUDE.md",
                                "reference": file_path,
                                "severity": "low"
                            })

    return issues


def validate_code_examples(project_dir: Path) -> List[Dict[str, Any]]:
    """Check that code examples reference actual exports/functions."""
    issues = []

    # Check skill documentation for import references
    skills_dir = project_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8", errors="ignore")

                    # Look for script references
                    script_refs = re.findall(r"python\s+(?:skills/)?[\w-]+/scripts/(\w+\.py)", content)
                    for script_ref in script_refs:
                        script_path = skill_dir / "scripts" / script_ref
                        if not script_path.exists():
                            issues.append({
                                "type": "missing_script",
                                "file": str(skill_md.relative_to(project_dir)),
                                "reference": script_ref,
                                "severity": "medium"
                            })

    return issues


def validate_version_sync(project_dir: Path) -> List[Dict[str, Any]]:
    """Check that version numbers are synchronized across files."""
    issues = []
    versions = {}

    # Check plugin.json
    plugin_json = project_dir / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            versions["plugin.json"] = data.get("version", "unknown")
        except:
            pass

    # Check marketplace.json
    marketplace_json = project_dir / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            data = json.loads(marketplace_json.read_text())
            versions["marketplace.json"] = data.get("version", "unknown")
        except:
            pass

    # Check CHANGELOG.md for latest version
    changelog = project_dir / "CHANGELOG.md"
    if not changelog.exists():
        changelog = project_dir.parent.parent / "CHANGELOG.md"

    if changelog.exists():
        content = changelog.read_text(encoding="utf-8", errors="ignore")
        version_match = re.search(r"## \[(\d+\.\d+\.\d+)\]", content)
        if version_match:
            versions["CHANGELOG.md"] = version_match.group(1)

    # Check for mismatches
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        issues.append({
            "type": "version_mismatch",
            "versions": versions,
            "severity": "high"
        })

    return issues


def validate_link_freshness(project_dir: Path) -> List[Dict[str, Any]]:
    """Check for potentially stale external links."""
    issues = []
    stale_patterns = [
        r"https?://[^\s\)]+2023[^\s\)]*",  # 2023 dated URLs
        r"https?://[^\s\)]+2022[^\s\)]*",  # 2022 dated URLs
    ]

    for md_file in project_dir.rglob("*.md"):
        if "node_modules" in str(md_file):
            continue

        content = md_file.read_text(encoding="utf-8", errors="ignore")

        for pattern in stale_patterns:
            for match in re.finditer(pattern, content):
                issues.append({
                    "type": "potentially_stale_link",
                    "file": str(md_file.relative_to(project_dir)),
                    "link": match.group(0)[:100],
                    "severity": "low"
                })

    return issues[:10]  # Limit to 10


def calculate_accuracy_score(issues: List[Dict[str, Any]]) -> float:
    """Calculate accuracy score based on issues found."""
    score = 100

    severity_weights = {
        "critical": 20,
        "high": 10,
        "medium": 5,
        "low": 2
    }

    for issue in issues:
        weight = severity_weights.get(issue.get("severity", "medium"), 5)
        score -= weight

    return max(0, score)


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Run validations
    all_issues = []

    auto_gen_issues = validate_auto_generated_counts(project_dir)
    file_ref_issues = validate_file_references(project_dir)
    code_example_issues = validate_code_examples(project_dir)
    version_issues = validate_version_sync(project_dir)
    link_issues = validate_link_freshness(project_dir)

    all_issues.extend(auto_gen_issues)
    all_issues.extend(file_ref_issues)
    all_issues.extend(code_example_issues)
    all_issues.extend(version_issues)
    all_issues.extend(link_issues)

    # Calculate score
    accuracy_score = calculate_accuracy_score(all_issues)

    # Determine status
    if accuracy_score >= 90:
        status = "accurate"
    elif accuracy_score >= 70:
        status = "mostly_accurate"
    elif accuracy_score >= 50:
        status = "needs_review"
    else:
        status = "inaccurate"

    report = {
        "assessment": "documentation-accuracy",
        "project_dir": str(project_dir),
        "accuracy_score": accuracy_score,
        "status": status,
        "issues_by_category": {
            "auto_generated_counts": auto_gen_issues,
            "file_references": file_ref_issues,
            "code_examples": code_example_issues,
            "version_sync": version_issues,
            "link_freshness": link_issues
        },
        "summary": {
            "total_issues": len(all_issues),
            "critical": len([i for i in all_issues if i.get("severity") == "critical"]),
            "high": len([i for i in all_issues if i.get("severity") == "high"]),
            "medium": len([i for i in all_issues if i.get("severity") == "medium"]),
            "low": len([i for i in all_issues if i.get("severity") == "low"])
        }
    }

    print(json.dumps(report, indent=2))
    return 0 if accuracy_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
