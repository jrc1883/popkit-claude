# MCP Server Detection & Integration Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** Enhance `pop-morning-generator` to detect existing MCP servers and generate lightweight wrapper commands instead of bash-based health checks.

**Architecture:** Add MCP detection as Step 0 in the morning generator skill. When MCP server is detected with health-related tools, generate minimal wrapper commands (10-20 lines each) that call MCP tools. When no MCP is detected, continue with current bash-based generation. This provides a tiered approach: sophisticated projects get MCP wrappers, simpler projects get bash commands.

**Tech Stack:** Python for detection utility, Markdown for skill updates, JSON for MCP tool parsing

**Estimated Tasks:** 6 tasks

---

## Task 1: Create MCP Detection Utility

**Files:**
- Create: `hooks/utils/mcp_detector.py`
- Test: `tests/hooks/test_mcp_detector.py`

**Step 1: Write the failing test**

```python
# tests/hooks/test_mcp_detector.py
"""Tests for MCP server detection utility."""
import pytest
import json
import os
import tempfile


def test_detect_mcp_in_package_json():
    """Detect @modelcontextprotocol/sdk in package.json."""
    from mcp_detector import detect_mcp_sdk

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = {"dependencies": {"@modelcontextprotocol/sdk": "^1.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        result = detect_mcp_sdk(tmpdir)
        assert result["found"] is True
        assert result["version"] == "^1.0.0"


def test_detect_mcp_sdk_not_found():
    """Return found=False when no MCP SDK."""
    from mcp_detector import detect_mcp_sdk

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = {"dependencies": {"express": "^4.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        result = detect_mcp_sdk(tmpdir)
        assert result["found"] is False


def test_detect_mcp_server_directories():
    """Detect MCP server directories."""
    from mcp_detector import detect_mcp_directories

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create MCP-like structure
        mcp_dir = os.path.join(tmpdir, "packages", "mcp-server", "src")
        os.makedirs(mcp_dir)
        with open(os.path.join(mcp_dir, "index.ts"), "w") as f:
            f.write("export const server = new McpServer();")

        result = detect_mcp_directories(tmpdir)
        assert result["found"] is True
        assert len(result["directories"]) > 0


def test_detect_claude_mcp_json():
    """Detect .mcp.json configuration."""
    from mcp_detector import detect_mcp_config

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "mcpServers": {
                "my-project-dev": {
                    "command": "node",
                    "args": ["packages/mcp-server/dist/index.js"]
                }
            }
        }
        with open(os.path.join(tmpdir, ".mcp.json"), "w") as f:
            json.dump(config, f)

        result = detect_mcp_config(tmpdir)
        assert result["found"] is True
        assert "my-project-dev" in result["servers"]


def test_parse_mcp_tools_from_source():
    """Parse MCP tool definitions from source code."""
    from mcp_detector import parse_mcp_tools

    source = '''
    server.tool("morning_routine", "Daily health check", async () => {});
    server.tool("check_database", "Check DB connection", async () => {});
    server.tool("build_project", "Run build", async () => {});
    '''

    tools = parse_mcp_tools(source)
    assert "morning_routine" in tools
    assert "check_database" in tools
    assert len(tools) == 3


def test_classify_health_tools():
    """Classify tools as health-related or not."""
    from mcp_detector import classify_health_tools

    tools = ["morning_routine", "check_database", "build_project", "create_user"]
    health, other = classify_health_tools(tools)

    assert "morning_routine" in health
    assert "check_database" in health
    assert "create_user" in other


def test_full_mcp_detection():
    """Full detection returns comprehensive result."""
    from mcp_detector import detect_mcp_infrastructure

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json with MCP SDK
        pkg = {"dependencies": {"@modelcontextprotocol/sdk": "^1.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        # Create .mcp.json
        config = {"mcpServers": {"test-server": {}}}
        with open(os.path.join(tmpdir, ".mcp.json"), "w") as f:
            json.dump(config, f)

        result = detect_mcp_infrastructure(tmpdir)
        assert result["has_mcp"] is True
        assert result["sdk"]["found"] is True
        assert result["config"]["found"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hooks/test_mcp_detector.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'mcp_detector'"

**Step 3: Write implementation**

```python
# hooks/utils/mcp_detector.py
#!/usr/bin/env python3
"""
MCP Server Detection Utility

Detects MCP (Model Context Protocol) server infrastructure in projects.
Used by morning-generator to determine if MCP wrapper commands should
be generated instead of bash-based health checks.

Part of the popkit plugin system.
"""

import os
import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path


# Health-related tool patterns
HEALTH_PATTERNS = [
    r"morning", r"nightly", r"health", r"check_",
    r"_status", r"routine", r"ping", r"verify"
]


def detect_mcp_sdk(project_dir: str) -> Dict[str, Any]:
    """Detect @modelcontextprotocol/sdk in package.json.

    Args:
        project_dir: Path to project root

    Returns:
        Dict with found, version, location
    """
    result = {"found": False, "version": None, "location": None}

    pkg_path = os.path.join(project_dir, "package.json")
    if not os.path.exists(pkg_path):
        return result

    try:
        with open(pkg_path, "r") as f:
            pkg = json.load(f)

        # Check dependencies and devDependencies
        for dep_type in ["dependencies", "devDependencies"]:
            deps = pkg.get(dep_type, {})
            if "@modelcontextprotocol/sdk" in deps:
                result["found"] = True
                result["version"] = deps["@modelcontextprotocol/sdk"]
                result["location"] = dep_type
                return result

    except (json.JSONDecodeError, IOError):
        pass

    return result


def detect_mcp_directories(project_dir: str) -> Dict[str, Any]:
    """Detect MCP server directories.

    Looks for common patterns:
    - packages/*/mcp/
    - **/mcp-server/
    - src/mcp/

    Args:
        project_dir: Path to project root

    Returns:
        Dict with found, directories list
    """
    result = {"found": False, "directories": []}

    patterns = [
        "packages/*/mcp",
        "packages/*/src/mcp",
        "**/mcp-server",
        "src/mcp",
        "server/mcp",
    ]

    for pattern in patterns:
        for path in Path(project_dir).glob(pattern):
            if path.is_dir():
                result["found"] = True
                result["directories"].append(str(path))

    return result


def detect_mcp_config(project_dir: str) -> Dict[str, Any]:
    """Detect .mcp.json configuration.

    Args:
        project_dir: Path to project root

    Returns:
        Dict with found, servers dict
    """
    result = {"found": False, "servers": {}}

    mcp_path = os.path.join(project_dir, ".mcp.json")
    if not os.path.exists(mcp_path):
        return result

    try:
        with open(mcp_path, "r") as f:
            config = json.load(f)

        if "mcpServers" in config:
            result["found"] = True
            result["servers"] = config["mcpServers"]

    except (json.JSONDecodeError, IOError):
        pass

    return result


def parse_mcp_tools(source: str) -> List[str]:
    """Parse MCP tool names from TypeScript source code.

    Looks for patterns like:
    - server.tool("name", ...)
    - server.setRequestHandler(ListToolsRequestSchema, ...)

    Args:
        source: TypeScript source code content

    Returns:
        List of tool names
    """
    tools = []

    # Pattern 1: server.tool("name", ...)
    pattern1 = r'\.tool\s*\(\s*["\']([^"\']+)["\']'
    tools.extend(re.findall(pattern1, source))

    # Pattern 2: name: "tool_name" in tool definitions
    pattern2 = r'name:\s*["\']([^"\']+)["\']'
    tools.extend(re.findall(pattern2, source))

    return list(set(tools))  # Deduplicate


def classify_health_tools(tools: List[str]) -> Tuple[List[str], List[str]]:
    """Classify tools as health-related or other.

    Args:
        tools: List of tool names

    Returns:
        Tuple of (health_tools, other_tools)
    """
    health_tools = []
    other_tools = []

    for tool in tools:
        is_health = any(
            re.search(pattern, tool, re.IGNORECASE)
            for pattern in HEALTH_PATTERNS
        )
        if is_health:
            health_tools.append(tool)
        else:
            other_tools.append(tool)

    return health_tools, other_tools


def detect_mcp_infrastructure(project_dir: str) -> Dict[str, Any]:
    """Full MCP infrastructure detection.

    Args:
        project_dir: Path to project root

    Returns:
        Comprehensive detection result with:
        - has_mcp: bool
        - sdk: SDK detection result
        - config: .mcp.json result
        - directories: MCP directories result
        - tools: Discovered tools (if source found)
        - health_tools: Tools classified as health-related
        - recommendation: "mcp_wrapper" | "bash" | "hybrid"
    """
    result = {
        "has_mcp": False,
        "sdk": detect_mcp_sdk(project_dir),
        "config": detect_mcp_config(project_dir),
        "directories": detect_mcp_directories(project_dir),
        "tools": [],
        "health_tools": [],
        "other_tools": [],
        "recommendation": "bash"
    }

    # Determine if MCP is present
    has_mcp = (
        result["sdk"]["found"] or
        result["config"]["found"] or
        result["directories"]["found"]
    )
    result["has_mcp"] = has_mcp

    # If MCP found, try to discover tools
    if has_mcp and result["directories"]["found"]:
        all_tools = []
        for dir_path in result["directories"]["directories"]:
            # Look for TypeScript files
            for ts_file in Path(dir_path).glob("**/*.ts"):
                try:
                    with open(ts_file, "r", encoding="utf-8") as f:
                        source = f.read()
                    all_tools.extend(parse_mcp_tools(source))
                except IOError:
                    continue

        result["tools"] = list(set(all_tools))
        health, other = classify_health_tools(result["tools"])
        result["health_tools"] = health
        result["other_tools"] = other

    # Make recommendation
    if has_mcp and result["health_tools"]:
        result["recommendation"] = "mcp_wrapper"
    elif has_mcp:
        result["recommendation"] = "hybrid"  # MCP exists but no health tools
    else:
        result["recommendation"] = "bash"

    return result


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.getcwd()

    print(f"Detecting MCP infrastructure in: {project_dir}")
    result = detect_mcp_infrastructure(project_dir)

    print(f"\nMCP SDK: {'Found' if result['sdk']['found'] else 'Not found'}")
    if result["sdk"]["found"]:
        print(f"  Version: {result['sdk']['version']}")

    print(f"MCP Config: {'Found' if result['config']['found'] else 'Not found'}")
    if result["config"]["found"]:
        print(f"  Servers: {list(result['config']['servers'].keys())}")

    print(f"MCP Directories: {'Found' if result['directories']['found'] else 'Not found'}")
    if result["directories"]["found"]:
        for d in result["directories"]["directories"]:
            print(f"  - {d}")

    if result["tools"]:
        print(f"\nDiscovered Tools ({len(result['tools'])}):")
        for tool in result["tools"]:
            marker = "[HEALTH]" if tool in result["health_tools"] else ""
            print(f"  - {tool} {marker}")

    print(f"\nRecommendation: {result['recommendation']}")
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/hooks/test_mcp_detector.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add hooks/utils/mcp_detector.py tests/hooks/test_mcp_detector.py
git commit -m "feat(hooks): add MCP server detection utility

Detects MCP infrastructure in projects:
- @modelcontextprotocol/sdk in package.json
- .mcp.json configuration
- MCP server directories
- Tool discovery from TypeScript source
- Health tool classification

Part of #6 MCP Server Detection"
```

---

## Task 2: Create MCP Wrapper Template

**Files:**
- Create: `skills/pop-morning-generator/templates/mcp-wrapper.md`

**Step 1: Create the template file**

```markdown
---
description: Morning health check via MCP (Ready to Code score 0-100)
---

# /$PREFIX$:morning - $PROJECT$ Morning Check

Run the MCP-based morning health check.

## Usage

```
/$PREFIX$:morning           # Full morning report
/$PREFIX$:morning quick     # Compact summary
```

## Implementation

This command uses the project's MCP server tools for health checks.

### Primary Check

Run the `mcp__$SERVER$__morning_routine` MCP tool if available.

This returns structured JSON with:
- Service status
- Database connectivity
- Cache/Redis status
- Ready to Code score (0-100)

### Fallback Checks

If morning_routine unavailable, run these individual tools:

$HEALTH_TOOLS$

### Service Status Display

| Service | MCP Tool | Status |
|---------|----------|--------|
$SERVICE_TABLE$

## Ready to Code Score

The MCP server calculates this score based on:

| Check | Points |
|-------|--------|
| Services running | 30 |
| Database connected | 20 |
| Cache available | 15 |
| Git status clean | 20 |
| No TypeScript errors | 15 |

## Commands Reference

```bash
# Start MCP server (if not auto-started)
$START_COMMAND$

# Direct MCP tool invocation
# (Handled automatically by Claude Code)
```

## Notes

- This is an MCP wrapper command (lightweight, 10-20 lines)
- Health checks run through `mcp__$SERVER$__*` tools
- Structured JSON responses enable better automation
- Falls back to bash checks if MCP unavailable
```

**Step 2: Commit**

```bash
git add skills/pop-morning-generator/templates/mcp-wrapper.md
git commit -m "feat(morning-generator): add MCP wrapper template

Template for generating lightweight MCP-based morning commands.
Uses project's MCP server tools instead of bash commands.

Part of #6 MCP Server Detection"
```

---

## Task 3: Update Morning Generator Skill with MCP Detection

**Files:**
- Modify: `skills/pop-morning-generator/SKILL.md`

**Step 1: Add Step 0 - MCP Detection**

Add this section after the Overview and before Step 1:

```markdown
### Step 0: Detect MCP Infrastructure

Before detecting tech stack, check for existing MCP server:

```bash
# Check for MCP SDK in package.json
grep -q "@modelcontextprotocol/sdk" package.json 2>/dev/null && echo "MCP SDK: Found"

# Check for .mcp.json configuration
test -f .mcp.json && echo "MCP Config: Found"

# Check for MCP server directories
ls -d packages/*/mcp packages/*/src/mcp **/mcp-server 2>/dev/null && echo "MCP Directories: Found"
```

**Decision Tree:**

```
Has MCP SDK or .mcp.json?
  │
  ├─ YES → Has health-related MCP tools?
  │         │
  │         ├─ YES → Generate MCP wrapper commands (Tier 2)
  │         │        - Minimal 10-20 line wrappers
  │         │        - Call mcp__server__tool directly
  │         │        - Skip bash-based checks
  │         │
  │         └─ NO → Generate hybrid commands
  │                  - MCP for available tools
  │                  - Bash for missing checks
  │
  └─ NO → Generate bash-based commands (current behavior)
          - Full detection in Step 1-4
          - Comprehensive bash scripts
```

**MCP Health Tool Detection:**

Look for these patterns in MCP tool names:
- `morning_routine`, `nightly_routine`
- `check_*` (check_database, check_api, etc.)
- `*_health`, `*_status`
- `ping_*`, `verify_*`

**Example MCP Detection Output:**

```
MCP Infrastructure Detected!

Server: mcp__reseller-central-dev
SDK Version: ^1.0.0
Config: .mcp.json

Health-Related Tools (8):
  ✓ morning_routine - Daily health check
  ✓ check_api - API server status
  ✓ check_database - Database connectivity
  ✓ check_redis - Redis connection
  ✓ check_ebay_connection - eBay API status
  ✓ nightly_routine - Sleep score
  ✓ system_overview - Full system status
  ✓ verify_oauth - OAuth token status

Recommendation: Generate MCP wrapper commands

Proceed with MCP wrapper generation? [Y/n]
```
```

**Step 2: Add MCP Wrapper Generation Section**

Add after Step 4:

```markdown
### Step 5: Generate MCP Wrapper Commands (If MCP Detected)

When MCP infrastructure is detected with health tools, generate minimal wrapper commands:

**Template: `.claude/commands/[prefix]:morning.md`**

```markdown
---
description: Morning health check via MCP (Ready to Code score 0-100)
---

# /[prefix]:morning - [Project] Morning Check

Run the MCP-based morning health check.

## Implementation

Run the `mcp__[server]__morning_routine` MCP tool.

If unavailable, run individual checks:
- `mcp__[server]__check_database`
- `mcp__[server]__check_api`
- `mcp__[server]__check_redis`

Display the Ready to Code score and any issues.
```

**Benefits of MCP Wrappers:**

| Aspect | MCP Wrapper | Bash Command |
|--------|-------------|--------------|
| Lines of code | 10-20 | 100-200+ |
| Maintenance | Auto-syncs with MCP | Manual updates |
| Error handling | Structured JSON | Text parsing |
| Extensibility | Add to MCP server | Edit markdown |
```

**Step 3: Update Post-Generation Output**

Update the Post-Generation section to show MCP-specific output:

```markdown
## Post-Generation (MCP Mode)

When MCP wrappers are generated:

```
Morning command generated! (MCP Wrapper Mode)

Created:
  .claude/commands/[prefix]:morning.md  (15 lines)

MCP Server Detected: mcp__[server-name]
Health Tools Available: 8

The generated command calls these MCP tools:
  ✓ morning_routine (primary)
  ✓ check_database (fallback)
  ✓ check_api (fallback)
  ✓ check_redis (fallback)

Benefits:
  - 15 lines vs 200+ bash lines
  - Structured JSON responses
  - Auto-syncs with MCP server updates

You can now run:
  /[prefix]:morning
```
```

**Step 4: Commit**

```bash
git add skills/pop-morning-generator/SKILL.md
git commit -m "feat(morning-generator): add MCP detection and wrapper generation

Adds Step 0 for MCP infrastructure detection:
- Detects @modelcontextprotocol/sdk
- Finds .mcp.json configuration
- Discovers health-related MCP tools
- Decision tree for wrapper vs bash generation

When MCP is detected, generates lightweight wrapper commands
instead of comprehensive bash scripts.

Part of #6 MCP Server Detection"
```

---

## Task 4: Add Integration Tests

**Files:**
- Create: `tests/hooks/test_mcp_integration.py`

**Step 1: Write integration tests**

```python
# tests/hooks/test_mcp_integration.py
"""Integration tests for MCP detection with morning generator."""
import pytest
import os
import json
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


def create_mcp_project(tmpdir):
    """Create a mock project with MCP infrastructure."""
    # package.json with MCP SDK
    pkg = {
        "name": "test-project",
        "dependencies": {
            "@modelcontextprotocol/sdk": "^1.0.0",
            "express": "^4.18.0"
        }
    }
    with open(os.path.join(tmpdir, "package.json"), "w") as f:
        json.dump(pkg, f)

    # .mcp.json
    mcp_config = {
        "mcpServers": {
            "test-project-dev": {
                "command": "node",
                "args": ["dist/index.js"]
            }
        }
    }
    with open(os.path.join(tmpdir, ".mcp.json"), "w") as f:
        json.dump(mcp_config, f)

    # MCP server directory with tools
    mcp_dir = os.path.join(tmpdir, "packages", "mcp-server", "src")
    os.makedirs(mcp_dir)

    mcp_source = '''
import { McpServer } from "@modelcontextprotocol/sdk";

const server = new McpServer();

server.tool("morning_routine", "Daily health check", async () => {
    return { ready_to_code: 85 };
});

server.tool("check_database", "Check DB connection", async () => {
    return { connected: true };
});

server.tool("check_redis", "Check Redis", async () => {
    return { connected: true };
});

server.tool("build_project", "Run build", async () => {
    return { success: true };
});
'''
    with open(os.path.join(mcp_dir, "index.ts"), "w") as f:
        f.write(mcp_source)

    return tmpdir


def create_non_mcp_project(tmpdir):
    """Create a mock project without MCP."""
    pkg = {
        "name": "simple-project",
        "dependencies": {
            "express": "^4.18.0",
            "react": "^18.0.0"
        }
    }
    with open(os.path.join(tmpdir, "package.json"), "w") as f:
        json.dump(pkg, f)

    return tmpdir


def test_full_mcp_project_detection():
    """Full MCP project should recommend mcp_wrapper."""
    from mcp_detector import detect_mcp_infrastructure

    with tempfile.TemporaryDirectory() as tmpdir:
        create_mcp_project(tmpdir)

        result = detect_mcp_infrastructure(tmpdir)

        assert result["has_mcp"] is True
        assert result["sdk"]["found"] is True
        assert result["config"]["found"] is True
        assert "test-project-dev" in result["config"]["servers"]
        assert "morning_routine" in result["health_tools"]
        assert "check_database" in result["health_tools"]
        assert "build_project" in result["other_tools"]
        assert result["recommendation"] == "mcp_wrapper"


def test_non_mcp_project_detection():
    """Non-MCP project should recommend bash."""
    from mcp_detector import detect_mcp_infrastructure

    with tempfile.TemporaryDirectory() as tmpdir:
        create_non_mcp_project(tmpdir)

        result = detect_mcp_infrastructure(tmpdir)

        assert result["has_mcp"] is False
        assert result["recommendation"] == "bash"


def test_mcp_without_health_tools():
    """MCP project without health tools should recommend hybrid."""
    from mcp_detector import detect_mcp_infrastructure

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json with MCP SDK
        pkg = {"dependencies": {"@modelcontextprotocol/sdk": "^1.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        # Create .mcp.json
        config = {"mcpServers": {"test-server": {}}}
        with open(os.path.join(tmpdir, ".mcp.json"), "w") as f:
            json.dump(config, f)

        # MCP dir with non-health tools only
        mcp_dir = os.path.join(tmpdir, "packages", "mcp-server", "src")
        os.makedirs(mcp_dir)
        with open(os.path.join(mcp_dir, "index.ts"), "w") as f:
            f.write('server.tool("create_user", "Create user", async () => {});')

        result = detect_mcp_infrastructure(tmpdir)

        assert result["has_mcp"] is True
        assert len(result["health_tools"]) == 0
        assert result["recommendation"] == "hybrid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

Run: `python -m pytest tests/hooks/test_mcp_integration.py -v`
Expected: PASS (3 tests)

**Step 3: Commit**

```bash
git add tests/hooks/test_mcp_integration.py
git commit -m "test(mcp): add integration tests for MCP detection

Verifies:
- Full MCP projects recommend wrapper generation
- Non-MCP projects recommend bash generation
- MCP without health tools recommends hybrid

Part of #6 MCP Server Detection"
```

---

## Task 5: Update generate-morning Command

**Files:**
- Modify: `commands/morning.md`

**Step 1: Read current command**

Read: `commands/morning.md` to understand current structure

**Step 2: Add MCP flags**

Add to the command's argument documentation:

```markdown
## Arguments

- `generate` - Generate project-specific morning command
- `generate --bash` - Force bash-based generation (skip MCP detection)
- `generate --mcp-wrapper` - Force MCP wrapper generation
- `generate --detect` - Show MCP detection results without generating
```

**Step 3: Update description**

Update the command description:

```markdown
---
description: Morning health check via MCP (Ready to Code score 0-100)
arguments: $ARGUMENTS
---

# /popkit:morning - Morning Health Check

## Subcommands

### Default (no arguments)
Run the generic morning health check.

### generate
Generate a project-specific morning command.

**MCP Detection:** Automatically detects MCP infrastructure and generates appropriate commands:
- **MCP Found + Health Tools:** Generates lightweight MCP wrapper commands
- **MCP Found, No Health Tools:** Generates hybrid (MCP + bash)
- **No MCP:** Generates comprehensive bash-based commands

**Flags:**
- `--bash` - Force bash generation (skip MCP)
- `--mcp-wrapper` - Force MCP wrapper generation
- `--detect` - Show detection results only
```

**Step 4: Commit**

```bash
git add commands/morning.md
git commit -m "feat(commands): add MCP flags to generate-morning

Adds flags for MCP-aware morning command generation:
- --bash: Force bash-based generation
- --mcp-wrapper: Force MCP wrapper generation
- --detect: Show MCP detection results only

Part of #6 MCP Server Detection"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Step 1: Add MCP Detection section to CLAUDE.md**

Add under "Morning Routine" section:

```markdown
### MCP-Aware Generation

The morning generator detects MCP infrastructure and adapts:

| Detection | Action |
|-----------|--------|
| MCP + health tools | Generate MCP wrapper commands |
| MCP, no health tools | Generate hybrid commands |
| No MCP | Generate bash commands (default) |

**MCP Detection Checks:**
- `@modelcontextprotocol/sdk` in package.json
- `.mcp.json` configuration
- MCP server directories (`packages/*/mcp/`, etc.)
- Health tool patterns (`morning_routine`, `check_*`, etc.)

**Flags:**
```bash
/popkit:morning generate           # Auto-detect
/popkit:morning generate --bash    # Force bash
/popkit:morning generate --detect  # Show detection only
```
```

**Step 2: Update README.md**

Add to the Commands table or create a note about MCP detection:

```markdown
### MCP Server Integration

PopKit detects existing MCP servers and generates appropriate commands:

```bash
/popkit:morning generate           # Auto-detects MCP infrastructure
/popkit:morning generate --detect  # Preview MCP detection results
```

When MCP is detected with health-related tools, generates lightweight wrapper commands (10-20 lines) instead of comprehensive bash scripts (100+ lines).
```

**Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: add MCP detection documentation

Documents MCP-aware morning command generation:
- Detection logic (SDK, config, directories)
- Wrapper vs bash generation decision
- Command flags for explicit control

Closes #6"
```

---

## Verification

After all tasks complete:

```bash
# Run full test suite
python -m pytest tests/hooks/test_mcp_detector.py tests/hooks/test_mcp_integration.py -v

# Verify MCP detector works standalone
python hooks/utils/mcp_detector.py /path/to/mcp-project

# Test morning generator with MCP project
/popkit:morning generate --detect
```

## Rollback Plan

If issues arise:
1. MCP detection is additive - doesn't modify existing behavior
2. `--bash` flag always available to skip MCP
3. Revert commits in reverse order if needed:
   - `git revert HEAD~5..HEAD`

---

**Plan Confidence:** 90%

This plan provides clear implementation of MCP detection with:
- Comprehensive detection utility with tests
- Minimal wrapper template for MCP projects
- Updated skill with decision tree
- Integration tests
- Backward compatibility via flags
