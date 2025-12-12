#!/usr/bin/env python3
"""
Validate Agent Routing Coverage

Checks routing configuration for coverage, conflicts, and missing patterns.

Usage:
    python validate_routing.py [plugin_dir]

Output:
    JSON object with findings and score
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any


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


def get_all_agents(plugin_dir: Path) -> Dict[str, Set[str]]:
    """Get all agents organized by tier."""
    agents = {
        "tier-1": set(),
        "tier-2": set(),
        "feature-workflow": set(),
        "assessors": set()
    }

    agents_dir = plugin_dir / "agents"
    if not agents_dir.exists():
        return agents

    for tier_dir in agents_dir.iterdir():
        if tier_dir.is_dir() and tier_dir.name != "_templates":
            tier_key = tier_dir.name
            if tier_key not in agents:
                tier_key = "other"
                agents[tier_key] = set()

            for agent_dir in tier_dir.iterdir():
                if agent_dir.is_dir() and (agent_dir / "AGENT.md").exists():
                    agents[tier_key].add(agent_dir.name)

    return agents


def load_routing_config(plugin_dir: Path) -> tuple[Dict, str]:
    """Load agents/config.json."""
    config_path = plugin_dir / "agents" / "config.json"
    if not config_path.exists():
        return None, "config.json not found"

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def check_keyword_routing(config: Dict, all_agents: Dict) -> List[Dict]:
    """Check keyword routing coverage."""
    findings = []

    routing = config.get("routing", {})
    keywords = routing.get("keywords", {})

    # Get all tier-1 agents
    tier1_agents = all_agents.get("tier-1", set()) | all_agents.get("tier-1-always-active", set())

    # Find agents with keywords
    agents_with_keywords = set()
    for keyword, agent_list in keywords.items():
        for agent in agent_list:
            agents_with_keywords.add(agent)

    # Check tier-1 coverage
    tier1_missing = tier1_agents - agents_with_keywords

    if tier1_missing:
        coverage = ((len(tier1_agents) - len(tier1_missing)) / max(len(tier1_agents), 1)) * 100
        findings.append({
            "id": "AR-001",
            "check": "Tier-1 agents have keywords",
            "status": "WARN" if len(tier1_missing) <= 2 else "FAIL",
            "severity": "high",
            "message": f"Missing keywords for: {sorted(tier1_missing)}",
            "coverage": round(coverage, 1),
            "deduction": min(len(tier1_missing) * 2, 10)
        })
    else:
        findings.append({
            "id": "AR-001",
            "check": "Tier-1 agents have keywords",
            "status": "PASS",
            "severity": "high",
            "message": f"All {len(tier1_agents)} tier-1 agents have keywords",
            "coverage": 100,
            "deduction": 0
        })

    # Check for duplicate keywords
    keyword_agents = {}
    for keyword, agents in keywords.items():
        if len(agents) > 1:
            keyword_agents[keyword] = agents

    if keyword_agents:
        findings.append({
            "id": "AR-002",
            "check": "No duplicate keyword mappings",
            "status": "INFO",
            "severity": "high",
            "message": f"Keywords with multiple agents: {list(keyword_agents.keys())[:5]}",
            "deduction": 0  # Not necessarily wrong, just notable
        })
    else:
        findings.append({
            "id": "AR-002",
            "check": "No duplicate keyword mappings",
            "status": "PASS",
            "severity": "high",
            "message": "Each keyword maps to single agent",
            "deduction": 0
        })

    return findings


def check_file_patterns(config: Dict) -> List[Dict]:
    """Check file pattern routing."""
    findings = []

    routing = config.get("routing", {})
    patterns = routing.get("filePatterns", {})

    # Common patterns that should exist
    recommended_patterns = {
        "*.test.*": "test-writer-fixer",
        "*.spec.*": "test-writer-fixer",
        "*.sql": "query-optimizer",
        "*.md": "documentation-maintainer",
        "*.yaml": "devops-automator",
        "*.yml": "devops-automator",
        "Dockerfile*": "devops-automator",
        ".env*": "security-auditor"
    }

    # Check which patterns exist
    existing_patterns = set(patterns.keys())
    missing_patterns = []

    for pattern, expected_agent in recommended_patterns.items():
        # Check if similar pattern exists
        pattern_base = pattern.replace("*", "").replace(".", "")
        found = any(pattern_base in p for p in existing_patterns)
        if not found:
            missing_patterns.append(pattern)

    if missing_patterns:
        coverage = ((len(recommended_patterns) - len(missing_patterns)) / len(recommended_patterns)) * 100
        findings.append({
            "id": "AR-007",
            "check": "Common file types covered",
            "status": "WARN" if len(missing_patterns) <= 3 else "FAIL",
            "severity": "medium",
            "message": f"Missing patterns: {missing_patterns[:5]}",
            "coverage": round(coverage, 1),
            "deduction": min(len(missing_patterns) * 2, 10)
        })
    else:
        findings.append({
            "id": "AR-007",
            "check": "Common file types covered",
            "status": "PASS",
            "severity": "medium",
            "message": f"All {len(recommended_patterns)} common patterns covered",
            "coverage": 100,
            "deduction": 0
        })

    return findings


def check_error_patterns(config: Dict) -> List[Dict]:
    """Check error pattern routing."""
    findings = []

    routing = config.get("routing", {})
    patterns = routing.get("errorPatterns", {})

    # Common errors that should be routed
    recommended_errors = {
        "TypeError": "bug-whisperer",
        "SyntaxError": "code-reviewer",
        "SecurityError": "security-auditor",
        "ImportError": "migration-specialist",
        "ConnectionError": "devops-automator",
        "MemoryError": "performance-optimizer"
    }

    existing_errors = set(patterns.keys())
    missing_errors = set(recommended_errors.keys()) - existing_errors

    if missing_errors:
        coverage = ((len(recommended_errors) - len(missing_errors)) / len(recommended_errors)) * 100
        findings.append({
            "id": "AR-008",
            "check": "Common errors covered",
            "status": "WARN" if len(missing_errors) <= 2 else "FAIL",
            "severity": "medium",
            "message": f"Missing error patterns: {sorted(missing_errors)}",
            "coverage": round(coverage, 1),
            "deduction": min(len(missing_errors) * 2, 10)
        })
    else:
        findings.append({
            "id": "AR-008",
            "check": "Common errors covered",
            "status": "PASS",
            "severity": "medium",
            "message": f"All {len(recommended_errors)} common errors covered",
            "coverage": 100,
            "deduction": 0
        })

    return findings


def check_agent_references(config: Dict, all_agents: Dict) -> List[Dict]:
    """Check that referenced agents exist."""
    findings = []

    # Flatten all agent names
    all_agent_names = set()
    for tier_agents in all_agents.values():
        all_agent_names.update(tier_agents)

    # Get all referenced agents
    referenced_agents = set()
    routing = config.get("routing", {})

    for keyword, agents in routing.get("keywords", {}).items():
        referenced_agents.update(agents)

    for pattern, agents in routing.get("filePatterns", {}).items():
        referenced_agents.update(agents)

    for error, agents in routing.get("errorPatterns", {}).items():
        referenced_agents.update(agents)

    # Find missing agents
    missing_agents = referenced_agents - all_agent_names

    if missing_agents:
        findings.append({
            "id": "AR-005",
            "check": "Referenced agents exist",
            "status": "FAIL",
            "severity": "critical",
            "message": f"Missing agents: {sorted(missing_agents)}",
            "deduction": len(missing_agents) * 10
        })
    else:
        findings.append({
            "id": "AR-005",
            "check": "Referenced agents exist",
            "status": "PASS",
            "severity": "critical",
            "message": f"All {len(referenced_agents)} referenced agents exist",
            "deduction": 0
        })

    return findings


def main():
    # Get plugin directory
    if len(sys.argv) > 1:
        plugin_dir = Path(sys.argv[1])
    else:
        plugin_dir = find_plugin_root()

    # Load configuration
    config, error = load_routing_config(plugin_dir)

    if error:
        result = {
            "category": "agent-routing",
            "plugin_dir": str(plugin_dir),
            "score": 0,
            "max_score": 100,
            "summary": {
                "error": error
            },
            "findings": [{
                "id": "AR-000",
                "check": "Config loadable",
                "status": "FAIL",
                "severity": "critical",
                "message": error,
                "deduction": 50
            }]
        }
        print(json.dumps(result, indent=2))
        return 1

    # Get all agents
    all_agents = get_all_agents(plugin_dir)

    # Run all checks
    all_findings = []
    all_findings.extend(check_keyword_routing(config, all_agents))
    all_findings.extend(check_file_patterns(config))
    all_findings.extend(check_error_patterns(config))
    all_findings.extend(check_agent_references(config, all_agents))

    # Calculate score
    total_deduction = sum(f.get("deduction", 0) for f in all_findings)
    score = max(0, 100 - total_deduction)

    # Summary
    passes = len([f for f in all_findings if f["status"] == "PASS"])
    fails = len([f for f in all_findings if f["status"] == "FAIL"])
    warns = len([f for f in all_findings if f["status"] == "WARN"])

    # Calculate average coverage
    coverage_checks = [f for f in all_findings if "coverage" in f]
    avg_coverage = sum(f["coverage"] for f in coverage_checks) / max(len(coverage_checks), 1)

    result = {
        "category": "agent-routing",
        "plugin_dir": str(plugin_dir),
        "score": score,
        "max_score": 100,
        "summary": {
            "passes": passes,
            "fails": fails,
            "warnings": warns,
            "total_deduction": total_deduction,
            "average_coverage": round(avg_coverage, 1)
        },
        "findings": all_findings
    }

    print(json.dumps(result, indent=2))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
