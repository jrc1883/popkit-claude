#!/usr/bin/env python3
"""
Calculate Overall UX Score.

Combines command naming, error quality, and interaction patterns.

Usage:
    python calculate_ux_score.py [project_dir]

Output:
    JSON object with overall UX score
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


def evaluate_nielsen_heuristics(project_dir: Path) -> Dict[str, Any]:
    """Evaluate against Nielsen's 10 usability heuristics."""
    heuristics = {
        "NH-001": {"name": "Visibility of system status", "score": 0, "max": 10},
        "NH-002": {"name": "Match system and real world", "score": 0, "max": 10},
        "NH-003": {"name": "User control and freedom", "score": 0, "max": 10},
        "NH-004": {"name": "Consistency and standards", "score": 0, "max": 10},
        "NH-005": {"name": "Error prevention", "score": 0, "max": 10},
        "NH-006": {"name": "Recognition over recall", "score": 0, "max": 10},
        "NH-007": {"name": "Flexibility and efficiency", "score": 0, "max": 10},
        "NH-008": {"name": "Aesthetic and minimalist", "score": 0, "max": 10},
        "NH-009": {"name": "Help users with errors", "score": 0, "max": 10},
        "NH-010": {"name": "Help and documentation", "score": 0, "max": 10},
    }

    # NH-001: Visibility - check for progress indicators, status messages
    skills_dir = project_dir / "skills"
    if skills_dir.exists():
        status_skills = len(list(skills_dir.glob("*status*"))) + len(list(skills_dir.glob("*progress*")))
        heuristics["NH-001"]["score"] = min(10, 5 + status_skills)

    # NH-002: Real world match - check for natural language in commands
    commands_dir = project_dir / "commands"
    if commands_dir.exists():
        natural_commands = 0
        for cmd in commands_dir.glob("*.md"):
            name = cmd.stem.replace("-", " ")
            if any(word in name for word in ["create", "run", "check", "review", "analyze"]):
                natural_commands += 1
        heuristics["NH-002"]["score"] = min(10, 3 + natural_commands)

    # NH-003: User control - check for undo/cancel options
    hooks_dir = project_dir / "hooks"
    if hooks_dir.exists():
        control_hooks = len(list(hooks_dir.glob("*cancel*"))) + len(list(hooks_dir.glob("*undo*")))
        heuristics["NH-003"]["score"] = min(10, 4 + control_hooks * 2)

    # NH-004: Consistency - check for consistent naming patterns
    if commands_dir.exists():
        names = [f.stem for f in commands_dir.glob("*.md")]
        has_consistent_prefix = all("-" in name or len(name) < 10 for name in names)
        heuristics["NH-004"]["score"] = 8 if has_consistent_prefix else 5

    # NH-005: Error prevention - check for validation
    validation_count = 0
    for py_file in project_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            validation_count += content.count("validate") + content.count("check_")
        except:
            pass
    heuristics["NH-005"]["score"] = min(10, 3 + validation_count // 5)

    # NH-006: Recognition - check for autocomplete/suggestions
    config_path = project_dir / "agents" / "config.json"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8", errors="ignore")
        has_keywords = "keywords" in content
        has_triggers = "triggers" in content
        heuristics["NH-006"]["score"] = 7 if has_keywords and has_triggers else 4

    # NH-007: Flexibility - check for shortcuts/power user features
    power_mode = project_dir / "power-mode"
    heuristics["NH-007"]["score"] = 8 if power_mode.exists() else 5

    # NH-008: Minimalist - check for concise skill definitions
    if skills_dir.exists():
        avg_size = 0
        skills = list(skills_dir.glob("*/SKILL.md"))
        if skills:
            sizes = [s.stat().st_size for s in skills]
            avg_size = sum(sizes) / len(sizes)
        heuristics["NH-008"]["score"] = 8 if avg_size < 3000 else 5 if avg_size < 6000 else 3

    # NH-009: Error recovery - check for error handling
    try_except_count = 0
    for py_file in project_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            try_except_count += content.count("except") + content.count("catch")
        except:
            pass
    heuristics["NH-009"]["score"] = min(10, 3 + try_except_count // 10)

    # NH-010: Documentation - check for help/docs
    readme = project_dir / "README.md"
    claude_md = project_dir / "CLAUDE.md"
    has_docs = readme.exists() or claude_md.exists()
    docs_dir = project_dir / "docs"
    heuristics["NH-010"]["score"] = 9 if has_docs and docs_dir.exists() else 7 if has_docs else 4

    # Calculate total
    total = sum(h["score"] for h in heuristics.values())
    max_total = sum(h["max"] for h in heuristics.values())

    return {
        "heuristics": heuristics,
        "total_score": total,
        "max_score": max_total,
        "percentage": round(total / max_total * 100, 1)
    }


def evaluate_interaction_patterns(project_dir: Path) -> Dict[str, Any]:
    """Evaluate interaction patterns."""
    patterns = {
        "ask_user_question_usage": 0,
        "confirmation_prompts": 0,
        "progressive_disclosure": 0,
        "default_values": 0
    }
    issues = []

    # Check for AskUserQuestion usage
    for py_file in project_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            patterns["ask_user_question_usage"] += content.count("AskUserQuestion")
            patterns["confirmation_prompts"] += content.count("confirm")
        except:
            pass

    # Check for progressive disclosure in skills
    skills_dir = project_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                # Check if skill has resources directory (progressive loading)
                has_resources = (skill_dir / "scripts").exists() or (skill_dir / "standards").exists()
                if has_resources:
                    patterns["progressive_disclosure"] += 1

    # Check for default values in configs
    config_path = project_dir / "agents" / "config.json"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8", errors="ignore")
        patterns["default_values"] = content.count('"default"')

    # Issues
    if patterns["ask_user_question_usage"] < 5:
        issues.append({
            "type": "low_interactivity",
            "message": "Limited use of AskUserQuestion for user interaction",
            "severity": "medium"
        })

    return {
        "patterns": patterns,
        "issues": issues
    }


def calculate_final_score(
    nielsen: Dict,
    interactions: Dict
) -> Dict[str, Any]:
    """Calculate final UX score."""
    # Nielsen contributes 70%
    nielsen_component = nielsen.get("percentage", 0) * 0.7

    # Interaction patterns contribute 30%
    patterns = interactions.get("patterns", {})
    interaction_score = 0
    interaction_score += min(30, patterns.get("ask_user_question_usage", 0) * 3)
    interaction_score += min(20, patterns.get("progressive_disclosure", 0) * 2)
    interaction_score += min(20, patterns.get("default_values", 0) * 2)
    interaction_score += min(30, patterns.get("confirmation_prompts", 0) * 5)
    interaction_component = min(100, interaction_score) * 0.3

    final = nielsen_component + interaction_component

    return {
        "score": round(final, 1),
        "breakdown": {
            "nielsen": round(nielsen_component, 1),
            "interactions": round(interaction_component, 1)
        }
    }


def get_recommendations(nielsen: Dict, interactions: Dict) -> List[str]:
    """Generate UX recommendations."""
    recommendations = []

    # Nielsen-based recommendations
    heuristics = nielsen.get("heuristics", {})
    for hid, data in heuristics.items():
        if data["score"] < 5:
            recommendations.append(f"Improve {data['name']} (current score: {data['score']}/10)")

    # Interaction-based recommendations
    patterns = interactions.get("patterns", {})
    if patterns.get("ask_user_question_usage", 0) < 5:
        recommendations.append("Increase use of AskUserQuestion for better user interaction")

    if patterns.get("progressive_disclosure", 0) < 3:
        recommendations.append("Add more progressive disclosure patterns (load details on demand)")

    if not recommendations:
        recommendations.append("UX is in good shape - maintain current patterns")

    return recommendations[:5]


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Evaluate
    nielsen = evaluate_nielsen_heuristics(project_dir)
    interactions = evaluate_interaction_patterns(project_dir)

    # Calculate final score
    scoring = calculate_final_score(nielsen, interactions)
    score = scoring["score"]

    # Determine grade
    if score >= 90:
        grade = "A"
        status = "excellent"
    elif score >= 80:
        grade = "B"
        status = "good"
    elif score >= 70:
        grade = "C"
        status = "acceptable"
    elif score >= 60:
        grade = "D"
        status = "needs_improvement"
    else:
        grade = "F"
        status = "poor"

    recommendations = get_recommendations(nielsen, interactions)

    report = {
        "assessment": "ux-score",
        "project_dir": str(project_dir),
        "ux_score": score,
        "grade": grade,
        "status": status,
        "scoring_breakdown": scoring["breakdown"],
        "nielsen_heuristics": nielsen,
        "interaction_patterns": interactions,
        "recommendations": recommendations
    }

    print(json.dumps(report, indent=2))
    return 0 if score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
