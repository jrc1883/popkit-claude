"""Tests for plugin conflict detection utility.

Tests the plugin_detector.py module which scans installed Claude Code plugins
and detects conflicts in commands, skills, hooks, and agent routing.
"""
import pytest
import json
import os
import sys
from pathlib import Path
import tempfile

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_plugin_data():
    """Mock plugin data structures for unit tests."""
    return [
        {
            "name": "popkit",
            "path": "/fake/plugins/popkit",
            "commands": [
                {"name": "commit", "file": "commit.md", "description": "Create commit"},
                {"name": "review", "file": "review.md", "description": "Code review"}
            ],
            "skills": [
                {"name": "pop-session-capture", "file": "pop-session-capture/SKILL.md", "description": "Capture state"},
                {"name": "pop-brainstorming", "file": "pop-brainstorming/SKILL.md", "description": "Brainstorm ideas"}
            ],
            "hooks": [
                {"name": "pre-tool-use", "event": "PreToolUse", "tools": ["Bash", "Edit"], "file": "hooks.json"},
                {"name": "post-tool-use", "event": "PostToolUse", "tools": ["Bash"], "file": "hooks.json"}
            ],
            "agents": [
                {"name": "code-reviewer", "keywords": ["review", "code quality"], "file_patterns": ["*.ts", "*.js"], "error_patterns": []},
                {"name": "bug-whisperer", "keywords": ["bug", "error", "crash"], "file_patterns": [], "error_patterns": ["Error:", "Exception:"]}
            ]
        },
        {
            "name": "devtools",
            "path": "/fake/plugins/devtools",
            "commands": [
                {"name": "lint", "file": "lint.md", "description": "Run linter"},
                {"name": "test", "file": "test.md", "description": "Run tests"}
            ],
            "skills": [
                {"name": "dev-optimize", "file": "dev-optimize/SKILL.md", "description": "Optimize code"}
            ],
            "hooks": [
                {"name": "pre-tool-use", "event": "PreToolUse", "tools": ["Write", "Read"], "file": "hooks.json"}
            ],
            "agents": [
                {"name": "test-runner", "keywords": ["test", "testing"], "file_patterns": ["*.test.ts"], "error_patterns": []}
            ]
        }
    ]


@pytest.fixture
def conflicting_plugin_data():
    """Mock plugin data with conflicts for testing detection."""
    return [
        {
            "name": "plugin-a",
            "path": "/fake/plugins/plugin-a",
            "commands": [
                {"name": "shared-command", "file": "shared-command.md", "description": "A command"}
            ],
            "skills": [
                {"name": "shared-skill", "file": "shared-skill/SKILL.md", "description": "A skill"}
            ],
            "hooks": [
                {"name": "pre-hook", "event": "PreToolUse", "tools": ["Bash", "Edit"], "file": "hooks.json"}
            ],
            "agents": [
                {"name": "agent-a", "keywords": ["review", "check"], "file_patterns": [], "error_patterns": []}
            ]
        },
        {
            "name": "plugin-b",
            "path": "/fake/plugins/plugin-b",
            "commands": [
                {"name": "shared-command", "file": "shared-command.md", "description": "Same command name!"}
            ],
            "skills": [
                {"name": "shared-skill", "file": "shared-skill/SKILL.md", "description": "Same skill name!"}
            ],
            "hooks": [
                {"name": "pre-hook", "event": "PreToolUse", "tools": ["Bash", "Write"], "file": "hooks.json"}
            ],
            "agents": [
                {"name": "agent-b", "keywords": ["review", "audit"], "file_patterns": [], "error_patterns": []}
            ]
        }
    ]


@pytest.fixture
def tmp_plugin_dir(tmp_path):
    """Create a temporary plugin directory with test plugins."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Create plugin 1
    plugin1 = plugins_dir / "test-plugin-1"
    plugin1.mkdir()

    # Plugin manifest
    manifest_dir = plugin1 / ".claude-plugin"
    manifest_dir.mkdir()
    with open(manifest_dir / "plugin.json", "w") as f:
        json.dump({"name": "test-plugin-1", "version": "1.0.0"}, f)

    # Commands
    commands_dir = plugin1 / "commands"
    commands_dir.mkdir()
    with open(commands_dir / "test-command.md", "w") as f:
        f.write("---\ndescription: A test command\n---\n# Test Command")

    # Skills
    skills_dir = plugin1 / "skills"
    skills_dir.mkdir()
    skill1_dir = skills_dir / "test-skill"
    skill1_dir.mkdir()
    with open(skill1_dir / "SKILL.md", "w") as f:
        f.write("---\ndescription: A test skill\n---\n# Test Skill")

    # Hooks
    hooks_dir = plugin1 / "hooks"
    hooks_dir.mkdir()
    with open(hooks_dir / "hooks.json", "w") as f:
        json.dump({
            "hooks": [
                {"matcher": "pre-hook", "event": "PreToolUse", "tools": ["Bash"]}
            ]
        }, f)

    # Agents
    agents_dir = plugin1 / "agents"
    agents_dir.mkdir()
    with open(agents_dir / "config.json", "w") as f:
        json.dump({
            "routing": {
                "test-agent": {
                    "keywords": ["test", "testing"],
                    "file_patterns": ["*.test.ts"]
                }
            }
        }, f)

    # Create plugin 2 (minimal)
    plugin2 = plugins_dir / "test-plugin-2"
    plugin2.mkdir()
    manifest_dir2 = plugin2 / ".claude-plugin"
    manifest_dir2.mkdir()
    with open(manifest_dir2 / "plugin.json", "w") as f:
        json.dump({"name": "test-plugin-2", "version": "1.0.0"}, f)

    return str(plugins_dir)


# =============================================================================
# Command Conflict Detection Tests
# =============================================================================

def test_detect_command_conflicts_none(mock_plugin_data):
    """No conflicts when all commands have unique names."""
    from plugin_detector import detect_command_conflicts

    conflicts = detect_command_conflicts(mock_plugin_data)
    assert len(conflicts) == 0


def test_detect_command_conflicts_collision(conflicting_plugin_data):
    """Detect command name collision between plugins."""
    from plugin_detector import detect_command_conflicts

    conflicts = detect_command_conflicts(conflicting_plugin_data)

    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "command_collision"
    assert conflicts[0]["severity"] == "high"
    assert conflicts[0]["name"] == "shared-command"
    assert set(conflicts[0]["plugins"]) == {"plugin-a", "plugin-b"}
    assert "shared-command" in conflicts[0]["message"]


def test_detect_command_conflicts_three_plugins():
    """Detect collision across three plugins."""
    from plugin_detector import detect_command_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [{"name": "common", "file": "common.md", "description": ""}],
            "skills": [], "hooks": [], "agents": []
        },
        {
            "name": "plugin-2",
            "commands": [{"name": "common", "file": "common.md", "description": ""}],
            "skills": [], "hooks": [], "agents": []
        },
        {
            "name": "plugin-3",
            "commands": [{"name": "common", "file": "common.md", "description": ""}],
            "skills": [], "hooks": [], "agents": []
        }
    ]

    conflicts = detect_command_conflicts(plugins)

    assert len(conflicts) == 1
    assert len(conflicts[0]["plugins"]) == 3
    assert set(conflicts[0]["plugins"]) == {"plugin-1", "plugin-2", "plugin-3"}


# =============================================================================
# Skill Conflict Detection Tests
# =============================================================================

def test_detect_skill_conflicts_none(mock_plugin_data):
    """No conflicts when all skills have unique names."""
    from plugin_detector import detect_skill_conflicts

    conflicts = detect_skill_conflicts(mock_plugin_data)
    assert len(conflicts) == 0


def test_detect_skill_conflicts_collision(conflicting_plugin_data):
    """Detect skill name collision between plugins."""
    from plugin_detector import detect_skill_conflicts

    conflicts = detect_skill_conflicts(conflicting_plugin_data)

    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "skill_collision"
    assert conflicts[0]["severity"] == "medium"
    assert conflicts[0]["name"] == "shared-skill"
    assert set(conflicts[0]["plugins"]) == {"plugin-a", "plugin-b"}
    assert "shared-skill" in conflicts[0]["message"]


# =============================================================================
# Hook Conflict Detection Tests
# =============================================================================

def test_detect_hook_conflicts_none(mock_plugin_data):
    """No conflicts when hooks don't overlap on tools."""
    from plugin_detector import detect_hook_conflicts

    conflicts = detect_hook_conflicts(mock_plugin_data)

    # popkit has PreToolUse with [Bash, Edit]
    # devtools has PreToolUse with [Write, Read]
    # No overlap, so no conflicts
    assert len(conflicts) == 0


def test_detect_hook_conflicts_overlap(conflicting_plugin_data):
    """Detect hook conflicts when same event overlaps on tools."""
    from plugin_detector import detect_hook_conflicts

    conflicts = detect_hook_conflicts(conflicting_plugin_data)

    # Both plugins have PreToolUse with Bash tool
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "hook_collision"
    assert conflicts[0]["severity"] == "medium"
    assert conflicts[0]["event"] == "PreToolUse"
    assert set(conflicts[0]["plugins"]) == {"plugin-a", "plugin-b"}
    assert "Bash" in conflicts[0]["overlapping_tools"]


def test_detect_hook_conflicts_different_events():
    """No conflicts when hooks use different events."""
    from plugin_detector import detect_hook_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [], "skills": [], "agents": [],
            "hooks": [
                {"name": "pre", "event": "PreToolUse", "tools": ["Bash"], "file": "hooks.json"}
            ]
        },
        {
            "name": "plugin-2",
            "commands": [], "skills": [], "agents": [],
            "hooks": [
                {"name": "post", "event": "PostToolUse", "tools": ["Bash"], "file": "hooks.json"}
            ]
        }
    ]

    conflicts = detect_hook_conflicts(plugins)
    assert len(conflicts) == 0


def test_detect_hook_conflicts_same_plugin():
    """No conflicts for multiple hooks in same plugin."""
    from plugin_detector import detect_hook_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [], "skills": [], "agents": [],
            "hooks": [
                {"name": "hook-1", "event": "PreToolUse", "tools": ["Bash"], "file": "hooks.json"},
                {"name": "hook-2", "event": "PreToolUse", "tools": ["Bash"], "file": "hooks.json"}
            ]
        }
    ]

    conflicts = detect_hook_conflicts(plugins)
    assert len(conflicts) == 0  # Same plugin, not a conflict


# =============================================================================
# Routing Conflict Detection Tests
# =============================================================================

def test_detect_routing_conflicts_none(mock_plugin_data):
    """No conflicts when keywords route to different plugins."""
    from plugin_detector import detect_routing_conflicts

    conflicts = detect_routing_conflicts(mock_plugin_data)

    # popkit has "review" -> code-reviewer
    # devtools has "test" -> test-runner
    # No overlap
    assert len(conflicts) == 0


def test_detect_routing_conflicts_overlap(conflicting_plugin_data):
    """Detect routing conflicts when keyword maps to multiple plugins."""
    from plugin_detector import detect_routing_conflicts

    conflicts = detect_routing_conflicts(conflicting_plugin_data)

    # Both plugins use "review" keyword
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "routing_overlap"
    assert conflicts[0]["severity"] == "low"
    assert conflicts[0]["keyword"] == "review"

    # Check routes contain both plugins
    routes = conflicts[0]["routes"]
    plugin_names = [r[0] for r in routes]
    assert set(plugin_names) == {"plugin-a", "plugin-b"}


def test_detect_routing_conflicts_case_insensitive():
    """Routing conflict detection is case-insensitive."""
    from plugin_detector import detect_routing_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [], "skills": [], "hooks": [],
            "agents": [
                {"name": "agent-1", "keywords": ["Review"], "file_patterns": [], "error_patterns": []}
            ]
        },
        {
            "name": "plugin-2",
            "commands": [], "skills": [], "hooks": [],
            "agents": [
                {"name": "agent-2", "keywords": ["review"], "file_patterns": [], "error_patterns": []}
            ]
        }
    ]

    conflicts = detect_routing_conflicts(plugins)
    assert len(conflicts) == 1
    assert conflicts[0]["keyword"] == "review"


# =============================================================================
# Combined Detection Tests
# =============================================================================

def test_detect_all_conflicts_none(mock_plugin_data):
    """No conflicts returns empty result with correct structure."""
    from plugin_detector import detect_all_conflicts

    result = detect_all_conflicts(mock_plugin_data)

    assert result["total"] == 0
    assert result["high"] == 0
    assert result["medium"] == 0
    assert result["low"] == 0
    assert len(result["conflicts"]) == 0


def test_detect_all_conflicts_multiple(conflicting_plugin_data):
    """Detect all types of conflicts."""
    from plugin_detector import detect_all_conflicts

    result = detect_all_conflicts(conflicting_plugin_data)

    # Should have: 1 command (high), 1 skill (medium), 1 hook (medium), 1 routing (low)
    assert result["total"] == 4
    assert result["high"] == 1  # command collision
    assert result["medium"] == 2  # skill + hook collisions
    assert result["low"] == 1  # routing overlap

    # Check conflict types present
    conflict_types = [c["type"] for c in result["conflicts"]]
    assert "command_collision" in conflict_types
    assert "skill_collision" in conflict_types
    assert "hook_collision" in conflict_types
    assert "routing_overlap" in conflict_types


def test_detect_all_conflicts_severity_counts():
    """Severity counts are accurate."""
    from plugin_detector import detect_all_conflicts

    plugins = [
        {
            "name": "plugin-a",
            "commands": [{"name": "cmd1", "file": "", "description": ""}, {"name": "cmd2", "file": "", "description": ""}],
            "skills": [{"name": "skill1", "file": "", "description": ""}],
            "hooks": [],
            "agents": []
        },
        {
            "name": "plugin-b",
            "commands": [{"name": "cmd1", "file": "", "description": ""}, {"name": "cmd2", "file": "", "description": ""}],
            "skills": [{"name": "skill1", "file": "", "description": ""}],
            "hooks": [],
            "agents": []
        }
    ]

    result = detect_all_conflicts(plugins)

    assert result["total"] == 3  # 2 command + 1 skill
    assert result["high"] == 2  # Both commands are HIGH
    assert result["medium"] == 1  # Skill is MEDIUM
    assert result["low"] == 0


# =============================================================================
# Report Formatting Tests
# =============================================================================

def test_format_conflict_report_no_conflicts(mock_plugin_data):
    """Report with no conflicts says so."""
    from plugin_detector import detect_all_conflicts, format_conflict_report

    result = detect_all_conflicts(mock_plugin_data)
    report = format_conflict_report(result, mock_plugin_data)

    assert "No conflicts detected!" in report
    assert "Plugins Scanned: 2" in report
    assert "popkit" in report
    assert "devtools" in report


def test_format_conflict_report_with_conflicts(conflicting_plugin_data):
    """Report with conflicts lists them by severity."""
    from plugin_detector import detect_all_conflicts, format_conflict_report

    result = detect_all_conflicts(conflicting_plugin_data)
    report = format_conflict_report(result, conflicting_plugin_data)

    assert "Conflicts Found: 4" in report
    assert "High:   1" in report
    assert "Medium: 2" in report
    assert "Low:    1" in report

    # Check severity sections
    assert "[HIGH] Conflicts:" in report
    assert "[MEDIUM] Conflicts:" in report
    assert "[LOW] Conflicts:" in report

    # Check messages
    assert "shared-command" in report
    assert "shared-skill" in report


def test_format_conflict_report_high_severity_first(conflicting_plugin_data):
    """HIGH severity conflicts appear before MEDIUM and LOW."""
    from plugin_detector import detect_all_conflicts, format_conflict_report

    result = detect_all_conflicts(conflicting_plugin_data)
    report = format_conflict_report(result, conflicting_plugin_data)

    high_pos = report.find("[HIGH]")
    medium_pos = report.find("[MEDIUM]")
    low_pos = report.find("[LOW]")

    assert high_pos < medium_pos < low_pos


def test_format_quick_summary_no_conflicts(mock_plugin_data):
    """Quick summary with no conflicts mentions compatibility."""
    from plugin_detector import detect_all_conflicts, format_quick_summary

    result = detect_all_conflicts(mock_plugin_data)
    summary = format_quick_summary(result, mock_plugin_data)

    assert "None" in summary
    assert "2 plugins" in summary
    assert "all compatible" in summary


def test_format_quick_summary_with_conflicts(conflicting_plugin_data):
    """Quick summary lists severity counts."""
    from plugin_detector import detect_all_conflicts, format_quick_summary

    result = detect_all_conflicts(conflicting_plugin_data)
    summary = format_quick_summary(result, conflicting_plugin_data)

    assert "4" in summary  # Total conflicts
    assert "1 HIGH" in summary
    assert "2 medium" in summary
    assert "1 low" in summary


def test_format_quick_summary_one_line():
    """Quick summary is one line."""
    from plugin_detector import detect_all_conflicts, format_quick_summary

    plugins = [
        {"name": "p1", "commands": [], "skills": [], "hooks": [], "agents": []}
    ]

    result = detect_all_conflicts(plugins)
    summary = format_quick_summary(result, plugins)

    assert "\n" not in summary


# =============================================================================
# Plugin Scanning Tests
# =============================================================================

def test_scan_plugin_commands(tmp_plugin_dir):
    """Scan finds .md files in commands/ directory."""
    from plugin_detector import scan_plugin_commands

    plugin_path = os.path.join(tmp_plugin_dir, "test-plugin-1")
    commands = scan_plugin_commands(plugin_path)

    assert len(commands) == 1
    assert commands[0]["name"] == "test-command"
    assert commands[0]["description"] == "A test command"


def test_scan_plugin_commands_missing_directory(tmp_path):
    """Handles missing commands/ directory gracefully."""
    from plugin_detector import scan_plugin_commands

    plugin_path = tmp_path / "empty-plugin"
    plugin_path.mkdir()

    commands = scan_plugin_commands(str(plugin_path))
    assert commands == []


def test_scan_plugin_commands_no_frontmatter(tmp_path):
    """Handles command files without frontmatter."""
    from plugin_detector import scan_plugin_commands

    plugin_path = tmp_path / "plugin"
    commands_dir = plugin_path / "commands"
    commands_dir.mkdir(parents=True)

    with open(commands_dir / "simple.md", "w") as f:
        f.write("# Simple Command\nNo frontmatter")

    commands = scan_plugin_commands(str(plugin_path))
    assert len(commands) == 1
    assert commands[0]["name"] == "simple"
    assert commands[0]["description"] == ""


def test_scan_plugin_skills(tmp_plugin_dir):
    """Scan finds SKILL.md in skills/*/ directories."""
    from plugin_detector import scan_plugin_skills

    plugin_path = os.path.join(tmp_plugin_dir, "test-plugin-1")
    skills = scan_plugin_skills(plugin_path)

    assert len(skills) == 1
    assert skills[0]["name"] == "test-skill"
    assert skills[0]["description"] == "A test skill"


def test_scan_plugin_skills_missing_directory(tmp_path):
    """Handles missing skills/ directory gracefully."""
    from plugin_detector import scan_plugin_skills

    plugin_path = tmp_path / "empty-plugin"
    plugin_path.mkdir()

    skills = scan_plugin_skills(str(plugin_path))
    assert skills == []


def test_scan_plugin_skills_truncates_description(tmp_path):
    """Long descriptions are truncated to 100 chars."""
    from plugin_detector import scan_plugin_skills

    plugin_path = tmp_path / "plugin"
    skill_dir = plugin_path / "skills" / "long-skill"
    skill_dir.mkdir(parents=True)

    long_desc = "A" * 200
    with open(skill_dir / "SKILL.md", "w") as f:
        f.write(f"---\ndescription: {long_desc}\n---\n# Skill")

    skills = scan_plugin_skills(str(plugin_path))
    assert len(skills[0]["description"]) == 100


def test_scan_plugin_hooks(tmp_plugin_dir):
    """Scan reads hooks from hooks/hooks.json."""
    from plugin_detector import scan_plugin_hooks

    plugin_path = os.path.join(tmp_plugin_dir, "test-plugin-1")
    hooks = scan_plugin_hooks(plugin_path)

    assert len(hooks) == 1
    assert hooks[0]["name"] == "pre-hook"
    assert hooks[0]["event"] == "PreToolUse"
    assert "Bash" in hooks[0]["tools"]


def test_scan_plugin_hooks_missing_file(tmp_path):
    """Handles missing hooks.json gracefully."""
    from plugin_detector import scan_plugin_hooks

    plugin_path = tmp_path / "empty-plugin"
    plugin_path.mkdir()

    hooks = scan_plugin_hooks(str(plugin_path))
    assert hooks == []


def test_scan_plugin_agents(tmp_plugin_dir):
    """Scan reads agents from agents/config.json."""
    from plugin_detector import scan_plugin_agents

    plugin_path = os.path.join(tmp_plugin_dir, "test-plugin-1")
    agents = scan_plugin_agents(plugin_path)

    assert len(agents) == 1
    assert agents[0]["name"] == "test-agent"
    assert "test" in agents[0]["keywords"]
    assert "*.test.ts" in agents[0]["file_patterns"]


def test_scan_plugin_agents_missing_file(tmp_path):
    """Handles missing agents/config.json gracefully."""
    from plugin_detector import scan_plugin_agents

    plugin_path = tmp_path / "empty-plugin"
    plugin_path.mkdir()

    agents = scan_plugin_agents(str(plugin_path))
    assert agents == []


# =============================================================================
# Full Plugin Scanning Tests
# =============================================================================

def test_scan_installed_plugins(tmp_plugin_dir):
    """Scan finds all plugins in directory."""
    from plugin_detector import scan_installed_plugins

    plugins = scan_installed_plugins(tmp_plugin_dir)

    assert len(plugins) == 2
    plugin_names = [p["name"] for p in plugins]
    assert "test-plugin-1" in plugin_names
    assert "test-plugin-2" in plugin_names

    # Check structure
    plugin1 = next(p for p in plugins if p["name"] == "test-plugin-1")
    assert len(plugin1["commands"]) == 1
    assert len(plugin1["skills"]) == 1
    assert len(plugin1["hooks"]) == 1
    assert len(plugin1["agents"]) == 1


def test_scan_installed_plugins_missing_directory(tmp_path):
    """Handles missing plugins directory gracefully."""
    from plugin_detector import scan_installed_plugins

    fake_dir = tmp_path / "nonexistent"
    plugins = scan_installed_plugins(str(fake_dir))

    assert plugins == []


def test_scan_installed_plugins_no_manifest(tmp_path):
    """Skips directories without plugin.json manifest."""
    from plugin_detector import scan_installed_plugins

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Create directory without manifest
    bad_plugin = plugins_dir / "bad-plugin"
    bad_plugin.mkdir()

    plugins = scan_installed_plugins(str(plugins_dir))
    assert plugins == []


def test_scan_installed_plugins_alternate_manifest_location(tmp_path):
    """Finds plugin.json in alternate location (root instead of .claude-plugin/)."""
    from plugin_detector import scan_installed_plugins

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    plugin = plugins_dir / "alt-plugin"
    plugin.mkdir()

    # Put manifest in root instead of .claude-plugin/
    with open(plugin / "plugin.json", "w") as f:
        json.dump({"name": "alt-plugin", "version": "1.0.0"}, f)

    plugins = scan_installed_plugins(str(plugins_dir))
    assert len(plugins) == 1
    assert plugins[0]["name"] == "alt-plugin"


def test_scan_installed_plugins_invalid_json(tmp_path):
    """Skips plugins with invalid JSON manifest."""
    from plugin_detector import scan_installed_plugins

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    plugin = plugins_dir / "bad-json"
    plugin.mkdir()
    manifest_dir = plugin / ".claude-plugin"
    manifest_dir.mkdir()

    with open(manifest_dir / "plugin.json", "w") as f:
        f.write("{invalid json")

    plugins = scan_installed_plugins(str(plugins_dir))
    assert plugins == []


# =============================================================================
# Integration Tests
# =============================================================================

def test_run_detection(tmp_plugin_dir):
    """Full detection returns result and plugins."""
    from plugin_detector import run_detection

    result, plugins = run_detection(tmp_plugin_dir)

    assert len(plugins) == 2
    assert result["total"] >= 0
    assert "conflicts" in result
    assert "high" in result
    assert "medium" in result
    assert "low" in result


def test_get_plugins_directory():
    """Gets ~/.claude/plugins directory."""
    from plugin_detector import get_plugins_directory

    plugins_dir = get_plugins_directory()

    assert ".claude" in plugins_dir
    assert "plugins" in plugins_dir
    assert os.path.expanduser("~") in plugins_dir


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

def test_empty_plugin_list():
    """All detection functions handle empty plugin list."""
    from plugin_detector import (
        detect_command_conflicts,
        detect_skill_conflicts,
        detect_hook_conflicts,
        detect_routing_conflicts,
        detect_all_conflicts
    )

    empty_plugins = []

    assert detect_command_conflicts(empty_plugins) == []
    assert detect_skill_conflicts(empty_plugins) == []
    assert detect_hook_conflicts(empty_plugins) == []
    assert detect_routing_conflicts(empty_plugins) == []

    result = detect_all_conflicts(empty_plugins)
    assert result["total"] == 0


def test_plugin_with_no_components():
    """Handles plugins with empty component lists."""
    from plugin_detector import detect_all_conflicts

    plugins = [
        {
            "name": "empty-plugin",
            "path": "/fake/path",
            "commands": [],
            "skills": [],
            "hooks": [],
            "agents": []
        }
    ]

    result = detect_all_conflicts(plugins)
    assert result["total"] == 0


def test_hook_with_no_tools():
    """Handles hooks with empty tools list."""
    from plugin_detector import detect_hook_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [], "skills": [], "agents": [],
            "hooks": [
                {"name": "hook-1", "event": "PreToolUse", "tools": [], "file": "hooks.json"}
            ]
        },
        {
            "name": "plugin-2",
            "commands": [], "skills": [], "agents": [],
            "hooks": [
                {"name": "hook-2", "event": "PreToolUse", "tools": [], "file": "hooks.json"}
            ]
        }
    ]

    conflicts = detect_hook_conflicts(plugins)
    assert len(conflicts) == 0  # No tools, no overlap


def test_agent_with_no_keywords():
    """Handles agents with empty keywords list."""
    from plugin_detector import detect_routing_conflicts

    plugins = [
        {
            "name": "plugin-1",
            "commands": [], "skills": [], "hooks": [],
            "agents": [
                {"name": "agent-1", "keywords": [], "file_patterns": [], "error_patterns": []}
            ]
        }
    ]

    conflicts = detect_routing_conflicts(plugins)
    assert len(conflicts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
