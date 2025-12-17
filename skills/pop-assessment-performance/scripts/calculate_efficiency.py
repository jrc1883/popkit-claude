#!/usr/bin/env python3
"""
Calculate Overall Efficiency Score.

Combines context usage, loading patterns, and runtime metrics.

Usage:
    python calculate_efficiency.py [project_dir]

Output:
    JSON object with overall efficiency score
"""

import json
import os
import sys
from datetime import datetime
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


def measure_file_complexity(project_dir: Path) -> Dict[str, Any]:
    """Measure file complexity metrics."""
    metrics = {
        "total_files": 0,
        "large_files": [],
        "deep_nesting": [],
        "complex_files": []
    }

    for ext in ["*.py", "*.ts", "*.js", "*.md", "*.json"]:
        for file_path in project_dir.rglob(ext):
            if "node_modules" in str(file_path) or "__pycache__" in str(file_path):
                continue

            metrics["total_files"] += 1

            try:
                stat = file_path.stat()
                size_kb = stat.st_size / 1024

                if size_kb > 50:
                    metrics["large_files"].append({
                        "path": str(file_path.relative_to(project_dir)),
                        "size_kb": round(size_kb, 2)
                    })

                # Check nesting for code files
                if ext in ["*.py", "*.ts", "*.js"]:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")

                    # Find max indentation
                    max_indent = 0
                    for line in lines:
                        if line.strip():
                            indent = len(line) - len(line.lstrip())
                            spaces = indent if line[0] == " " else indent * 4
                            max_indent = max(max_indent, spaces // 4)

                    if max_indent > 6:
                        metrics["deep_nesting"].append({
                            "path": str(file_path.relative_to(project_dir)),
                            "max_depth": max_indent
                        })

            except Exception:
                pass

    # Limit lists
    metrics["large_files"] = sorted(metrics["large_files"], key=lambda x: x["size_kb"], reverse=True)[:10]
    metrics["deep_nesting"] = metrics["deep_nesting"][:10]

    return metrics


def analyze_caching_opportunities(project_dir: Path) -> Dict[str, Any]:
    """Identify caching opportunities."""
    opportunities = []
    implementations = []

    # Check for existing caching patterns
    cache_patterns = [
        (r"@cache|@lru_cache|@cached", "Python caching decorator"),
        (r"\.cache\s*=|_cache\s*=", "Manual cache variable"),
        (r"memo\w*\s*=|useMemo|useCallback", "React memoization"),
    ]

    for py_file in project_dir.rglob("*.py"):
        if "node_modules" in str(py_file) or "__pycache__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8", errors="ignore")

        import re
        for pattern, desc in cache_patterns:
            if re.search(pattern, content):
                implementations.append({
                    "file": str(py_file.relative_to(project_dir)),
                    "pattern": desc
                })

        # Look for expensive operations without caching
        expensive_uncached = [
            (r"def.*\n.*\.rglob\(", "Recursive glob without caching"),
            (r"json\.loads?\(.*\.read", "JSON parsing without caching"),
        ]

        for pattern, desc in expensive_uncached:
            if re.search(pattern, content):
                opportunities.append({
                    "file": str(py_file.relative_to(project_dir)),
                    "opportunity": desc
                })

    return {
        "existing_implementations": implementations[:10],
        "opportunities": opportunities[:10]
    }


def measure_bundle_impact(project_dir: Path) -> Dict[str, Any]:
    """Measure impact on bundle/distribution size."""
    categories = {
        "scripts": {"pattern": "*.py", "count": 0, "size_kb": 0},
        "configs": {"pattern": "*.json", "count": 0, "size_kb": 0},
        "markdown": {"pattern": "*.md", "count": 0, "size_kb": 0},
        "typescript": {"pattern": "*.ts", "count": 0, "size_kb": 0},
    }

    for cat_name, cat_data in categories.items():
        for file_path in project_dir.rglob(cat_data["pattern"]):
            if "node_modules" in str(file_path) or "__pycache__" in str(file_path):
                continue
            cat_data["count"] += 1
            cat_data["size_kb"] += file_path.stat().st_size / 1024

        cat_data["size_kb"] = round(cat_data["size_kb"], 2)
        del cat_data["pattern"]

    total_size = sum(c["size_kb"] for c in categories.values())

    return {
        "categories": categories,
        "total_size_kb": round(total_size, 2),
        "total_size_mb": round(total_size / 1024, 2)
    }


def calculate_efficiency_score(
    complexity: Dict,
    caching: Dict,
    bundle: Dict
) -> Dict[str, Any]:
    """Calculate overall efficiency score."""
    score = 100
    issues = []

    # Deduct for large files
    large_count = len(complexity.get("large_files", []))
    if large_count > 5:
        score -= min(15, large_count * 2)
        issues.append(f"{large_count} files over 50KB")

    # Deduct for deep nesting
    nesting_count = len(complexity.get("deep_nesting", []))
    if nesting_count > 3:
        score -= min(10, nesting_count * 2)
        issues.append(f"{nesting_count} files with deep nesting")

    # Reward for caching implementations
    cache_impl = len(caching.get("existing_implementations", []))
    if cache_impl > 3:
        score += 5

    # Deduct for missed caching opportunities
    cache_opps = len(caching.get("opportunities", []))
    if cache_opps > 5:
        score -= min(10, cache_opps)
        issues.append(f"{cache_opps} caching opportunities identified")

    # Bundle size check
    total_mb = bundle.get("total_size_mb", 0)
    if total_mb > 5:
        score -= 10
        issues.append(f"Total size {total_mb}MB exceeds 5MB target")
    elif total_mb > 2:
        score -= 5

    return {
        "score": max(0, min(100, round(score))),
        "issues": issues
    }


def get_recommendations(
    complexity: Dict,
    caching: Dict,
    bundle: Dict,
    scoring: Dict
) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    if len(complexity.get("large_files", [])) > 3:
        recommendations.append("Consider splitting large files (>50KB) into smaller modules")

    if len(complexity.get("deep_nesting", [])) > 0:
        recommendations.append("Reduce nesting depth in complex functions (target: <5 levels)")

    if len(caching.get("opportunities", [])) > 0:
        recommendations.append("Add caching for expensive operations (glob, JSON parsing)")

    if bundle.get("total_size_mb", 0) > 2:
        recommendations.append("Review and remove unused files to reduce distribution size")

    if not recommendations:
        recommendations.append("Plugin efficiency is good - maintain current practices")

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

    # Gather metrics
    complexity = measure_file_complexity(project_dir)
    caching = analyze_caching_opportunities(project_dir)
    bundle = measure_bundle_impact(project_dir)

    # Calculate score
    scoring = calculate_efficiency_score(complexity, caching, bundle)

    # Determine grade
    score = scoring["score"]
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
        status = "critical"

    recommendations = get_recommendations(complexity, caching, bundle, scoring)

    report = {
        "assessment": "efficiency-score",
        "project_dir": str(project_dir),
        "efficiency_score": score,
        "grade": grade,
        "status": status,
        "metrics": {
            "file_complexity": {
                "total_files": complexity["total_files"],
                "large_files_count": len(complexity["large_files"]),
                "deep_nesting_count": len(complexity["deep_nesting"])
            },
            "caching": {
                "implementations": len(caching["existing_implementations"]),
                "opportunities": len(caching["opportunities"])
            },
            "bundle": bundle
        },
        "details": {
            "complexity": complexity,
            "caching": caching
        },
        "issues": scoring["issues"],
        "recommendations": recommendations
    }

    print(json.dumps(report, indent=2))
    return 0 if score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
