#!/usr/bin/env python3
"""
Calculate Overall Security Risk Score

Combines results from secret scanning and injection detection to produce
final security risk assessment.

Usage:
    python calculate_risk.py [plugin_dir]

    Or pipe results from other scripts:
    cat secrets.json injection.json | python calculate_risk.py --combine

Output:
    JSON object with overall risk score and breakdown
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


def run_scan_script(script_name: str, plugin_dir: Path) -> dict:
    """Run a scan script and return its result."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        return {
            "category": script_name.replace("scan_", "").replace(".py", ""),
            "score": 100,
            "error": f"Script not found: {script_path}",
            "findings": []
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {
            "category": script_name.replace("scan_", "").replace(".py", ""),
            "score": 100,
            "error": "Script timeout",
            "findings": []
        }
    except json.JSONDecodeError:
        return {
            "category": script_name.replace("scan_", "").replace(".py", ""),
            "score": 100,
            "error": "Invalid JSON output",
            "findings": []
        }
    except Exception as e:
        return {
            "category": script_name.replace("scan_", "").replace(".py", ""),
            "score": 100,
            "error": str(e),
            "findings": []
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


def calculate_weighted_risk(results: list) -> dict:
    """Calculate weighted risk score (inverted from compliance score)."""
    weights = {
        "secret-detection": 40,
        "injection-prevention": 40,
        "access-control": 10,
        "input-validation": 10
    }

    total_weight = 0
    weighted_score = 0
    category_scores = {}

    for result in results:
        category = result.get("category", "unknown")
        # Score from scan is compliance (100 = no issues)
        # We want risk score (100 = maximum risk)
        compliance_score = result.get("score", 100)
        risk_contribution = 100 - compliance_score

        weight = weights.get(category, 10)

        category_scores[category] = {
            "compliance_score": compliance_score,
            "risk_contribution": risk_contribution,
            "weight": weight,
            "weighted_risk": round(risk_contribution * weight / 100, 2),
            "findings_count": len(result.get("findings", []))
        }

        total_weight += weight
        weighted_score += risk_contribution * weight

    # Risk score: 0 = no risk, 100 = maximum risk
    overall_risk = round(weighted_score / max(total_weight, 1), 1)

    return {
        "risk_score": overall_risk,
        "compliance_score": round(100 - overall_risk, 1),
        "categories": category_scores,
        "total_weight": total_weight
    }


def get_risk_label(risk_score: float) -> str:
    """Get risk label for score."""
    if risk_score >= 75:
        return "CRITICAL"
    elif risk_score >= 50:
        return "HIGH"
    elif risk_score >= 25:
        return "MEDIUM"
    elif risk_score >= 10:
        return "LOW"
    else:
        return "MINIMAL"


def collect_all_findings(results: list) -> dict:
    """Collect and categorize all security findings."""
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
                    finding["scan_category"] = category
                    all_findings[severity].append(finding)

    return all_findings


def generate_recommendations(findings: dict, risk_score: float) -> list:
    """Generate prioritized security recommendations."""
    recommendations = []

    if findings["critical"]:
        recommendations.append({
            "priority": "CRITICAL",
            "action": "IMMEDIATE",
            "message": f"Fix {len(findings['critical'])} critical vulnerabilities before release",
            "cwes": list(set(f.get("cwe", "unknown") for f in findings["critical"]))
        })

    if findings["high"]:
        recommendations.append({
            "priority": "HIGH",
            "action": "REQUIRED",
            "message": f"Address {len(findings['high'])} high-severity issues",
            "cwes": list(set(f.get("cwe", "unknown") for f in findings["high"]))
        })

    if findings["medium"]:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "RECOMMENDED",
            "message": f"Review {len(findings['medium'])} medium-severity findings"
        })

    if risk_score < 10:
        recommendations.append({
            "priority": "INFO",
            "action": "MAINTAIN",
            "message": "Security posture is strong. Continue regular scanning."
        })

    return recommendations


def main():
    # Handle --combine mode (read from stdin)
    if "--combine" in sys.argv:
        try:
            results = []
            for line in sys.stdin:
                if line.strip():
                    results.append(json.loads(line))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return 1
        plugin_dir = find_plugin_root()
    else:
        # Get plugin directory
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            plugin_dir = Path(sys.argv[1])
        else:
            plugin_dir = find_plugin_root()

        # Run all scan scripts
        scripts = [
            "scan_secrets.py",
            "scan_injection.py"
        ]

        results = []
        for script in scripts:
            result = run_scan_script(script, plugin_dir)
            results.append(result)

    # Calculate risk scores
    scoring = calculate_weighted_risk(results)
    risk_score = scoring["risk_score"]
    risk_label = get_risk_label(risk_score)

    # Collect all findings
    all_findings = collect_all_findings(results)

    # Generate recommendations
    recommendations = generate_recommendations(all_findings, risk_score)

    # Get version
    version = get_version(plugin_dir)

    # Build final report
    report = {
        "assessment": "security-audit",
        "version": version,
        "date": datetime.now().isoformat(),
        "risk_score": risk_score,
        "compliance_score": scoring["compliance_score"],
        "risk_level": risk_label,
        "scoring": scoring,
        "summary": {
            "critical_issues": len(all_findings["critical"]),
            "high_issues": len(all_findings["high"]),
            "medium_issues": len(all_findings["medium"]),
            "low_issues": len(all_findings["low"]),
            "total_issues": sum(len(v) for v in all_findings.values())
        },
        "category_results": results,
        "findings_by_severity": all_findings,
        "recommendations": recommendations,
        "owasp_mapping": {
            "A01:2021-Broken Access Control": len([f for f in all_findings["critical"] + all_findings["high"] if f.get("cwe") in ["CWE-22", "CWE-23"]]),
            "A02:2021-Cryptographic Failures": len([f for f in all_findings["critical"] + all_findings["high"] if f.get("cwe") in ["CWE-321", "CWE-798"]]),
            "A03:2021-Injection": len([f for f in all_findings["critical"] + all_findings["high"] if f.get("cwe") in ["CWE-78", "CWE-89", "CWE-94"]]),
            "A08:2021-Software and Data Integrity Failures": len([f for f in all_findings["critical"] + all_findings["high"] if f.get("cwe") in ["CWE-502"]])
        }
    }

    # Print report
    print(json.dumps(report, indent=2))

    # Return exit code based on critical issues
    return 1 if all_findings["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
