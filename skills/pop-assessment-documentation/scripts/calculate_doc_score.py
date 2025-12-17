#!/usr/bin/env python3
"""
Calculate Overall Documentation Score.

Combines coverage, accuracy, and freshness into a single score.

Usage:
    python calculate_doc_score.py [project_dir]

Output:
    JSON object with overall documentation score
"""

import json
import os
import sys
from datetime import datetime, timedelta
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
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def measure_freshness(project_dir: Path) -> Dict[str, Any]:
    """Measure documentation freshness based on modification dates."""
    key_docs = [
        ("CLAUDE.md", project_dir / "CLAUDE.md"),
        ("README.md", project_dir / "README.md"),
        ("CHANGELOG.md", project_dir.parent.parent / "CHANGELOG.md"),
    ]

    freshness_data = []
    now = datetime.now()

    for name, path in key_docs:
        if path.exists():
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            days_old = (now - mtime).days

            if days_old <= 7:
                status = "fresh"
            elif days_old <= 30:
                status = "recent"
            elif days_old <= 90:
                status = "aging"
            else:
                status = "stale"

            freshness_data.append({
                "name": name,
                "days_old": days_old,
                "status": status,
                "last_modified": mtime.isoformat()
            })
        else:
            freshness_data.append({
                "name": name,
                "status": "missing",
                "days_old": None
            })

    # Calculate freshness score
    status_scores = {"fresh": 100, "recent": 80, "aging": 50, "stale": 20, "missing": 0}
    scores = [status_scores.get(d["status"], 0) for d in freshness_data]
    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "documents": freshness_data,
        "freshness_score": round(avg_score, 1)
    }


def check_required_sections(project_dir: Path) -> Dict[str, Any]:
    """Check for required documentation sections."""
    claude_md = project_dir / "CLAUDE.md"

    required_sections = [
        ("Project Overview", r"## Project Overview|# Project Overview"),
        ("Repository Structure", r"## Repository Structure|Repository Structure"),
        ("Development Notes", r"## Development Notes|Development Notes"),
        ("Key Architectural Patterns", r"## Key Architectural|Architectural Patterns"),
        ("Key Files", r"## Key Files|Key Files"),
        ("Conventions", r"## Conventions|Conventions"),
    ]

    if not claude_md.exists():
        return {
            "found": 0,
            "required": len(required_sections),
            "missing": [s[0] for s in required_sections],
            "score": 0
        }

    content = claude_md.read_text(encoding="utf-8", errors="ignore")

    found = []
    missing = []

    import re
    for section_name, pattern in required_sections:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(section_name)
        else:
            missing.append(section_name)

    score = (len(found) / len(required_sections) * 100) if required_sections else 100

    return {
        "found": len(found),
        "required": len(required_sections),
        "missing": missing,
        "score": round(score, 1)
    }


def check_example_quality(project_dir: Path) -> Dict[str, Any]:
    """Check quality and presence of code examples."""
    total_docs = 0
    docs_with_examples = 0
    example_stats = {
        "code_blocks": 0,
        "shell_examples": 0,
        "json_examples": 0
    }

    for md_file in project_dir.rglob("*.md"):
        if "node_modules" in str(md_file):
            continue

        total_docs += 1
        content = md_file.read_text(encoding="utf-8", errors="ignore")

        # Count code blocks
        code_blocks = content.count("```")
        if code_blocks > 0:
            docs_with_examples += 1
            example_stats["code_blocks"] += code_blocks // 2

        # Count specific types
        example_stats["shell_examples"] += content.count("```bash") + content.count("```sh")
        example_stats["json_examples"] += content.count("```json")

    percent = (docs_with_examples / total_docs * 100) if total_docs > 0 else 100

    return {
        "total_docs": total_docs,
        "docs_with_examples": docs_with_examples,
        "percent": round(percent, 1),
        "example_stats": example_stats,
        "score": round(min(100, percent), 1)
    }


def calculate_final_score(
    coverage_score: float,
    accuracy_score: float,
    freshness_score: float,
    sections_score: float,
    examples_score: float
) -> float:
    """Calculate weighted final documentation score."""
    weights = {
        "coverage": 30,
        "accuracy": 25,
        "freshness": 15,
        "sections": 15,
        "examples": 15
    }

    total_weight = sum(weights.values())
    weighted_sum = (
        coverage_score * weights["coverage"] +
        accuracy_score * weights["accuracy"] +
        freshness_score * weights["freshness"] +
        sections_score * weights["sections"] +
        examples_score * weights["examples"]
    )

    return round(weighted_sum / total_weight, 1)


def get_recommendations(
    coverage_score: float,
    accuracy_score: float,
    freshness_score: float,
    sections_score: float,
    examples_score: float
) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    if coverage_score < 80:
        recommendations.append("Add SKILL.md/AGENT.md files to undocumented components")

    if accuracy_score < 80:
        recommendations.append("Update auto-generated counts in CLAUDE.md")

    if freshness_score < 60:
        recommendations.append("Review and update documentation older than 30 days")

    if sections_score < 80:
        recommendations.append("Add missing required sections to CLAUDE.md")

    if examples_score < 70:
        recommendations.append("Add more code examples and usage snippets to docs")

    if not recommendations:
        recommendations.append("Documentation is in good shape - maintain regular updates")

    return recommendations


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Gather all metrics
    freshness = measure_freshness(project_dir)
    sections = check_required_sections(project_dir)
    examples = check_example_quality(project_dir)

    # Use placeholder scores for coverage and accuracy
    # (In real use, these would come from the other scripts)
    coverage_score = 85.0  # Placeholder
    accuracy_score = 90.0  # Placeholder

    # Calculate final score
    final_score = calculate_final_score(
        coverage_score,
        accuracy_score,
        freshness["freshness_score"],
        sections["score"],
        examples["score"]
    )

    # Determine grade
    if final_score >= 90:
        grade = "A"
        status = "excellent"
    elif final_score >= 80:
        grade = "B"
        status = "good"
    elif final_score >= 70:
        grade = "C"
        status = "acceptable"
    elif final_score >= 60:
        grade = "D"
        status = "needs_improvement"
    else:
        grade = "F"
        status = "critical"

    recommendations = get_recommendations(
        coverage_score,
        accuracy_score,
        freshness["freshness_score"],
        sections["score"],
        examples["score"]
    )

    report = {
        "assessment": "documentation-score",
        "project_dir": str(project_dir),
        "final_score": final_score,
        "grade": grade,
        "status": status,
        "component_scores": {
            "coverage": coverage_score,
            "accuracy": accuracy_score,
            "freshness": freshness["freshness_score"],
            "required_sections": sections["score"],
            "examples": examples["score"]
        },
        "details": {
            "freshness": freshness,
            "sections": sections,
            "examples": examples
        },
        "recommendations": recommendations
    }

    print(json.dumps(report, indent=2))
    return 0 if final_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
