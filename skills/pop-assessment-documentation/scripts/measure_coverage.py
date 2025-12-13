#!/usr/bin/env python3
"""
Measure Documentation Coverage.

Calculates the percentage of code artifacts that have proper documentation.

Usage:
    python measure_coverage.py [project_dir]

Output:
    JSON object with coverage metrics by category
"""

import json
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


def measure_skill_coverage(project_dir: Path) -> Dict[str, Any]:
    """Measure documentation coverage for skills."""
    skills_dir = project_dir / "skills"
    if not skills_dir.exists():
        return {"total": 0, "documented": 0, "percent": 100.0, "missing": []}

    skills = []
    documented = []
    missing = []

    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
            skill_name = skill_dir.name
            skills.append(skill_name)

            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                # Check for minimal required content
                if len(content) > 100 and "---" in content:
                    documented.append(skill_name)
                else:
                    missing.append({"name": skill_name, "reason": "SKILL.md incomplete"})
            else:
                missing.append({"name": skill_name, "reason": "No SKILL.md"})

    total = len(skills)
    doc_count = len(documented)
    percent = (doc_count / total * 100) if total > 0 else 100.0

    return {
        "total": total,
        "documented": doc_count,
        "percent": round(percent, 1),
        "missing": missing
    }


def measure_agent_coverage(project_dir: Path) -> Dict[str, Any]:
    """Measure documentation coverage for agents."""
    agents_dir = project_dir / "agents"
    if not agents_dir.exists():
        return {"total": 0, "documented": 0, "percent": 100.0, "missing": []}

    agents = []
    documented = []
    missing = []

    # Check tier directories
    for tier_dir in agents_dir.iterdir():
        if tier_dir.is_dir() and tier_dir.name.startswith("tier-"):
            for agent_dir in tier_dir.iterdir():
                if agent_dir.is_dir():
                    agent_name = agent_dir.name
                    agents.append(agent_name)

                    agent_md = agent_dir / "AGENT.md"
                    if agent_md.exists():
                        content = agent_md.read_text(encoding="utf-8", errors="ignore")
                        if len(content) > 50:
                            documented.append(agent_name)
                        else:
                            missing.append({"name": agent_name, "reason": "AGENT.md too short"})
                    else:
                        missing.append({"name": agent_name, "reason": "No AGENT.md"})

    # Check feature-workflow
    feature_dir = agents_dir / "feature-workflow"
    if feature_dir.exists():
        for agent_dir in feature_dir.iterdir():
            if agent_dir.is_dir():
                agent_name = agent_dir.name
                agents.append(agent_name)

                agent_md = agent_dir / "AGENT.md"
                if agent_md.exists():
                    documented.append(agent_name)
                else:
                    missing.append({"name": agent_name, "reason": "No AGENT.md"})

    total = len(agents)
    doc_count = len(documented)
    percent = (doc_count / total * 100) if total > 0 else 100.0

    return {
        "total": total,
        "documented": doc_count,
        "percent": round(percent, 1),
        "missing": missing
    }


def measure_command_coverage(project_dir: Path) -> Dict[str, Any]:
    """Measure documentation coverage for commands."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"total": 0, "documented": 0, "percent": 100.0, "missing": []}

    commands = []
    documented = []
    missing = []

    for cmd_file in commands_dir.glob("*.md"):
        cmd_name = cmd_file.stem
        commands.append(cmd_name)

        content = cmd_file.read_text(encoding="utf-8", errors="ignore")

        # Check for required sections
        has_description = "description:" in content.lower() or "## " in content
        has_examples = "example" in content.lower() or "```" in content

        if has_description and has_examples:
            documented.append(cmd_name)
        else:
            reasons = []
            if not has_description:
                reasons.append("missing description")
            if not has_examples:
                reasons.append("missing examples")
            missing.append({"name": cmd_name, "reason": ", ".join(reasons)})

    total = len(commands)
    doc_count = len(documented)
    percent = (doc_count / total * 100) if total > 0 else 100.0

    return {
        "total": total,
        "documented": doc_count,
        "percent": round(percent, 1),
        "missing": missing
    }


def measure_readme_coverage(project_dir: Path) -> Dict[str, Any]:
    """Check for README files in key locations."""
    readme_locations = [
        ("root", project_dir / "README.md"),
        ("claude", project_dir / "CLAUDE.md"),
        ("hooks", project_dir / "hooks" / "README.md"),
        ("power-mode", project_dir / "power-mode" / "README.md"),
        ("templates", project_dir / "templates" / "README.md"),
    ]

    total = len(readme_locations)
    found = []
    missing = []

    for name, path in readme_locations:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 100:
                found.append(name)
            else:
                missing.append({"name": name, "reason": "README too short"})
        else:
            missing.append({"name": name, "reason": "Not found"})

    percent = (len(found) / total * 100) if total > 0 else 100.0

    return {
        "total": total,
        "documented": len(found),
        "percent": round(percent, 1),
        "missing": missing
    }


def measure_inline_docs(project_dir: Path) -> Dict[str, Any]:
    """Measure inline documentation (docstrings, JSDoc comments)."""
    stats = {
        "python_files": 0,
        "python_with_docstrings": 0,
        "ts_files": 0,
        "ts_with_jsdoc": 0,
    }

    # Python files
    for py_file in project_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or "node_modules" in str(py_file):
            continue
        stats["python_files"] += 1
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if '"""' in content or "'''" in content:
            stats["python_with_docstrings"] += 1

    # TypeScript files
    for ts_file in project_dir.rglob("*.ts"):
        if "node_modules" in str(ts_file) or ".d.ts" in str(ts_file):
            continue
        stats["ts_files"] += 1
        content = ts_file.read_text(encoding="utf-8", errors="ignore")
        if "/**" in content:
            stats["ts_with_jsdoc"] += 1

    # Calculate percentages
    py_percent = (stats["python_with_docstrings"] / stats["python_files"] * 100) if stats["python_files"] > 0 else 100.0
    ts_percent = (stats["ts_with_jsdoc"] / stats["ts_files"] * 100) if stats["ts_files"] > 0 else 100.0

    return {
        "python": {
            "total": stats["python_files"],
            "documented": stats["python_with_docstrings"],
            "percent": round(py_percent, 1)
        },
        "typescript": {
            "total": stats["ts_files"],
            "documented": stats["ts_with_jsdoc"],
            "percent": round(ts_percent, 1)
        }
    }


def calculate_overall_coverage(metrics: Dict[str, Any]) -> float:
    """Calculate weighted overall coverage score."""
    weights = {
        "skills": 25,
        "agents": 20,
        "commands": 20,
        "readmes": 20,
        "inline_python": 7.5,
        "inline_typescript": 7.5,
    }

    total_weight = 0
    weighted_sum = 0

    if metrics["skills"]["total"] > 0:
        weighted_sum += metrics["skills"]["percent"] * weights["skills"]
        total_weight += weights["skills"]

    if metrics["agents"]["total"] > 0:
        weighted_sum += metrics["agents"]["percent"] * weights["agents"]
        total_weight += weights["agents"]

    if metrics["commands"]["total"] > 0:
        weighted_sum += metrics["commands"]["percent"] * weights["commands"]
        total_weight += weights["commands"]

    if metrics["readmes"]["total"] > 0:
        weighted_sum += metrics["readmes"]["percent"] * weights["readmes"]
        total_weight += weights["readmes"]

    if metrics["inline"]["python"]["total"] > 0:
        weighted_sum += metrics["inline"]["python"]["percent"] * weights["inline_python"]
        total_weight += weights["inline_python"]

    if metrics["inline"]["typescript"]["total"] > 0:
        weighted_sum += metrics["inline"]["typescript"]["percent"] * weights["inline_typescript"]
        total_weight += weights["inline_typescript"]

    return round(weighted_sum / total_weight, 1) if total_weight > 0 else 100.0


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Measure coverage for each category
    metrics = {
        "skills": measure_skill_coverage(project_dir),
        "agents": measure_agent_coverage(project_dir),
        "commands": measure_command_coverage(project_dir),
        "readmes": measure_readme_coverage(project_dir),
        "inline": measure_inline_docs(project_dir),
    }

    # Calculate overall coverage
    overall = calculate_overall_coverage(metrics)

    # Determine status
    if overall >= 90:
        status = "excellent"
    elif overall >= 70:
        status = "good"
    elif overall >= 50:
        status = "needs_improvement"
    else:
        status = "critical"

    report = {
        "assessment": "documentation-coverage",
        "project_dir": str(project_dir),
        "overall_coverage": overall,
        "status": status,
        "metrics": metrics,
        "summary": {
            "total_items": (
                metrics["skills"]["total"] +
                metrics["agents"]["total"] +
                metrics["commands"]["total"] +
                metrics["readmes"]["total"]
            ),
            "documented_items": (
                metrics["skills"]["documented"] +
                metrics["agents"]["documented"] +
                metrics["commands"]["documented"] +
                metrics["readmes"]["documented"]
            )
        }
    }

    print(json.dumps(report, indent=2))
    return 0 if overall >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
