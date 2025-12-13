#!/usr/bin/env python3
"""
Analyze Project Structure for Architecture Assessment.

Examines project organization, module boundaries, and structural patterns.

Usage:
    python analyze_structure.py [project_dir]

Output:
    JSON object with structure analysis and recommendations
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        # Look for common project markers
        if (current / "package.json").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        if (current / "packages" / "plugin").exists():
            return current
        current = current.parent

    return start_path


def analyze_directory_structure(project_dir: Path) -> Dict[str, Any]:
    """Analyze the directory structure of the project."""
    structure = {
        "depth": 0,
        "total_dirs": 0,
        "total_files": 0,
        "file_types": defaultdict(int),
        "large_directories": [],
        "empty_directories": [],
        "hidden_directories": [],
    }

    max_depth = 0
    file_count_by_dir = defaultdict(int)

    for item in project_dir.rglob("*"):
        if item.is_dir():
            structure["total_dirs"] += 1

            # Check for hidden directories
            if item.name.startswith(".") and item.name not in [".git", ".github"]:
                structure["hidden_directories"].append(str(item.relative_to(project_dir)))

            # Track depth
            depth = len(item.relative_to(project_dir).parts)
            max_depth = max(max_depth, depth)

            # Check for empty directories
            if not any(item.iterdir()):
                structure["empty_directories"].append(str(item.relative_to(project_dir)))

        elif item.is_file():
            structure["total_files"] += 1

            # Track file types
            suffix = item.suffix.lower() or "no_extension"
            structure["file_types"][suffix] += 1

            # Track files per directory
            parent = str(item.parent.relative_to(project_dir))
            file_count_by_dir[parent] += 1

    structure["depth"] = max_depth
    structure["file_types"] = dict(structure["file_types"])

    # Find directories with many files (potential organization issues)
    for dir_path, count in file_count_by_dir.items():
        if count > 20:  # Threshold for "large" directory
            structure["large_directories"].append({
                "path": dir_path,
                "file_count": count
            })

    return structure


def detect_architecture_patterns(project_dir: Path) -> Dict[str, Any]:
    """Detect common architecture patterns in the project."""
    patterns = {
        "detected": [],
        "confidence_scores": {},
        "recommendations": []
    }

    # Check for common patterns
    pattern_indicators = {
        "monorepo": [
            ("packages", "dir"),
            ("lerna.json", "file"),
            ("pnpm-workspace.yaml", "file"),
        ],
        "clean_architecture": [
            ("domain", "dir"),
            ("application", "dir"),
            ("infrastructure", "dir"),
            ("interfaces", "dir"),
        ],
        "mvc": [
            ("models", "dir"),
            ("views", "dir"),
            ("controllers", "dir"),
        ],
        "feature_based": [
            ("features", "dir"),
            ("modules", "dir"),
        ],
        "layered": [
            ("api", "dir"),
            ("services", "dir"),
            ("repositories", "dir"),
            ("entities", "dir"),
        ],
        "component_based": [
            ("components", "dir"),
            ("containers", "dir"),
            ("hooks", "dir"),
        ],
    }

    for pattern_name, indicators in pattern_indicators.items():
        matches = 0
        total = len(indicators)

        for indicator, indicator_type in indicators:
            if indicator_type == "dir":
                # Search for directory
                if any(project_dir.rglob(indicator)):
                    matches += 1
            elif indicator_type == "file":
                if (project_dir / indicator).exists():
                    matches += 1

        if matches > 0:
            confidence = round((matches / total) * 100)
            patterns["confidence_scores"][pattern_name] = confidence

            if confidence >= 50:
                patterns["detected"].append(pattern_name)

    # Generate recommendations based on detected patterns
    if not patterns["detected"]:
        patterns["recommendations"].append({
            "priority": "medium",
            "message": "No clear architecture pattern detected. Consider adopting a consistent structure."
        })
    elif len(patterns["detected"]) > 2:
        patterns["recommendations"].append({
            "priority": "low",
            "message": "Multiple architecture patterns detected. Ensure intentional design."
        })

    return patterns


def analyze_module_boundaries(project_dir: Path) -> Dict[str, Any]:
    """Analyze module boundaries and potential violations."""
    boundaries = {
        "modules": [],
        "potential_violations": [],
        "cross_cutting_concerns": []
    }

    # Common module boundary indicators
    module_markers = ["index.ts", "index.js", "index.py", "__init__.py", "mod.rs"]

    # Find potential modules
    for marker in module_markers:
        for marker_file in project_dir.rglob(marker):
            module_dir = marker_file.parent
            rel_path = str(module_dir.relative_to(project_dir))

            if rel_path != ".":
                boundaries["modules"].append({
                    "path": rel_path,
                    "marker": marker,
                    "files": len(list(module_dir.glob("*")))
                })

    # Check for potential boundary violations (imports across boundaries)
    # This is a simplified check - just looking for patterns
    suspicious_patterns = [
        "../../",  # Deep relative imports
        "../../../",  # Very deep relative imports
    ]

    for py_file in project_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in suspicious_patterns:
                if pattern in content:
                    boundaries["potential_violations"].append({
                        "file": str(py_file.relative_to(project_dir)),
                        "issue": f"Deep relative import ({pattern})",
                        "severity": "warning"
                    })
                    break
        except:
            pass

    for ts_file in project_dir.rglob("*.ts"):
        try:
            content = ts_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in suspicious_patterns:
                if pattern in content:
                    boundaries["potential_violations"].append({
                        "file": str(ts_file.relative_to(project_dir)),
                        "issue": f"Deep relative import ({pattern})",
                        "severity": "warning"
                    })
                    break
        except:
            pass

    # Identify cross-cutting concerns
    cross_cutting_dirs = ["utils", "common", "shared", "helpers", "lib"]
    for dir_name in cross_cutting_dirs:
        for found_dir in project_dir.rglob(dir_name):
            if found_dir.is_dir():
                boundaries["cross_cutting_concerns"].append(
                    str(found_dir.relative_to(project_dir))
                )

    return boundaries


def calculate_structure_score(
    structure: Dict[str, Any],
    patterns: Dict[str, Any],
    boundaries: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate overall structure quality score."""
    score = 100
    deductions = []

    # Deduct for deep nesting
    if structure["depth"] > 8:
        deduct = min(15, (structure["depth"] - 8) * 3)
        score -= deduct
        deductions.append({
            "reason": f"Deep directory nesting ({structure['depth']} levels)",
            "points": deduct
        })

    # Deduct for large directories
    if structure["large_directories"]:
        deduct = min(15, len(structure["large_directories"]) * 5)
        score -= deduct
        deductions.append({
            "reason": f"{len(structure['large_directories'])} directories with >20 files",
            "points": deduct
        })

    # Deduct for no clear architecture
    if not patterns["detected"]:
        score -= 10
        deductions.append({
            "reason": "No clear architecture pattern",
            "points": 10
        })

    # Deduct for boundary violations
    violation_count = len(boundaries["potential_violations"])
    if violation_count > 0:
        deduct = min(20, violation_count * 2)
        score -= deduct
        deductions.append({
            "reason": f"{violation_count} potential module boundary violations",
            "points": deduct
        })

    # Deduct for empty directories
    empty_count = len(structure["empty_directories"])
    if empty_count > 3:
        deduct = min(5, empty_count - 3)
        score -= deduct
        deductions.append({
            "reason": f"{empty_count} empty directories",
            "points": deduct
        })

    return {
        "score": max(0, score),
        "grade": get_grade(score),
        "deductions": deductions
    }


def get_grade(score: int) -> str:
    """Convert score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Run analysis
    structure = analyze_directory_structure(project_dir)
    patterns = detect_architecture_patterns(project_dir)
    boundaries = analyze_module_boundaries(project_dir)
    scoring = calculate_structure_score(structure, patterns, boundaries)

    # Build report
    report = {
        "assessment": "architecture-structure",
        "project_dir": str(project_dir),
        "structure": structure,
        "patterns": patterns,
        "module_boundaries": boundaries,
        "scoring": scoring,
        "recommendations": patterns.get("recommendations", [])
    }

    print(json.dumps(report, indent=2))
    return 0 if scoring["score"] >= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
