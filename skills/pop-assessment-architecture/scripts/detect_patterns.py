#!/usr/bin/env python3
"""
Detect Architecture Patterns in Codebase.

Identifies common design patterns, anti-patterns, and architectural concerns.

Usage:
    python detect_patterns.py [project_dir]

Output:
    JSON object with detected patterns and anti-patterns
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


def detect_design_patterns(project_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Detect common design patterns in the codebase."""
    patterns = {
        "singleton": [],
        "factory": [],
        "observer": [],
        "strategy": [],
        "decorator": [],
        "adapter": [],
        "repository": [],
        "service": [],
    }

    # Pattern detection rules
    pattern_rules = {
        "singleton": [
            r"private\s+static\s+instance",
            r"getInstance\s*\(\)",
            r"_instance\s*=\s*None",
            r"__new__.*cls\._instance",
        ],
        "factory": [
            r"create\w+\s*\(",
            r"Factory\s*[({]",
            r"make\w+\s*\(",
            r"build\w+\s*\(",
        ],
        "observer": [
            r"subscribe\s*\(",
            r"unsubscribe\s*\(",
            r"notify\s*\(",
            r"addEventListener",
            r"on\w+\s*:\s*\[",
        ],
        "strategy": [
            r"Strategy\s*[({]",
            r"setStrategy\s*\(",
            r"interface\s+\w+Strategy",
        ],
        "decorator": [
            r"@\w+\s*\n",
            r"Decorator\s*[({]",
            r"wrap\s*\(",
        ],
        "repository": [
            r"Repository\s*[({]",
            r"findBy\w+\s*\(",
            r"findAll\s*\(",
            r"save\s*\(",
            r"delete\s*\(",
        ],
        "service": [
            r"\w+Service\s*[({]",
            r"class\s+\w+Service",
        ],
    }

    # Scan files for patterns
    for ext in ["*.py", "*.ts", "*.js", "*.java"]:
        for file_path in project_dir.rglob(ext):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(project_dir))

                for pattern_name, rules in pattern_rules.items():
                    for rule in rules:
                        if re.search(rule, content):
                            patterns[pattern_name].append({
                                "file": rel_path,
                                "pattern": rule,
                                "confidence": "medium"
                            })
                            break  # One match per pattern per file
            except:
                pass

    return patterns


def detect_anti_patterns(project_dir: Path) -> List[Dict[str, Any]]:
    """Detect common anti-patterns in the codebase."""
    anti_patterns = []

    # Anti-pattern detection rules
    anti_pattern_rules = [
        {
            "name": "god_class",
            "description": "Class with too many responsibilities",
            "patterns": [r"class\s+\w+"],
            "threshold": {"lines": 500, "methods": 20},
        },
        {
            "name": "deep_nesting",
            "description": "Excessive control flow nesting",
            "patterns": [r"^\s{16,}(if|for|while|try)"],
            "severity": "medium",
        },
        {
            "name": "magic_numbers",
            "description": "Hardcoded numeric values without constants",
            "patterns": [r"[^a-zA-Z0-9_]\d{3,}[^a-zA-Z0-9_]"],
            "severity": "low",
        },
        {
            "name": "long_method",
            "description": "Methods exceeding recommended length",
            "patterns": [r"(def|function)\s+\w+"],
            "threshold": {"lines": 50},
        },
        {
            "name": "circular_dependency",
            "description": "Files importing each other",
            "patterns": [r"from\s+\.\w+\s+import|import\s+\{\s*\w+\s*\}\s+from\s+['\"]\."],
            "severity": "high",
        },
        {
            "name": "string_concatenation",
            "description": "String concatenation instead of templates",
            "patterns": [r"['\"].*['\"].*\+.*['\"]"],
            "severity": "low",
        },
        {
            "name": "callback_hell",
            "description": "Deeply nested callbacks",
            "patterns": [r"=>\s*\{[^}]*=>\s*\{[^}]*=>\s*\{"],
            "severity": "medium",
        },
    ]

    for ext in ["*.py", "*.ts", "*.js"]:
        for file_path in project_dir.rglob(ext):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                rel_path = str(file_path.relative_to(project_dir))

                for rule in anti_pattern_rules:
                    for pattern in rule["patterns"]:
                        matches = re.findall(pattern, content, re.MULTILINE)
                        if matches and len(matches) > 0:
                            # Apply thresholds if defined
                            if "threshold" in rule:
                                if rule["name"] == "god_class" and len(lines) > rule["threshold"]["lines"]:
                                    anti_patterns.append({
                                        "name": rule["name"],
                                        "description": rule["description"],
                                        "file": rel_path,
                                        "details": f"File has {len(lines)} lines",
                                        "severity": "high"
                                    })
                                elif rule["name"] == "long_method":
                                    # Simplified check - just flag files with many function definitions
                                    if len(matches) > 10:
                                        anti_patterns.append({
                                            "name": rule["name"],
                                            "description": rule["description"],
                                            "file": rel_path,
                                            "details": f"File has {len(matches)} methods",
                                            "severity": "medium"
                                        })
                            else:
                                anti_patterns.append({
                                    "name": rule["name"],
                                    "description": rule["description"],
                                    "file": rel_path,
                                    "details": f"Found {len(matches)} occurrences",
                                    "severity": rule.get("severity", "medium")
                                })
                            break
            except:
                pass

    return anti_patterns


def detect_solid_violations(project_dir: Path) -> List[Dict[str, Any]]:
    """Detect potential SOLID principle violations."""
    violations = []

    # Simplified SOLID checks
    solid_checks = [
        {
            "principle": "SRP",
            "name": "Single Responsibility",
            "check": lambda f, c: len(c.split("\n")) > 300,
            "message": "File may have multiple responsibilities (>300 lines)"
        },
        {
            "principle": "DIP",
            "name": "Dependency Inversion",
            "pattern": r"new\s+\w+\s*\(",
            "message": "Direct instantiation may violate dependency inversion"
        },
    ]

    for ext in ["*.py", "*.ts", "*.js"]:
        for file_path in project_dir.rglob(ext):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(project_dir))

                for check in solid_checks:
                    if "check" in check:
                        if check["check"](file_path, content):
                            violations.append({
                                "principle": check["principle"],
                                "name": check["name"],
                                "file": rel_path,
                                "message": check["message"]
                            })
                    elif "pattern" in check:
                        if re.search(check["pattern"], content):
                            # Only flag if many occurrences
                            matches = len(re.findall(check["pattern"], content))
                            if matches > 5:
                                violations.append({
                                    "principle": check["principle"],
                                    "name": check["name"],
                                    "file": rel_path,
                                    "message": f"{check['message']} ({matches} instances)"
                                })
            except:
                pass

    return violations


def calculate_pattern_score(
    patterns: Dict[str, List],
    anti_patterns: List[Dict],
    solid_violations: List[Dict]
) -> Dict[str, Any]:
    """Calculate pattern quality score."""
    score = 100

    # Count positive patterns (good)
    total_patterns = sum(len(p) for p in patterns.values())
    if total_patterns < 3:
        score -= 5  # Small deduction for limited pattern usage

    # Deduct for anti-patterns
    severity_weights = {"high": 10, "medium": 5, "low": 2}
    for ap in anti_patterns:
        weight = severity_weights.get(ap.get("severity", "medium"), 5)
        score -= min(weight, 20)  # Cap per anti-pattern

    # Deduct for SOLID violations
    score -= len(solid_violations) * 3

    return {
        "score": max(0, min(100, score)),
        "patterns_found": total_patterns,
        "anti_patterns_found": len(anti_patterns),
        "solid_violations": len(solid_violations)
    }


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Run detection
    patterns = detect_design_patterns(project_dir)
    anti_patterns = detect_anti_patterns(project_dir)
    solid_violations = detect_solid_violations(project_dir)
    scoring = calculate_pattern_score(patterns, anti_patterns, solid_violations)

    # Filter to only patterns with findings
    patterns_summary = {k: len(v) for k, v in patterns.items() if v}

    # Build report
    report = {
        "assessment": "architecture-patterns",
        "project_dir": str(project_dir),
        "design_patterns": {
            "summary": patterns_summary,
            "total": sum(patterns_summary.values()),
            "details": {k: v[:5] for k, v in patterns.items() if v}  # Limit details
        },
        "anti_patterns": {
            "count": len(anti_patterns),
            "findings": anti_patterns[:20]  # Limit to top 20
        },
        "solid_violations": {
            "count": len(solid_violations),
            "findings": solid_violations[:10]  # Limit to top 10
        },
        "scoring": scoring
    }

    print(json.dumps(report, indent=2))
    return 0 if scoring["score"] >= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
