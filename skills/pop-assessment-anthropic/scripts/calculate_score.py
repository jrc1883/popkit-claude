#!/usr/bin/env python3
"""
Calculate Overall Assessment Score

Combines results from all validation scripts to produce final score.

Usage:
    python calculate_score.py [plugin_dir]

    Or pipe results from other scripts:
    cat structure.json hooks.json routing.json | python calculate_score.py --combine

Output:
    JSON object with overall score and breakdown
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def find_plugin_root(start_path: Path = None) -> Path:
    """Find the plugin root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / ".claude-plugin" / "plugin.json").exists():
            return current
        if (current / "packages" / "plugin" / ".claude-plugin" / "plugin.json").exists():
            return current / "packages" / "plugin"
        current = current.parent

    return start_path


def run_validation_script(script_name: str, plugin_dir: Path) -> dict:
    """Run a validation script and return its result."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        return {
            "category": script_name.replace("validate_", "").replace(".py", ""),
            "score": 0,
            "error": f"Script not found: {script_path}"
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {
            "category": script_name.replace("validate_", "").replace(".py", ""),
            "score": 0,
            "error": "Script timeout"
        }
    except json.JSONDecodeError:
        return {
            "category": script_name.replace("validate_", "").replace(".py", ""),
            "score": 0,
            "error": "Invalid JSON output"
        }
    except Exception as e:
        return {
            "category": script_name.replace("validate_", "").replace(".py", ""),
            "score": 0,
            "error": str(e)
        }


def get_version(plugin_dir: Path) -> str:
    """Get plugin version from plugin.json."""
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            with open(plugin_json, 'r') as f:
                data = json.load(f)
                return data.get("version", "unknown")
        except:
            pass
    return "unknown"


def calculate_weighted_score(results: list) -> dict:
    """Calculate weighted overall score."""
    weights = {
        "plugin-structure": 25,
        "hook-protocol": 30,
        "agent-routing": 25,
        "progressive-disclosure": 20
    }

    total_weight = 0
    weighted_score = 0
    category_scores = {}

    for result in results:
        category = result.get("category", "unknown")
        score = result.get("score", 0)
        weight = weights.get(category, 10)

        category_scores[category] = {
            "score": score,
            "weight": weight,
            "weighted": round(score * weight / 100, 2)
        }

        total_weight += weight
        weighted_score += score * weight

    overall = round(weighted_score / max(total_weight, 1), 1)

    return {
        "overall": overall,
        "categories": category_scores,
        "total_weight": total_weight
    }


def get_status_label(score: float) -> str:
    """Get status label for score."""
    if score >= 90:
        return "EXCELLENT"
    elif score >= 80:
        return "GOOD"
    elif score >= 70:
        return "ACCEPTABLE"
    elif score >= 60:
        return "NEEDS WORK"
    else:
        return "FAILING"


def collect_all_findings(results: list) -> dict:
    """Collect and categorize all findings."""
    all_findings = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
        "info": []
    }

    for result in results:
        category = result.get("category", "unknown")
        findings = result.get("findings", [])

        for finding in findings:
            if isinstance(finding, dict):
                severity = finding.get("severity", "info")
                if severity in all_findings:
                    finding["category"] = category
                    all_findings[severity].append(finding)

                # Also check nested checks
                checks = finding.get("checks", [])
                for check in checks:
                    if isinstance(check, dict) and check.get("status") in ("FAIL", "WARN"):
                        check_severity = check.get("severity", "info")
                        if check_severity in all_findings:
                            check["category"] = category
                            check["file"] = finding.get("file", "")
                            all_findings[check_severity].append(check)

    return all_findings


def main():
    # Handle --combine mode (read from stdin)
    if "--combine" in sys.argv:
        try:
            results = []
            for line in sys.stdin:
                if line.strip():
                    results.append(json.loads(line))
            # Continue with scoring below
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return 1
    else:
        # Get plugin directory
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            plugin_dir = Path(sys.argv[1])
        else:
            plugin_dir = find_plugin_root()

        # Run all validation scripts
        scripts = [
            "validate_plugin_structure.py",
            "validate_hooks.py",
            "validate_routing.py"
        ]

        results = []
        for script in scripts:
            result = run_validation_script(script, plugin_dir)
            results.append(result)

    # Calculate scores
    scoring = calculate_weighted_score(results)
    overall = scoring["overall"]
    status = get_status_label(overall)

    # Collect findings
    all_findings = collect_all_findings(results)

    # Get version
    version = get_version(plugin_dir) if 'plugin_dir' in dir() else "unknown"

    # Build final report
    report = {
        "assessment": "anthropic-engineer",
        "version": version,
        "date": datetime.now().isoformat(),
        "overall_score": overall,
        "status": status,
        "scoring": scoring,
        "summary": {
            "critical_issues": len(all_findings["critical"]),
            "high_issues": len(all_findings["high"]),
            "medium_issues": len(all_findings["medium"]),
            "low_issues": len(all_findings["low"])
        },
        "category_results": results,
        "findings_by_severity": all_findings,
        "recommendations": []
    }

    # Add recommendations based on findings
    if all_findings["critical"]:
        report["recommendations"].append({
            "priority": "CRITICAL",
            "message": f"Fix {len(all_findings['critical'])} critical issues before release"
        })

    if all_findings["high"]:
        report["recommendations"].append({
            "priority": "HIGH",
            "message": f"Address {len(all_findings['high'])} high priority issues"
        })

    # Print report
    print(json.dumps(report, indent=2))

    # Return exit code based on critical issues
    return 1 if all_findings["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
