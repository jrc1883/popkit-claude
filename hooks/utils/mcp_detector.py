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
        with open(pkg_path, "r", encoding="utf-8") as f:
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
    - packages/*/mcp-server/
    - **/mcp-server/
    - src/mcp/

    Args:
        project_dir: Path to project root

    Returns:
        Dict with found, directories list
    """
    result = {"found": False, "directories": []}

    patterns = [
        "packages/**/mcp",
        "packages/**/mcp-server",
        "**/mcp-server",
        "src/mcp",
        "server/mcp",
    ]

    for pattern in patterns:
        for path in Path(project_dir).glob(pattern):
            if path.is_dir():
                result["found"] = True
                result["directories"].append(str(path))

    # Deduplicate
    result["directories"] = list(set(result["directories"]))

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
        with open(mcp_path, "r", encoding="utf-8") as f:
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
    - name: "tool_name" in tool definitions

    Args:
        source: TypeScript source code content

    Returns:
        List of tool names (deduplicated)
    """
    tools = []

    # Pattern 1: server.tool("name", ...) or .tool('name', ...)
    pattern1 = r'\.tool\s*\(\s*["\']([^"\']+)["\']'
    tools.extend(re.findall(pattern1, source))

    # Pattern 2: name: "tool_name" in object definitions
    pattern2 = r'name:\s*["\']([^"\']+)["\']'
    tools.extend(re.findall(pattern2, source))

    return list(set(tools))  # Deduplicate


def classify_health_tools(tools: List[str]) -> Tuple[List[str], List[str]]:
    """Classify tools as health-related or other.

    Health-related patterns:
    - morning, nightly (routine checks)
    - check_* (explicit health checks)
    - *_health, *_status (status checks)
    - ping_*, verify_* (connectivity checks)

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
        - other_tools: Non-health tools
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

    # If MCP found, try to discover tools from source
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


def format_detection_report(result: Dict[str, Any]) -> str:
    """Format detection result as human-readable report.

    Args:
        result: Result from detect_mcp_infrastructure()

    Returns:
        Formatted report string
    """
    lines = []

    if result["has_mcp"]:
        lines.append("MCP Infrastructure Detected!")
        lines.append("")
    else:
        lines.append("No MCP Infrastructure Found")
        lines.append("Recommendation: Generate bash-based commands")
        return "\n".join(lines)

    # SDK info
    if result["sdk"]["found"]:
        lines.append(f"SDK Version: {result['sdk']['version']}")
        lines.append(f"  Location: {result['sdk']['location']}")

    # Config info
    if result["config"]["found"]:
        servers = list(result["config"]["servers"].keys())
        lines.append(f"Servers: {', '.join(servers)}")

    # Directories
    if result["directories"]["found"]:
        lines.append(f"Directories: {len(result['directories']['directories'])}")
        for d in result["directories"]["directories"][:3]:  # Show max 3
            lines.append(f"  - {d}")

    # Tools
    if result["tools"]:
        lines.append("")
        lines.append(f"Discovered Tools ({len(result['tools'])}):")

        if result["health_tools"]:
            lines.append(f"  Health-Related ({len(result['health_tools'])}):")
            for tool in result["health_tools"]:
                lines.append(f"    - {tool}")

        if result["other_tools"]:
            lines.append(f"  Other ({len(result['other_tools'])}):")
            for tool in result["other_tools"][:5]:  # Show max 5
                lines.append(f"    - {tool}")

    lines.append("")
    lines.append(f"Recommendation: {result['recommendation']}")

    return "\n".join(lines)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.getcwd()

    print(f"Detecting MCP infrastructure in: {project_dir}")
    print("")

    result = detect_mcp_infrastructure(project_dir)
    print(format_detection_report(result))
