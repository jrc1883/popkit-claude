"""Tests for MCP server detection utility."""
import pytest
import json
import os
import sys
import tempfile

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


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


def test_detect_mcp_sdk_in_dev_dependencies():
    """Detect MCP SDK in devDependencies."""
    from mcp_detector import detect_mcp_sdk

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = {"devDependencies": {"@modelcontextprotocol/sdk": "^0.9.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        result = detect_mcp_sdk(tmpdir)
        assert result["found"] is True
        assert result["version"] == "^0.9.0"
        assert result["location"] == "devDependencies"


def test_detect_mcp_sdk_not_found():
    """Return found=False when no MCP SDK."""
    from mcp_detector import detect_mcp_sdk

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = {"dependencies": {"express": "^4.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        result = detect_mcp_sdk(tmpdir)
        assert result["found"] is False


def test_detect_mcp_sdk_no_package_json():
    """Handle missing package.json gracefully."""
    from mcp_detector import detect_mcp_sdk

    with tempfile.TemporaryDirectory() as tmpdir:
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


def test_detect_mcp_directories_not_found():
    """Return empty when no MCP directories."""
    from mcp_detector import detect_mcp_directories

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"))

        result = detect_mcp_directories(tmpdir)
        assert result["found"] is False


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


def test_detect_mcp_config_not_found():
    """Handle missing .mcp.json gracefully."""
    from mcp_detector import detect_mcp_config

    with tempfile.TemporaryDirectory() as tmpdir:
        result = detect_mcp_config(tmpdir)
        assert result["found"] is False


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


def test_parse_mcp_tools_name_property():
    """Parse tools from name property syntax."""
    from mcp_detector import parse_mcp_tools

    source = '''
    const tools = [
        { name: "morning_routine", description: "Health check" },
        { name: "check_api", description: "API status" }
    ];
    '''

    tools = parse_mcp_tools(source)
    assert "morning_routine" in tools
    assert "check_api" in tools


def test_classify_health_tools():
    """Classify tools as health-related or not."""
    from mcp_detector import classify_health_tools

    tools = ["morning_routine", "check_database", "build_project", "create_user"]
    health, other = classify_health_tools(tools)

    assert "morning_routine" in health
    assert "check_database" in health
    assert "create_user" in other
    assert "build_project" in other


def test_classify_health_tools_patterns():
    """Health patterns are comprehensive."""
    from mcp_detector import classify_health_tools

    tools = [
        "morning_routine", "nightly_routine",  # routine
        "check_db", "check_api", "check_redis",  # check_*
        "api_health", "db_status",  # *_health, *_status
        "ping_server", "verify_connection",  # ping_*, verify_*
        "deploy_app", "run_migration"  # non-health
    ]
    health, other = classify_health_tools(tools)

    # Health tools
    assert "morning_routine" in health
    assert "check_db" in health
    assert "api_health" in health
    assert "ping_server" in health

    # Non-health tools
    assert "deploy_app" in other
    assert "run_migration" in other


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


def test_full_detection_no_mcp():
    """No MCP returns bash recommendation."""
    from mcp_detector import detect_mcp_infrastructure

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = {"dependencies": {"express": "^4.0.0"}}
        with open(os.path.join(tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

        result = detect_mcp_infrastructure(tmpdir)
        assert result["has_mcp"] is False
        assert result["recommendation"] == "bash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
