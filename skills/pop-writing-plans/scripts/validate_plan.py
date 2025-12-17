#!/usr/bin/env python3
"""
Plan Structure Validator for PopKit.

Validates implementation plan documents for completeness and correctness.
Part of pop-writing-plans skill.

Usage:
    python validate_plan.py <plan_file.md>
    python validate_plan.py --json <plan_file.md>  # JSON output
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationIssue:
    """A validation issue found in the plan."""
    severity: str  # "error", "warning", "info"
    message: str
    line: Optional[int] = None
    task: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "task": self.task
        }


@dataclass
class ValidationResult:
    """Result of plan validation."""
    valid: bool
    score: int  # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats
        }


def validate_plan(plan_path: Path) -> ValidationResult:
    """Validate an implementation plan document.

    Checks:
    - Required header fields (Goal, Architecture, Tech Stack)
    - Task structure (Files, Steps)
    - Code blocks have language specifiers
    - Run commands have expected outputs
    - File paths are specific (not placeholders)
    - Commit messages follow convention

    Args:
        plan_path: Path to the plan markdown file

    Returns:
        ValidationResult with score and issues
    """
    if not plan_path.exists():
        return ValidationResult(
            valid=False,
            score=0,
            issues=[ValidationIssue("error", f"Plan file not found: {plan_path}")]
        )

    content = plan_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    issues: List[ValidationIssue] = []

    # Stats tracking
    stats = {
        "total_tasks": 0,
        "total_steps": 0,
        "code_blocks": 0,
        "run_commands": 0,
        "file_references": 0
    }

    # Check header
    issues.extend(_check_header(content, lines))

    # Check tasks
    task_issues, task_stats = _check_tasks(content, lines)
    issues.extend(task_issues)
    stats.update(task_stats)

    # Check code blocks
    issues.extend(_check_code_blocks(content, lines))
    stats["code_blocks"] = len(re.findall(r'```\w+', content))

    # Check file paths
    issues.extend(_check_file_paths(content, lines))
    stats["file_references"] = len(re.findall(r'`[a-zA-Z0-9_/.-]+\.[a-z]+`', content))

    # Check run commands
    issues.extend(_check_run_commands(content, lines))
    stats["run_commands"] = len(re.findall(r'Run:\s*`', content))

    # Calculate score
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    base_score = 100
    base_score -= error_count * 20
    base_score -= warning_count * 5
    score = max(0, min(100, base_score))

    valid = error_count == 0 and score >= 60

    return ValidationResult(
        valid=valid,
        score=score,
        issues=issues,
        stats=stats
    )


def _check_header(content: str, lines: List[str]) -> List[ValidationIssue]:
    """Check plan header for required fields."""
    issues = []

    # Check for title
    if not re.search(r'^#\s+.+Implementation Plan', content, re.MULTILINE):
        issues.append(ValidationIssue(
            "warning",
            "Plan title should include 'Implementation Plan'",
            line=1
        ))

    # Check for required fields
    required_fields = ["Goal:", "Architecture:", "Tech Stack:"]
    for field in required_fields:
        if field not in content:
            issues.append(ValidationIssue(
                "error",
                f"Missing required header field: {field}",
                line=1
            ))

    # Check for Claude instruction
    if "For Claude:" not in content and "executing-plans" not in content:
        issues.append(ValidationIssue(
            "info",
            "Consider adding Claude execution instruction in header"
        ))

    return issues


def _check_tasks(content: str, lines: List[str]) -> tuple:
    """Check task structure and completeness."""
    issues = []
    stats = {"total_tasks": 0, "total_steps": 0}

    # Find all tasks
    task_pattern = r'^###\s+Task\s+(\d+):\s+(.+)$'
    tasks = list(re.finditer(task_pattern, content, re.MULTILINE))
    stats["total_tasks"] = len(tasks)

    if len(tasks) == 0:
        issues.append(ValidationIssue(
            "error",
            "No tasks found. Use '### Task N: Name' format"
        ))
        return issues, stats

    # Check each task
    for i, task_match in enumerate(tasks):
        task_num = task_match.group(1)
        task_name = task_match.group(2)
        task_start = task_match.start()

        # Find task end (next task or end of file)
        if i + 1 < len(tasks):
            task_end = tasks[i + 1].start()
        else:
            task_end = len(content)

        task_content = content[task_start:task_end]

        # Check for Files section
        if "**Files:**" not in task_content and "Files:" not in task_content:
            issues.append(ValidationIssue(
                "warning",
                f"Task {task_num} missing Files section",
                task=task_name
            ))

        # Check for steps
        steps = re.findall(r'\*\*Step\s+\d+:', task_content)
        stats["total_steps"] += len(steps)

        if len(steps) == 0:
            issues.append(ValidationIssue(
                "warning",
                f"Task {task_num} has no numbered steps",
                task=task_name
            ))

        # Check for commit step
        if "commit" not in task_content.lower() and "Commit" not in task_content:
            issues.append(ValidationIssue(
                "info",
                f"Task {task_num} missing commit step",
                task=task_name
            ))

    # Check task numbering
    expected_nums = [str(i) for i in range(1, len(tasks) + 1)]
    actual_nums = [m.group(1) for m in tasks]
    if actual_nums != expected_nums:
        issues.append(ValidationIssue(
            "warning",
            f"Task numbering is not sequential: {actual_nums}"
        ))

    return issues, stats


def _check_code_blocks(content: str, lines: List[str]) -> List[ValidationIssue]:
    """Check code blocks for language specifiers."""
    issues = []

    # Find code blocks without language
    unlabeled = re.findall(r'```\s*\n', content)
    if unlabeled:
        issues.append(ValidationIssue(
            "warning",
            f"Found {len(unlabeled)} code blocks without language specifier"
        ))

    return issues


def _check_file_paths(content: str, lines: List[str]) -> List[ValidationIssue]:
    """Check file paths for specificity."""
    issues = []

    # Check for placeholder paths
    placeholders = [
        r'path/to/',
        r'your/',
        r'example/',
        r'\[path\]',
        r'<path>',
        r'xxx',
        r'\.\.\./'
    ]

    for placeholder in placeholders:
        if re.search(placeholder, content, re.IGNORECASE):
            issues.append(ValidationIssue(
                "error",
                f"Found placeholder in file path: '{placeholder}'"
            ))

    # Check for missing file extensions in Create/Modify
    create_modify = re.findall(r'(?:Create|Modify):\s*`([^`]+)`', content)
    for path in create_modify:
        if not re.search(r'\.\w+$', path) and not re.search(r':\d+-\d+$', path):
            issues.append(ValidationIssue(
                "warning",
                f"File path may be missing extension: {path}"
            ))

    return issues


def _check_run_commands(content: str, lines: List[str]) -> List[ValidationIssue]:
    """Check run commands have expected outputs."""
    issues = []

    # Find Run: commands
    run_commands = list(re.finditer(r'Run:\s*`([^`]+)`', content))

    for match in run_commands:
        # Check if followed by Expected:
        after_run = content[match.end():match.end() + 200]
        if "Expected:" not in after_run and "PASS" not in after_run and "FAIL" not in after_run:
            issues.append(ValidationIssue(
                "info",
                f"Run command may be missing expected output: {match.group(1)[:50]}"
            ))

    return issues


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_plan.py [--json] <plan_file.md>")
        sys.exit(1)

    json_output = "--json" in sys.argv
    plan_file = sys.argv[-1]

    result = validate_plan(Path(plan_file))

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # Human-readable output
        print(f"\n{'=' * 50}")
        print(f"Plan Validation: {plan_file}")
        print(f"{'=' * 50}")
        print(f"\nScore: {result.score}/100 {'[PASS]' if result.valid else '[FAIL]'}")
        print(f"\nStats:")
        for key, value in result.stats.items():
            print(f"  {key}: {value}")

        if result.issues:
            print(f"\nIssues ({len(result.issues)}):")
            for issue in result.issues:
                prefix = {"error": "[ERROR]", "warning": "[WARN]", "info": "[INFO]"}[issue.severity]
                location = f" (Task: {issue.task})" if issue.task else ""
                location = f" (Line: {issue.line})" if issue.line else location
                print(f"  {prefix} {issue.message}{location}")
        else:
            print("\nNo issues found!")

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
