#!/usr/bin/env python3
"""
Analyze Loading Patterns.

Examines lazy loading, startup overhead, and file access patterns.

Usage:
    python analyze_loading.py [project_dir]

Output:
    JSON object with loading analysis results
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
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def analyze_tier_distribution(project_dir: Path) -> Dict[str, Any]:
    """Analyze agent tier distribution for lazy loading."""
    agents_dir = project_dir / "agents"
    if not agents_dir.exists():
        return {"tiers": {}, "issues": []}

    tiers = {
        "tier-1-always-active": 0,
        "tier-2-on-demand": 0,
        "feature-workflow": 0
    }
    issues = []

    for tier_name in tiers.keys():
        tier_dir = agents_dir / tier_name
        if tier_dir.exists():
            count = len(list(tier_dir.glob("*/")))
            tiers[tier_name] = count

    # Check tier 1 count
    tier1_count = tiers.get("tier-1-always-active", 0)
    if tier1_count > 20:
        issues.append({
            "type": "tier_1_overload",
            "message": f"Tier 1 has {tier1_count} agents (limit: 20)",
            "severity": "critical"
        })
    elif tier1_count > 15:
        issues.append({
            "type": "tier_1_warning",
            "message": f"Tier 1 has {tier1_count} agents (target: <=15)",
            "severity": "medium"
        })

    # Calculate ratio
    total = sum(tiers.values())
    tier1_ratio = (tier1_count / total * 100) if total > 0 else 0

    return {
        "tiers": tiers,
        "total_agents": total,
        "tier_1_ratio": round(tier1_ratio, 1),
        "lazy_load_ratio": round(100 - tier1_ratio, 1),
        "issues": issues
    }


def analyze_startup_files(project_dir: Path) -> Dict[str, Any]:
    """Analyze files that must be read at startup."""
    startup_files = [
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "agents/config.json",
        "hooks/hooks.json",
        ".mcp.json",
        "CLAUDE.md",
    ]

    found_files = []
    total_size = 0
    issues = []

    for file_path in startup_files:
        full_path = project_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            total_size += size
            found_files.append({
                "path": file_path,
                "size_bytes": size,
                "size_kb": round(size / 1024, 2)
            })

    # Check total startup size
    total_kb = total_size / 1024
    if total_kb > 100:
        issues.append({
            "type": "startup_size",
            "message": f"Startup files total {round(total_kb)}KB (target: <50KB)",
            "severity": "medium"
        })

    # Check file count
    if len(found_files) > 10:
        issues.append({
            "type": "startup_count",
            "message": f"{len(found_files)} startup files (target: <10)",
            "severity": "low"
        })

    return {
        "files": found_files,
        "count": len(found_files),
        "total_size_kb": round(total_kb, 2),
        "issues": issues
    }


def analyze_hook_efficiency(project_dir: Path) -> Dict[str, Any]:
    """Analyze hook execution efficiency."""
    hooks_dir = project_dir / "hooks"
    if not hooks_dir.exists():
        return {"hooks": [], "issues": []}

    hooks = []
    issues = []

    for hook_file in hooks_dir.glob("*.py"):
        if hook_file.name.startswith("_"):
            continue

        content = hook_file.read_text(encoding="utf-8", errors="ignore")
        lines = len(content.split("\n"))

        # Check for imports
        imports = re.findall(r"^(?:from|import)\s+", content, re.MULTILINE)

        # Check for expensive operations
        expensive_patterns = [
            (r"subprocess\.", "subprocess calls"),
            (r"requests\.", "HTTP requests"),
            (r"\.rglob\(", "recursive glob"),
            (r"time\.sleep\(", "sleep calls"),
        ]

        expensive_ops = []
        for pattern, desc in expensive_patterns:
            if re.search(pattern, content):
                expensive_ops.append(desc)

        hook_data = {
            "name": hook_file.stem,
            "lines": lines,
            "imports": len(imports),
            "expensive_ops": expensive_ops
        }

        if expensive_ops:
            issues.append({
                "hook": hook_file.stem,
                "type": "expensive_operations",
                "operations": expensive_ops,
                "severity": "medium"
            })

        if lines > 200:
            issues.append({
                "hook": hook_file.stem,
                "type": "complex_hook",
                "message": f"Hook has {lines} lines (target: <100)",
                "severity": "low"
            })

        hooks.append(hook_data)

    return {
        "hooks": hooks,
        "total_hooks": len(hooks),
        "issues": issues
    }


def analyze_import_patterns(project_dir: Path) -> Dict[str, Any]:
    """Analyze import patterns for lazy loading opportunities."""
    utils_dir = project_dir / "hooks" / "utils"
    if not utils_dir.exists():
        return {"modules": [], "issues": []}

    modules = []
    issues = []
    import_graph = {}

    for py_file in utils_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")

        # Find internal imports
        internal_imports = re.findall(
            r"from\s+\.(\w+)\s+import|import\s+\.(\w+)",
            content
        )
        flat_imports = [i[0] or i[1] for i in internal_imports if i[0] or i[1]]

        module_data = {
            "name": py_file.stem,
            "internal_imports": len(flat_imports),
            "imports": flat_imports
        }

        import_graph[py_file.stem] = set(flat_imports)
        modules.append(module_data)

    # Check for circular dependencies (simplified)
    for module, imports in import_graph.items():
        for imp in imports:
            if imp in import_graph and module in import_graph.get(imp, set()):
                issues.append({
                    "type": "potential_circular",
                    "modules": [module, imp],
                    "severity": "medium"
                })

    # Find most imported modules (candidates for lazy loading)
    import_counts = {}
    for module, imports in import_graph.items():
        for imp in imports:
            import_counts[imp] = import_counts.get(imp, 0) + 1

    hotspots = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "modules": modules[:20],
        "total_modules": len(modules),
        "import_hotspots": [{"module": m, "import_count": c} for m, c in hotspots],
        "issues": issues
    }


def calculate_loading_score(
    tier_dist: Dict,
    startup: Dict,
    hooks: Dict,
    imports: Dict
) -> float:
    """Calculate overall loading efficiency score."""
    score = 100

    # Deduct for tier issues
    for issue in tier_dist.get("issues", []):
        if issue["severity"] == "critical":
            score -= 15
        elif issue["severity"] == "medium":
            score -= 7

    # Deduct for startup issues
    for issue in startup.get("issues", []):
        score -= 5

    # Deduct for hook issues
    for issue in hooks.get("issues", []):
        if issue["severity"] == "medium":
            score -= 3
        else:
            score -= 1

    # Deduct for import issues
    for issue in imports.get("issues", []):
        score -= 5

    # Bonus for good lazy loading ratio
    if tier_dist.get("lazy_load_ratio", 0) > 60:
        score += 5

    return max(0, min(100, score))


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
    tier_distribution = analyze_tier_distribution(project_dir)
    startup = analyze_startup_files(project_dir)
    hooks = analyze_hook_efficiency(project_dir)
    imports = analyze_import_patterns(project_dir)

    # Calculate score
    loading_score = calculate_loading_score(tier_distribution, startup, hooks, imports)

    # Determine status
    if loading_score >= 90:
        status = "excellent"
    elif loading_score >= 70:
        status = "good"
    elif loading_score >= 50:
        status = "needs_optimization"
    else:
        status = "critical"

    report = {
        "assessment": "loading-analysis",
        "project_dir": str(project_dir),
        "loading_score": loading_score,
        "status": status,
        "tier_distribution": tier_distribution,
        "startup_analysis": startup,
        "hook_efficiency": hooks,
        "import_patterns": imports,
        "all_issues": (
            tier_distribution.get("issues", []) +
            startup.get("issues", []) +
            hooks.get("issues", []) +
            imports.get("issues", [])
        )
    }

    print(json.dumps(report, indent=2))
    return 0 if loading_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
