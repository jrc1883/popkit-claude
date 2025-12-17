"""Integration tests for MCP detection with morning generator."""
import pytest
import os
import json
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


def create_mcp_project(tmpdir):
    """Create a mock project with full MCP infrastructure."""
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


def test_format_detection_report():
    """Detection report formats correctly."""
    from mcp_detector import detect_mcp_infrastructure, format_detection_report

    with tempfile.TemporaryDirectory() as tmpdir:
        create_mcp_project(tmpdir)

        result = detect_mcp_infrastructure(tmpdir)
        report = format_detection_report(result)

        assert "MCP Infrastructure Detected" in report
        assert "mcp_wrapper" in report
        assert "morning_routine" in report


def test_format_non_mcp_report():
    """Non-MCP report indicates bash recommendation."""
    from mcp_detector import detect_mcp_infrastructure, format_detection_report

    with tempfile.TemporaryDirectory() as tmpdir:
        create_non_mcp_project(tmpdir)

        result = detect_mcp_infrastructure(tmpdir)
        report = format_detection_report(result)

        assert "No MCP Infrastructure" in report
        assert "bash" in report.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
