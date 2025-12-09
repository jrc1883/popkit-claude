#!/usr/bin/env python3
"""
Documentation Sync Utility
Gathers counts from source-of-truth files and compares to CLAUDE.md.

Part of PopKit plugin - Issue #84 (Documentation Automation Epic #81)

Usage:
    python doc_sync.py           # Check mode (default)
    python doc_sync.py --fix     # Fix drift
    python doc_sync.py --json    # Output as JSON
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class DocSyncChecker:
    """Checks documentation synchronization with source-of-truth files."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.drift_issues: List[Dict[str, Any]] = []

    def get_plugin_version(self) -> Optional[str]:
        """Get version from plugin.json."""
        plugin_file = self.project_root / ".claude-plugin" / "plugin.json"
        if plugin_file.exists():
            try:
                with open(plugin_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("version")
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def get_marketplace_version(self) -> Optional[str]:
        """Get version from marketplace.json."""
        marketplace_file = self.project_root / ".claude-plugin" / "marketplace.json"
        if marketplace_file.exists():
            try:
                with open(marketplace_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Version can be at root level or nested in plugins[0]
                    if "version" in data:
                        return data["version"]
                    # Check nested structure
                    plugins = data.get("plugins", [])
                    if plugins and "version" in plugins[0]:
                        return plugins[0]["version"]
            except (json.JSONDecodeError, IOError, IndexError, KeyError):
                pass
        return None

    def get_agent_counts(self) -> Dict[str, int]:
        """Get agent counts from config.json."""
        config_file = self.project_root / "agents" / "config.json"
        counts = {"tier1": 0, "tier2": 0, "feature": 0, "total": 0}

        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = json.load(f)
                    tiers = data.get("tiers", {})
                    counts["tier1"] = len(tiers.get("tier-1-always-active", {}).get("agents", []))
                    counts["tier2"] = len(tiers.get("tier-2-on-demand", {}).get("agents", []))
                    counts["feature"] = len(tiers.get("feature-workflow", {}).get("agents", []))
                    counts["total"] = counts["tier1"] + counts["tier2"] + counts["feature"]
            except (json.JSONDecodeError, IOError):
                pass

        return counts

    def get_hook_count(self) -> int:
        """Count hooks in hooks.json."""
        hooks_file = self.project_root / "hooks" / "hooks.json"
        if hooks_file.exists():
            try:
                with open(hooks_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data.get("hooks", []))
            except (json.JSONDecodeError, IOError):
                pass
        return 0

    def get_skill_count(self) -> int:
        """Count skills (directories with SKILL.md)."""
        skills_dir = self.project_root / "skills"
        if not skills_dir.exists():
            return 0

        count = 0
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    count += 1
        return count

    def get_command_counts(self) -> Dict[str, int]:
        """Count commands (total, active, deprecated)."""
        commands_dir = self.project_root / "commands"
        if not commands_dir.exists():
            return {"total": 0, "active": 0, "deprecated": 0}

        total = 0
        deprecated = 0

        for cmd_file in commands_dir.glob("*.md"):
            total += 1
            try:
                content = cmd_file.read_text(encoding="utf-8")
                if "deprecated" in content.lower() or "DEPRECATED" in content:
                    deprecated += 1
            except IOError:
                pass

        return {
            "total": total,
            "active": total - deprecated,
            "deprecated": deprecated
        }

    def get_utils_count(self) -> int:
        """Count utility modules in hooks/utils/."""
        utils_dir = self.project_root / "hooks" / "utils"
        if not utils_dir.exists():
            return 0

        return len(list(utils_dir.glob("*.py")))

    def gather_source_counts(self) -> Dict[str, Any]:
        """Gather all counts from source-of-truth files."""
        agent_counts = self.get_agent_counts()
        command_counts = self.get_command_counts()

        return {
            "version": {
                "plugin": self.get_plugin_version(),
                "marketplace": self.get_marketplace_version()
            },
            "agents": agent_counts,
            "hooks": self.get_hook_count(),
            "skills": self.get_skill_count(),
            "commands": command_counts,
            "utils": self.get_utils_count()
        }

    def parse_claude_md(self) -> Dict[str, Any]:
        """Parse CLAUDE.md for documented counts."""
        claude_md = self.project_root / "CLAUDE.md"
        if not claude_md.exists():
            return {}

        try:
            content = claude_md.read_text(encoding="utf-8")
        except IOError:
            return {}

        documented = {}

        # Parse TIER-COUNTS section
        tier_match = re.search(
            r'<!-- AUTO-GEN:TIER-COUNTS START -->(.*?)<!-- AUTO-GEN:TIER-COUNTS END -->',
            content, re.DOTALL
        )
        if tier_match:
            section = tier_match.group(1)
            tier1 = re.search(r'(\d+)\s+core agents', section)
            tier2 = re.search(r'(\d+)\s+specialized agents', section)
            feature = re.search(r'(\d+)\s+agents for 7-phase', section)

            documented["tier1"] = int(tier1.group(1)) if tier1 else None
            documented["tier2"] = int(tier2.group(1)) if tier2 else None
            documented["feature"] = int(feature.group(1)) if feature else None

        # Parse REPO-STRUCTURE section
        repo_match = re.search(
            r'<!-- AUTO-GEN:REPO-STRUCTURE START -->(.*?)<!-- AUTO-GEN:REPO-STRUCTURE END -->',
            content, re.DOTALL
        )
        if repo_match:
            section = repo_match.group(1)

            # Extract counts from repo structure
            skills = re.search(r'skills/\s+(\d+)\s+reusable skills', section)
            commands = re.search(r'commands/\s+(\d+)\s+slash commands', section)
            hooks = re.search(r'hooks/\s+(\d+)\s+Python hooks', section)
            utils = re.search(r'utils/\s+(\d+)\s+utility modules', section)

            documented["skills"] = int(skills.group(1)) if skills else None
            documented["commands_total"] = int(commands.group(1)) if commands else None
            documented["hooks"] = int(hooks.group(1)) if hooks else None
            documented["utils"] = int(utils.group(1)) if utils else None

            # Parse deprecated count
            deprecated = re.search(r'(\d+)\s+active,\s+(\d+)\s+deprecated', section)
            if deprecated:
                documented["commands_active"] = int(deprecated.group(1))
                documented["commands_deprecated"] = int(deprecated.group(2))

        return documented

    def compare_counts(self) -> List[Dict[str, Any]]:
        """Compare source counts to documented counts."""
        source = self.gather_source_counts()
        documented = self.parse_claude_md()
        drift = []

        # Version sync
        if source["version"]["plugin"] and source["version"]["marketplace"]:
            if source["version"]["plugin"] != source["version"]["marketplace"]:
                drift.append({
                    "type": "version_mismatch",
                    "field": "version",
                    "source": f"plugin.json={source['version']['plugin']}",
                    "documented": f"marketplace.json={source['version']['marketplace']}",
                    "severity": "high"
                })

        # Agent counts
        if documented.get("tier1") is not None and documented["tier1"] != source["agents"]["tier1"]:
            drift.append({
                "type": "count_mismatch",
                "field": "tier1_agents",
                "source": source["agents"]["tier1"],
                "documented": documented["tier1"],
                "severity": "medium"
            })

        if documented.get("tier2") is not None and documented["tier2"] != source["agents"]["tier2"]:
            drift.append({
                "type": "count_mismatch",
                "field": "tier2_agents",
                "source": source["agents"]["tier2"],
                "documented": documented["tier2"],
                "severity": "medium"
            })

        if documented.get("feature") is not None and documented["feature"] != source["agents"]["feature"]:
            drift.append({
                "type": "count_mismatch",
                "field": "feature_agents",
                "source": source["agents"]["feature"],
                "documented": documented["feature"],
                "severity": "medium"
            })

        # Component counts
        if documented.get("hooks") is not None and documented["hooks"] != source["hooks"]:
            drift.append({
                "type": "count_mismatch",
                "field": "hooks",
                "source": source["hooks"],
                "documented": documented["hooks"],
                "severity": "medium"
            })

        if documented.get("skills") is not None and documented["skills"] != source["skills"]:
            drift.append({
                "type": "count_mismatch",
                "field": "skills",
                "source": source["skills"],
                "documented": documented["skills"],
                "severity": "medium"
            })

        if documented.get("commands_total") is not None and documented["commands_total"] != source["commands"]["total"]:
            drift.append({
                "type": "count_mismatch",
                "field": "commands",
                "source": source["commands"]["total"],
                "documented": documented["commands_total"],
                "severity": "medium"
            })

        if documented.get("utils") is not None and documented["utils"] != source["utils"]:
            drift.append({
                "type": "count_mismatch",
                "field": "utils",
                "source": source["utils"],
                "documented": documented["utils"],
                "severity": "low"
            })

        self.drift_issues = drift
        return drift

    def generate_report(self, verbose: bool = False) -> str:
        """Generate a human-readable sync report."""
        source = self.gather_source_counts()
        drift = self.compare_counts()

        lines = ["Documentation Sync Report", "=" * 25, ""]

        # Version
        lines.append("Version Sync:")
        plugin_v = source["version"]["plugin"] or "unknown"
        market_v = source["version"]["marketplace"] or "unknown"
        match = "✓" if plugin_v == market_v else "✗ MISMATCH"
        lines.append(f"  plugin.json:      {plugin_v}")
        lines.append(f"  marketplace.json: {market_v} {match}")
        lines.append("")

        # Agents
        lines.append("Agent Counts:")
        a = source["agents"]
        lines.append(f"  Tier 1: {a['tier1']}, Tier 2: {a['tier2']}, Feature: {a['feature']}")
        lines.append(f"  Total: {a['total']}")
        lines.append("")

        # Components
        lines.append("Component Counts:")
        lines.append(f"  Skills: {source['skills']}")
        c = source["commands"]
        lines.append(f"  Commands: {c['total']} ({c['active']} active, {c['deprecated']} deprecated)")
        lines.append(f"  Hooks: {source['hooks']}")
        lines.append(f"  Utils: {source['utils']}")
        lines.append("")

        # Drift summary
        if drift:
            lines.append(f"DRIFT DETECTED: {len(drift)} issue(s)")
            for d in drift:
                lines.append(f"  - {d['field']}: source={d['source']}, docs={d['documented']}")
        else:
            lines.append("Status: All synchronized ✓")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Output full analysis as JSON."""
        source = self.gather_source_counts()
        drift = self.compare_counts()

        return json.dumps({
            "source_counts": source,
            "drift_issues": drift,
            "synchronized": len(drift) == 0
        }, indent=2)


def main():
    """CLI entry point."""
    import argparse
    import io

    # Handle Windows encoding issues
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="Check documentation synchronization")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    checker = DocSyncChecker()

    if args.json:
        print(checker.to_json())
    else:
        print(checker.generate_report(verbose=args.verbose))

    # Exit with non-zero if drift detected
    if checker.drift_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
