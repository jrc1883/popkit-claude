#!/usr/bin/env python3
"""
Analyze Error Message Quality.

Evaluates error messages for clarity, helpfulness, and actionability.

Usage:
    python analyze_errors.py [project_dir]

Output:
    JSON object with error message analysis results
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


def find_error_messages(project_dir: Path) -> List[Dict[str, Any]]:
    """Find error messages in code files."""
    errors = []

    # Patterns to find error messages
    patterns = [
        (r'raise\s+\w+Error\s*\(\s*["\']([^"\']+)["\']', "python_raise"),
        (r'raise\s+\w+Exception\s*\(\s*["\']([^"\']+)["\']', "python_raise"),
        (r'print\s*\(\s*["\']error[^"\']*["\']', "python_print"),
        (r'console\.error\s*\(\s*[`"\']([^`"\']+)[`"\']', "js_console"),
        (r'throw\s+new\s+Error\s*\(\s*[`"\']([^`"\']+)[`"\']', "js_throw"),
        (r'"error":\s*["\']([^"\']+)["\']', "json_error"),
    ]

    for ext in ["*.py", "*.ts", "*.js"]:
        for file_path in project_dir.rglob(ext):
            if "node_modules" in str(file_path) or "__pycache__" in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(project_dir))

                for pattern, error_type in patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        message = match.group(1) if match.groups() else match.group(0)
                        errors.append({
                            "file": rel_path,
                            "type": error_type,
                            "message": message[:100],
                            "line": content[:match.start()].count("\n") + 1
                        })
            except:
                pass

    return errors[:50]  # Limit to 50


def analyze_error_quality(errors: List[Dict]) -> Dict[str, Any]:
    """Analyze quality of error messages."""
    issues = []
    quality_scores = []

    for error in errors:
        message = error.get("message", "")
        score = 100

        # Check for vague messages
        vague_patterns = [
            "error occurred",
            "something went wrong",
            "failed",
            "invalid",
            "bad request",
            "unknown error",
        ]

        for vague in vague_patterns:
            if vague.lower() in message.lower() and len(message) < 30:
                issues.append({
                    "file": error["file"],
                    "message": message,
                    "issue": f"Vague error message: '{vague}'",
                    "severity": "medium"
                })
                score -= 20
                break

        # Check for technical jargon without context
        jargon = ["ENOENT", "EACCES", "EPERM", "null", "undefined", "NaN"]
        for term in jargon:
            if term in message and ":" not in message:
                issues.append({
                    "file": error["file"],
                    "message": message,
                    "issue": f"Technical jargon '{term}' without explanation",
                    "severity": "low"
                })
                score -= 10
                break

        # Check for actionable guidance
        action_words = ["try", "check", "ensure", "verify", "run", "install", "update", "see"]
        has_action = any(word in message.lower() for word in action_words)
        if not has_action and len(message) > 20:
            score -= 5

        # Check for user-friendly tone
        harsh_words = ["stupid", "wrong", "idiot", "dumb", "fail"]
        for word in harsh_words:
            if word in message.lower():
                issues.append({
                    "file": error["file"],
                    "message": message,
                    "issue": f"Harsh language in error: '{word}'",
                    "severity": "high"
                })
                score -= 25
                break

        quality_scores.append(max(0, score))

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 100

    return {
        "total_errors": len(errors),
        "average_quality": round(avg_quality, 1),
        "issues": issues[:20]
    }


def analyze_error_patterns(errors: List[Dict]) -> Dict[str, Any]:
    """Analyze error message patterns for consistency."""
    patterns = {
        "has_context": 0,
        "has_suggestion": 0,
        "has_code": 0,
        "is_templated": 0
    }

    for error in errors:
        message = error.get("message", "")

        # Check for context (file path, variable name, etc.)
        if re.search(r"'[^']+'" , message) or re.search(r'"[^"]+"', message):
            patterns["has_context"] += 1

        # Check for suggestions
        if any(word in message.lower() for word in ["try", "check", "ensure", "should"]):
            patterns["has_suggestion"] += 1

        # Check for error codes
        if re.search(r"[A-Z]{2,}-\d+|E\d{4}", message):
            patterns["has_code"] += 1

        # Check for template placeholders
        if re.search(r"\{[^}]+\}|%[sd]|\$\w+", message):
            patterns["is_templated"] += 1

    total = len(errors) if errors else 1
    percentages = {k: round(v / total * 100, 1) for k, v in patterns.items()}

    return {
        "counts": patterns,
        "percentages": percentages
    }


def analyze_error_consistency(project_dir: Path) -> Dict[str, Any]:
    """Check for consistent error handling patterns."""
    issues = []

    # Check for custom error classes
    custom_errors = set()
    for py_file in project_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8", errors="ignore")

        # Find custom error classes
        for match in re.finditer(r"class\s+(\w+Error)\s*\(", content):
            custom_errors.add(match.group(1))

    # Check if custom errors are used consistently
    if len(custom_errors) > 5:
        issues.append({
            "type": "too_many_error_classes",
            "message": f"Found {len(custom_errors)} custom error classes - consider consolidating",
            "severity": "low"
        })

    return {
        "custom_error_classes": list(custom_errors),
        "issues": issues
    }


def calculate_error_score(
    quality: Dict,
    patterns: Dict,
    consistency: Dict
) -> float:
    """Calculate overall error message score."""
    score = quality.get("average_quality", 100)

    # Bonus for good patterns
    percentages = patterns.get("percentages", {})
    if percentages.get("has_suggestion", 0) > 50:
        score += 5
    if percentages.get("has_context", 0) > 60:
        score += 5

    # Deduct for consistency issues
    for issue in consistency.get("issues", []):
        score -= 3

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

    # Find and analyze errors
    errors = find_error_messages(project_dir)
    quality = analyze_error_quality(errors)
    patterns = analyze_error_patterns(errors)
    consistency = analyze_error_consistency(project_dir)

    # Calculate score
    error_score = calculate_error_score(quality, patterns, consistency)

    # Determine status
    if error_score >= 90:
        status = "excellent"
    elif error_score >= 70:
        status = "good"
    elif error_score >= 50:
        status = "needs_improvement"
    else:
        status = "poor"

    report = {
        "assessment": "error-analysis",
        "project_dir": str(project_dir),
        "error_score": error_score,
        "status": status,
        "quality_analysis": quality,
        "pattern_analysis": patterns,
        "consistency_analysis": consistency,
        "sample_errors": errors[:10]
    }

    print(json.dumps(report, indent=2))
    return 0 if error_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
