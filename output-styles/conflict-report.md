---
name: conflict-report
description: Plugin conflict detection report format
---

# Plugin Conflict Report Style

## Full Report Format

```
Plugin Conflict Report
==================================================

Plugins Scanned: [N]
  - [plugin-1]: [N] commands, [N] skills
  - [plugin-2]: [N] commands, [N] skills
  - [plugin-3]: [N] commands, [N] skills

Conflicts Found: [N]
  High:   [N]
  Medium: [N]
  Low:    [N]

[HIGH] Conflicts:
  - [Conflict description]
  - [Conflict description]

[MEDIUM] Conflicts:
  - [Conflict description]

[LOW] Conflicts:
  - [Conflict description]

Recommendations:
  - [Recommendation 1]
  - [Recommendation 2]
```

## Quick Summary Format

One-line summary for `--quick` option:

```
Plugin Conflicts: [N] ([N] HIGH, [N] medium, [N] low)
```

Or if no conflicts:

```
Plugin Conflicts: None ([N] plugins, all compatible)
```

## JSON Output Format

For `--json` option:

```json
{
  "scan_timestamp": "2025-01-15T10:30:00Z",
  "plugins": [
    {
      "name": "popkit",
      "path": "~/.claude/plugins/popkit",
      "commands": 16,
      "skills": 30,
      "hooks": 17,
      "agents": 30
    }
  ],
  "conflicts": {
    "total": 2,
    "high": 1,
    "medium": 1,
    "low": 0,
    "items": [
      {
        "type": "command_collision",
        "severity": "high",
        "name": "commit",
        "plugins": ["popkit", "other-plugin"],
        "message": "Command 'commit' defined in multiple plugins"
      }
    ]
  },
  "recommendations": [
    "Rename or prefix conflicting commands",
    "Consider uninstalling conflicting plugin"
  ]
}
```

## Conflict Types

### Command Collision (HIGH)

Same command name defined in multiple plugins.

```
[HIGH] Command Collision:
  Command: commit
  Plugins: popkit, other-plugin
  Impact: Only one version will be accessible

  Resolution Options:
  1. Rename command in one plugin (e.g., popkit:commit)
  2. Uninstall conflicting plugin
  3. Set plugin priority in settings
```

### Skill Collision (MEDIUM)

Same skill name defined in multiple plugins.

```
[MEDIUM] Skill Collision:
  Skill: code-review
  Plugins: popkit, another-plugin
  Impact: Skill invocation may be ambiguous

  Resolution Options:
  1. Use fully-qualified name (popkit:code-review)
  2. Rename skill in one plugin
```

### Hook Collision (MEDIUM)

Same event with overlapping tool filters.

```
[MEDIUM] Hook Collision:
  Event: PreToolUse
  Plugins: popkit, other-plugin
  Overlapping Tools: Bash, Edit
  Impact: Both hooks will run, potential conflicts

  Resolution Options:
  1. Coordinate hook behavior between plugins
  2. Disable one plugin's hooks for these tools
```

### Routing Overlap (LOW)

Same keyword routes to different agents.

```
[LOW] Routing Overlap:
  Keyword: security
  Routes:
    - popkit: security-auditor
    - other-plugin: security-scanner
  Impact: Agent selection may vary

  Resolution Options:
  1. Use more specific keywords
  2. Adjust confidence thresholds
```

## Severity Definitions

| Severity | Criteria | Impact |
|----------|----------|--------|
| HIGH | Command collision | Direct functionality conflict |
| MEDIUM | Skill or hook collision | Potential ambiguity or interference |
| LOW | Routing overlap | Minor routing differences |

## Morning Integration Format

In the morning dashboard, show summary:

```
| Plugin Conflicts:    None detected                                |
```

Or with issues:

```
| Plugin Conflicts:    2 (1 HIGH!) - run /popkit:plugin detect     |
```

## Recommendations by Type

### For Command Collisions:
- "Rename conflicting command in [plugin] to [prefix]:[command]"
- "Uninstall [plugin] if functionality is duplicated"
- "Set plugin priority: [plugin-1] > [plugin-2]"

### For Skill Collisions:
- "Use fully-qualified skill name: [plugin]:[skill]"
- "Rename skill in [plugin] to avoid conflict"

### For Hook Collisions:
- "Review hook behavior in both plugins"
- "Configure tool exclusions in [plugin] hooks"

### For Routing Overlaps:
- "Add unique keywords to distinguish agent purposes"
- "Adjust confidence thresholds for better routing"

## No Conflicts Format

When no conflicts are found:

```
Plugin Conflict Report
==================================================

Plugins Scanned: 3
  - popkit: 16 commands, 30 skills
  - other-plugin: 5 commands, 10 skills
  - another-plugin: 3 commands, 8 skills

No conflicts detected!

All plugins are compatible and can run together.
```
