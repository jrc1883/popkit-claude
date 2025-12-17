#!/usr/bin/env python3
"""
Plugin Conflict Detection Utility

Detects conflicts between Claude Code plugins installed in the system.
Scans ~/.claude/plugins/ for all installed plugins and compares their
commands, skills, hooks, and agent routing for potential conflicts.

Part of the popkit plugin system.
"""

import os
import json
import re
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# Conflict severity levels
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"


def get_plugins_directory() -> str:
    """Get the Claude Code plugins directory.

    Returns:
        Path to ~/.claude/plugins/ or platform-appropriate equivalent
    """
    home = os.path.expanduser("~")
    return os.path.join(home, ".claude", "plugins")


def scan_installed_plugins(plugins_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Scan for all installed Claude Code plugins.

    Args:
        plugins_dir: Optional override for plugins directory

    Returns:
        List of plugin info dicts with name, path, manifest, etc.
    """
    if plugins_dir is None:
        plugins_dir = get_plugins_directory()

    plugins = []

    if not os.path.exists(plugins_dir):
        return plugins

    for entry in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, entry)
        if not os.path.isdir(plugin_path):
            continue

        # Look for plugin manifest
        manifest_path = os.path.join(plugin_path, ".claude-plugin", "plugin.json")
        if not os.path.exists(manifest_path):
            # Try alternate location
            manifest_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.exists(manifest_path):
                continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            plugin_info = {
                "name": manifest.get("name", entry),
                "path": plugin_path,
                "manifest": manifest,
                "commands": [],
                "skills": [],
                "hooks": [],
                "agents": []
            }

            # Scan for components
            plugin_info["commands"] = scan_plugin_commands(plugin_path)
            plugin_info["skills"] = scan_plugin_skills(plugin_path)
            plugin_info["hooks"] = scan_plugin_hooks(plugin_path)
            plugin_info["agents"] = scan_plugin_agents(plugin_path)

            plugins.append(plugin_info)

        except (json.JSONDecodeError, IOError):
            continue

    return plugins


def scan_plugin_commands(plugin_path: str) -> List[Dict[str, str]]:
    """Scan for command definitions in a plugin.

    Args:
        plugin_path: Path to plugin directory

    Returns:
        List of command info dicts with name, file, description
    """
    commands = []
    commands_dir = os.path.join(plugin_path, "commands")

    if not os.path.exists(commands_dir):
        return commands

    for cmd_file in Path(commands_dir).glob("*.md"):
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract command name from filename or frontmatter
            name = cmd_file.stem

            # Try to extract description from frontmatter
            description = ""
            if content.startswith("---"):
                match = re.search(r"description:\s*(.+?)(?:\n|$)", content)
                if match:
                    description = match.group(1).strip().strip('"\'')

            commands.append({
                "name": name,
                "file": str(cmd_file),
                "description": description
            })

        except IOError:
            continue

    return commands


def scan_plugin_skills(plugin_path: str) -> List[Dict[str, str]]:
    """Scan for skill definitions in a plugin.

    Args:
        plugin_path: Path to plugin directory

    Returns:
        List of skill info dicts with name, file, description
    """
    skills = []
    skills_dir = os.path.join(plugin_path, "skills")

    if not os.path.exists(skills_dir):
        return skills

    # Skills can be SKILL.md in subdirectories
    for skill_file in Path(skills_dir).glob("*/SKILL.md"):
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Name from directory
            name = skill_file.parent.name

            # Try to extract description from frontmatter
            description = ""
            if content.startswith("---"):
                match = re.search(r"description:\s*[\"']?(.+?)[\"']?(?:\n|$)", content)
                if match:
                    description = match.group(1).strip()[:100]  # Truncate

            skills.append({
                "name": name,
                "file": str(skill_file),
                "description": description
            })

        except IOError:
            continue

    return skills


def scan_plugin_hooks(plugin_path: str) -> List[Dict[str, Any]]:
    """Scan for hook definitions in a plugin.

    Args:
        plugin_path: Path to plugin directory

    Returns:
        List of hook info dicts with name, event, tools
    """
    hooks = []

    # Check hooks.json
    hooks_json = os.path.join(plugin_path, "hooks", "hooks.json")
    if not os.path.exists(hooks_json):
        return hooks

    try:
        with open(hooks_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        for hook in config.get("hooks", []):
            hooks.append({
                "name": hook.get("matcher", "unknown"),
                "event": hook.get("event", "unknown"),
                "tools": hook.get("tools", []),
                "file": hooks_json
            })

    except (json.JSONDecodeError, IOError):
        pass

    return hooks


def scan_plugin_agents(plugin_path: str) -> List[Dict[str, Any]]:
    """Scan for agent definitions in a plugin.

    Args:
        plugin_path: Path to plugin directory

    Returns:
        List of agent info dicts with name, keywords, file_patterns
    """
    agents = []

    # Check agents/config.json
    config_path = os.path.join(plugin_path, "agents", "config.json")
    if not os.path.exists(config_path):
        return agents

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        routing = config.get("routing", {})
        for agent_name, agent_config in routing.items():
            agents.append({
                "name": agent_name,
                "keywords": agent_config.get("keywords", []),
                "file_patterns": agent_config.get("file_patterns", []),
                "error_patterns": agent_config.get("error_patterns", [])
            })

    except (json.JSONDecodeError, IOError):
        pass

    return agents


def detect_command_conflicts(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect command name collisions between plugins.

    Args:
        plugins: List of plugin info dicts

    Returns:
        List of conflict dicts
    """
    conflicts = []
    command_map: Dict[str, List[str]] = {}  # command_name -> [plugin_names]

    for plugin in plugins:
        for cmd in plugin["commands"]:
            cmd_name = cmd["name"]
            if cmd_name not in command_map:
                command_map[cmd_name] = []
            command_map[cmd_name].append(plugin["name"])

    for cmd_name, plugin_names in command_map.items():
        if len(plugin_names) > 1:
            conflicts.append({
                "type": "command_collision",
                "severity": SEVERITY_HIGH,
                "name": cmd_name,
                "plugins": plugin_names,
                "message": f"Command '{cmd_name}' defined in multiple plugins: {', '.join(plugin_names)}"
            })

    return conflicts


def detect_skill_conflicts(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect skill name collisions between plugins.

    Args:
        plugins: List of plugin info dicts

    Returns:
        List of conflict dicts
    """
    conflicts = []
    skill_map: Dict[str, List[str]] = {}

    for plugin in plugins:
        for skill in plugin["skills"]:
            skill_name = skill["name"]
            if skill_name not in skill_map:
                skill_map[skill_name] = []
            skill_map[skill_name].append(plugin["name"])

    for skill_name, plugin_names in skill_map.items():
        if len(plugin_names) > 1:
            conflicts.append({
                "type": "skill_collision",
                "severity": SEVERITY_MEDIUM,
                "name": skill_name,
                "plugins": plugin_names,
                "message": f"Skill '{skill_name}' defined in multiple plugins: {', '.join(plugin_names)}"
            })

    return conflicts


def detect_hook_conflicts(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect hook conflicts (same event, overlapping tools).

    Args:
        plugins: List of plugin info dicts

    Returns:
        List of conflict dicts
    """
    conflicts = []

    # Group hooks by event
    event_hooks: Dict[str, List[Tuple[str, Dict]]] = {}  # event -> [(plugin_name, hook)]

    for plugin in plugins:
        for hook in plugin["hooks"]:
            event = hook["event"]
            if event not in event_hooks:
                event_hooks[event] = []
            event_hooks[event].append((plugin["name"], hook))

    # Check for tool overlaps within same event
    for event, hook_list in event_hooks.items():
        if len(hook_list) < 2:
            continue

        # Check each pair
        for i, (plugin1, hook1) in enumerate(hook_list):
            for plugin2, hook2 in hook_list[i + 1:]:
                if plugin1 == plugin2:
                    continue

                tools1 = set(hook1.get("tools", []))
                tools2 = set(hook2.get("tools", []))
                overlap = tools1 & tools2

                if overlap:
                    conflicts.append({
                        "type": "hook_collision",
                        "severity": SEVERITY_MEDIUM,
                        "event": event,
                        "plugins": [plugin1, plugin2],
                        "overlapping_tools": list(overlap),
                        "message": f"Hooks for '{event}' in {plugin1} and {plugin2} "
                                   f"overlap on tools: {', '.join(overlap)}"
                    })

    return conflicts


def detect_routing_conflicts(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect agent routing conflicts (same keywords to different agents).

    Args:
        plugins: List of plugin info dicts

    Returns:
        List of conflict dicts
    """
    conflicts = []

    # Map keywords to (plugin, agent) pairs
    keyword_map: Dict[str, List[Tuple[str, str]]] = {}

    for plugin in plugins:
        for agent in plugin["agents"]:
            for keyword in agent.get("keywords", []):
                keyword_lower = keyword.lower()
                if keyword_lower not in keyword_map:
                    keyword_map[keyword_lower] = []
                keyword_map[keyword_lower].append((plugin["name"], agent["name"]))

    # Find conflicts
    for keyword, routes in keyword_map.items():
        # Filter to different plugins
        unique_plugins = set(r[0] for r in routes)
        if len(unique_plugins) > 1:
            conflicts.append({
                "type": "routing_overlap",
                "severity": SEVERITY_LOW,
                "keyword": keyword,
                "routes": routes,
                "message": f"Keyword '{keyword}' routes to agents in different plugins: "
                           f"{', '.join(f'{p}:{a}' for p, a in routes)}"
            })

    return conflicts


def detect_all_conflicts(plugins: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run all conflict detection.

    Args:
        plugins: List of plugin info dicts

    Returns:
        Dict with conflicts categorized by type and severity counts
    """
    all_conflicts = []

    all_conflicts.extend(detect_command_conflicts(plugins))
    all_conflicts.extend(detect_skill_conflicts(plugins))
    all_conflicts.extend(detect_hook_conflicts(plugins))
    all_conflicts.extend(detect_routing_conflicts(plugins))

    # Count by severity
    severity_counts = {
        SEVERITY_HIGH: 0,
        SEVERITY_MEDIUM: 0,
        SEVERITY_LOW: 0
    }

    for conflict in all_conflicts:
        severity = conflict.get("severity", SEVERITY_LOW)
        severity_counts[severity] += 1

    return {
        "conflicts": all_conflicts,
        "total": len(all_conflicts),
        "high": severity_counts[SEVERITY_HIGH],
        "medium": severity_counts[SEVERITY_MEDIUM],
        "low": severity_counts[SEVERITY_LOW]
    }


def format_conflict_report(result: Dict[str, Any], plugins: List[Dict[str, Any]]) -> str:
    """Format conflict detection result as human-readable report.

    Args:
        result: Result from detect_all_conflicts()
        plugins: List of plugin info dicts

    Returns:
        Formatted report string
    """
    lines = []

    # Header
    lines.append("Plugin Conflict Report")
    lines.append("=" * 50)
    lines.append("")

    # Plugin summary
    lines.append(f"Plugins Scanned: {len(plugins)}")
    for plugin in plugins:
        cmd_count = len(plugin["commands"])
        skill_count = len(plugin["skills"])
        lines.append(f"  - {plugin['name']}: {cmd_count} commands, {skill_count} skills")
    lines.append("")

    # Conflict summary
    total = result["total"]
    if total == 0:
        lines.append("No conflicts detected!")
        return "\n".join(lines)

    lines.append(f"Conflicts Found: {total}")
    lines.append(f"  High:   {result['high']}")
    lines.append(f"  Medium: {result['medium']}")
    lines.append(f"  Low:    {result['low']}")
    lines.append("")

    # Group by type
    by_type: Dict[str, List] = {}
    for conflict in result["conflicts"]:
        ctype = conflict["type"]
        if ctype not in by_type:
            by_type[ctype] = []
        by_type[ctype].append(conflict)

    # High severity first
    severity_order = [SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW]

    for severity in severity_order:
        severity_conflicts = [c for c in result["conflicts"] if c.get("severity") == severity]
        if not severity_conflicts:
            continue

        lines.append(f"[{severity.upper()}] Conflicts:")
        for conflict in severity_conflicts:
            lines.append(f"  - {conflict['message']}")
        lines.append("")

    return "\n".join(lines)


def format_quick_summary(result: Dict[str, Any], plugins: List[Dict[str, Any]]) -> str:
    """Format a one-line summary of conflict detection.

    Args:
        result: Result from detect_all_conflicts()
        plugins: List of plugin info dicts

    Returns:
        One-line summary string
    """
    total = result["total"]
    if total == 0:
        return f"Plugin Conflicts: None ({len(plugins)} plugins, all compatible)"

    parts = []
    if result["high"] > 0:
        parts.append(f"{result['high']} HIGH")
    if result["medium"] > 0:
        parts.append(f"{result['medium']} medium")
    if result["low"] > 0:
        parts.append(f"{result['low']} low")

    return f"Plugin Conflicts: {total} ({', '.join(parts)})"


def run_detection(plugins_dir: Optional[str] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run full plugin conflict detection.

    Args:
        plugins_dir: Optional override for plugins directory

    Returns:
        Tuple of (conflict_result, plugins_list)
    """
    plugins = scan_installed_plugins(plugins_dir)
    result = detect_all_conflicts(plugins)
    return result, plugins


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    plugins_dir = sys.argv[1] if len(sys.argv) > 1 else None

    print("Scanning for installed Claude Code plugins...")
    print("")

    plugins = scan_installed_plugins(plugins_dir)

    if not plugins:
        print("No plugins found.")
        sys.exit(0)

    result = detect_all_conflicts(plugins)
    print(format_conflict_report(result, plugins))
