#!/usr/bin/env python3
"""
Documentation Sync Hook
Detects changes to documentation-impacting files and suggests synchronization.

Part of PopKit plugin - Issue #82 (Documentation Automation Epic #81)

Monitors:
- plugin.json version changes -> marketplace.json, CLAUDE.md
- agents/config.json changes -> CLAUDE.md agent counts
- hooks/hooks.json changes -> CLAUDE.md hook counts
- commands/*.md changes -> CLAUDE.md command counts
- skills/*/SKILL.md changes -> CLAUDE.md skill counts

Output: Suggestions for documentation updates (non-blocking)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


# Files that impact documentation
DOC_IMPACTING_PATTERNS = {
    "plugin.json": {
        "description": "Plugin version",
        "targets": ["marketplace.json", "CLAUDE.md", "README.md"],
        "check": "version_sync"
    },
    "marketplace.json": {
        "description": "Marketplace version",
        "targets": ["plugin.json"],
        "check": "version_sync"
    },
    "agents/config.json": {
        "description": "Agent configuration",
        "targets": ["CLAUDE.md"],
        "check": "agent_counts"
    },
    "hooks/hooks.json": {
        "description": "Hook configuration",
        "targets": ["CLAUDE.md"],
        "check": "hook_counts"
    }
}

# Directory patterns (any file in these dirs)
DOC_IMPACTING_DIRS = {
    "commands/": {
        "extension": ".md",
        "description": "Command definitions",
        "targets": ["CLAUDE.md"],
        "check": "command_counts"
    },
    "skills/": {
        "extension": "SKILL.md",
        "description": "Skill definitions",
        "targets": ["CLAUDE.md"],
        "check": "skill_counts"
    },
    "agents/tier-": {
        "extension": "AGENT.md",
        "description": "Agent definitions",
        "targets": ["CLAUDE.md"],
        "check": "agent_counts"
    }
}


class DocSyncChecker:
    """Checks for documentation synchronization needs."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()

    def get_plugin_version(self) -> Optional[str]:
        """Get version from plugin.json."""
        plugin_file = self.project_root / ".claude-plugin" / "plugin.json"
        if plugin_file.exists():
            try:
                with open(plugin_file) as f:
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
                with open(marketplace_file) as f:
                    data = json.load(f)
                    return data.get("version")
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def get_hook_count(self) -> int:
        """Count hooks in hooks.json."""
        hooks_file = self.project_root / "hooks" / "hooks.json"
        if hooks_file.exists():
            try:
                with open(hooks_file) as f:
                    data = json.load(f)
                    return len(data.get("hooks", []))
            except (json.JSONDecodeError, IOError):
                pass
        return 0

    def get_command_count(self) -> Dict[str, int]:
        """Count commands (active vs deprecated)."""
        commands_dir = self.project_root / "commands"
        if not commands_dir.exists():
            return {"active": 0, "deprecated": 0}

        active = 0
        deprecated = 0

        for cmd_file in commands_dir.glob("*.md"):
            try:
                content = cmd_file.read_text()
                if "deprecated: true" in content.lower() or "DEPRECATED" in content:
                    deprecated += 1
                else:
                    active += 1
            except IOError:
                pass

        return {"active": active, "deprecated": deprecated}

    def get_skill_count(self) -> int:
        """Count skills with SKILL.md files."""
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

    def get_agent_counts(self) -> Dict[str, int]:
        """Count agents by tier."""
        agents_dir = self.project_root / "agents"
        config_file = agents_dir / "config.json"

        counts = {"tier1": 0, "tier2": 0, "feature_workflow": 0, "total": 0}

        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    tiers = data.get("tiers", {})
                    counts["tier1"] = len(tiers.get("tier-1-always-active", []))
                    counts["tier2"] = len(tiers.get("tier-2-on-demand", []))
                    counts["feature_workflow"] = len(tiers.get("feature-workflow", []))
                    counts["total"] = counts["tier1"] + counts["tier2"] + counts["feature_workflow"]
            except (json.JSONDecodeError, IOError):
                pass

        return counts

    def check_version_sync(self) -> List[Dict[str, Any]]:
        """Check if versions are synchronized."""
        issues = []

        plugin_version = self.get_plugin_version()
        marketplace_version = self.get_marketplace_version()

        if plugin_version and marketplace_version:
            if plugin_version != marketplace_version:
                issues.append({
                    "type": "version_mismatch",
                    "severity": "high",
                    "message": f"Version mismatch: plugin.json={plugin_version}, marketplace.json={marketplace_version}",
                    "suggestion": f"Update marketplace.json version to {plugin_version}"
                })

        return issues

    def check_file_impact(self, file_path: str) -> Dict[str, Any]:
        """Check if a file change impacts documentation."""
        result = {
            "impacts_docs": False,
            "description": None,
            "targets": [],
            "check_type": None,
            "suggestions": []
        }

        # Normalize path
        file_path = file_path.replace("\\", "/")

        # Check direct file patterns
        for pattern, info in DOC_IMPACTING_PATTERNS.items():
            if pattern in file_path:
                result["impacts_docs"] = True
                result["description"] = info["description"]
                result["targets"] = info["targets"]
                result["check_type"] = info["check"]
                break

        # Check directory patterns
        if not result["impacts_docs"]:
            for dir_pattern, info in DOC_IMPACTING_DIRS.items():
                if dir_pattern in file_path and file_path.endswith(info["extension"]):
                    result["impacts_docs"] = True
                    result["description"] = info["description"]
                    result["targets"] = info["targets"]
                    result["check_type"] = info["check"]
                    break

        # Generate specific suggestions based on check type
        if result["impacts_docs"]:
            if result["check_type"] == "version_sync":
                version_issues = self.check_version_sync()
                for issue in version_issues:
                    result["suggestions"].append(issue["suggestion"])
                if not version_issues:
                    result["suggestions"].append(
                        "Version changed - verify CLAUDE.md version history is updated"
                    )

            elif result["check_type"] == "hook_counts":
                hook_count = self.get_hook_count()
                result["suggestions"].append(
                    f"Hook configuration changed - verify CLAUDE.md hook count ({hook_count} hooks)"
                )

            elif result["check_type"] == "command_counts":
                cmd_counts = self.get_command_count()
                result["suggestions"].append(
                    f"Command changed - verify CLAUDE.md command count ({cmd_counts['active']} active, {cmd_counts['deprecated']} deprecated)"
                )

            elif result["check_type"] == "skill_counts":
                skill_count = self.get_skill_count()
                result["suggestions"].append(
                    f"Skill changed - verify CLAUDE.md skill count ({skill_count} skills)"
                )

            elif result["check_type"] == "agent_counts":
                agent_counts = self.get_agent_counts()
                result["suggestions"].append(
                    f"Agent config changed - verify CLAUDE.md agent counts (Tier1: {agent_counts['tier1']}, Tier2: {agent_counts['tier2']})"
                )

        return result


def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_data = json.loads(sys.stdin.read())

        # Extract file path from tool input
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # If no file path, check for content that might indicate file
        if not file_path:
            file_path = tool_input.get("path", "")

        checker = DocSyncChecker()
        result = checker.check_file_impact(file_path)

        response = {
            "status": "success",
            "file_path": file_path,
            "impacts_docs": result["impacts_docs"],
            "description": result["description"],
            "targets": result["targets"],
            "suggestions": result["suggestions"]
        }

        # Output suggestions to stderr for visibility (non-blocking)
        if result["impacts_docs"] and result["suggestions"]:
            print(f"\n[doc-sync] {result['description']} changed", file=sys.stderr)
            for suggestion in result["suggestions"]:
                print(f"  -> {suggestion}", file=sys.stderr)
            print(f"  Run: /popkit:plugin docs --check", file=sys.stderr)

        # Output JSON response
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors


if __name__ == "__main__":
    main()
