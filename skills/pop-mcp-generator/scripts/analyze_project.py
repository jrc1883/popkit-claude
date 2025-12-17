#!/usr/bin/env python3
"""
Project Analysis Script for MCP Generation.

Analyze project to determine appropriate MCP tools.

Usage:
    python analyze_project.py [--dir DIR]

Output:
    JSON object with analysis results for MCP generation
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_package_manager(project_dir: Path) -> Dict[str, Any]:
    """Detect package manager and available scripts."""
    result = {
        "package_manager": None,
        "scripts": [],
        "dependencies": []
    }

    # Check for npm/yarn/pnpm
    if (project_dir / "package.json").exists():
        try:
            pkg = json.loads((project_dir / "package.json").read_text())
            result["package_manager"] = "npm"

            if (project_dir / "pnpm-lock.yaml").exists():
                result["package_manager"] = "pnpm"
            elif (project_dir / "yarn.lock").exists():
                result["package_manager"] = "yarn"

            result["scripts"] = list(pkg.get("scripts", {}).keys())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            result["dependencies"] = list(deps.keys())
        except:
            pass

    # Check for Python
    elif (project_dir / "pyproject.toml").exists():
        result["package_manager"] = "pip"
        try:
            content = (project_dir / "pyproject.toml").read_text()
            # Extract scripts from pyproject.toml
            if "[project.scripts]" in content:
                result["scripts"].append("cli entry points")
        except:
            pass

    return result


def detect_framework(project_dir: Path) -> Dict[str, Any]:
    """Detect web framework and related tools."""
    result = {
        "framework": None,
        "dev_server_command": None,
        "test_command": None,
        "lint_command": None,
        "build_command": None,
        "typecheck_command": None
    }

    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            scripts = pkg.get("scripts", {})

            # Detect framework
            if "next" in deps:
                result["framework"] = "nextjs"
                result["dev_server_command"] = scripts.get("dev", "npm run dev")
            elif "react" in deps:
                result["framework"] = "react"
                result["dev_server_command"] = scripts.get("start", "npm start")
            elif "express" in deps:
                result["framework"] = "express"
            elif "fastify" in deps:
                result["framework"] = "fastify"

            # Common commands
            if "test" in scripts:
                result["test_command"] = "npm test"
            if "lint" in scripts:
                result["lint_command"] = "npm run lint"
            if "build" in scripts:
                result["build_command"] = "npm run build"
            if "typecheck" in scripts:
                result["typecheck_command"] = "npm run typecheck"
        except:
            pass

    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text().lower()
            if "fastapi" in content:
                result["framework"] = "fastapi"
                result["dev_server_command"] = "uvicorn main:app --reload"
            elif "django" in content:
                result["framework"] = "django"
                result["dev_server_command"] = "python manage.py runserver"
            elif "flask" in content:
                result["framework"] = "flask"
                result["dev_server_command"] = "flask run"

            result["test_command"] = "pytest"
            result["lint_command"] = "ruff check ."
            result["typecheck_command"] = "mypy ."
        except:
            pass

    return result


def detect_database(project_dir: Path) -> Dict[str, Any]:
    """Detect database configuration."""
    result = {
        "database": None,
        "orm": None,
        "connection_file": None
    }

    # Check for Prisma
    if (project_dir / "prisma" / "schema.prisma").exists():
        result["orm"] = "prisma"
        result["connection_file"] = "prisma/schema.prisma"

        schema = (project_dir / "prisma" / "schema.prisma").read_text()
        if 'provider = "postgresql"' in schema:
            result["database"] = "postgresql"
        elif 'provider = "mysql"' in schema:
            result["database"] = "mysql"
        elif 'provider = "sqlite"' in schema:
            result["database"] = "sqlite"

    # Check for SQLAlchemy
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text().lower()
        if "sqlalchemy" in content:
            result["orm"] = "sqlalchemy"
        if "alembic" in content:
            result["connection_file"] = "alembic.ini"

    # Check for environment files
    env_files = [".env", ".env.local", ".env.development"]
    for env_file in env_files:
        env_path = project_dir / env_file
        if env_path.exists():
            try:
                content = env_path.read_text()
                if "DATABASE_URL" in content:
                    if "postgresql" in content.lower():
                        result["database"] = "postgresql"
                    elif "mysql" in content.lower():
                        result["database"] = "mysql"
                    elif "sqlite" in content.lower():
                        result["database"] = "sqlite"
            except:
                pass

    return result


def detect_services(project_dir: Path) -> List[Dict[str, Any]]:
    """Detect external services and integrations."""
    services = []

    pkg_json = project_dir / "package.json"
    pyproject = project_dir / "pyproject.toml"

    deps_content = ""
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps_content = json.dumps(pkg.get("dependencies", {})).lower()
        except:
            pass

    if pyproject.exists():
        try:
            deps_content += pyproject.read_text().lower()
        except:
            pass

    # Check for common services
    service_indicators = {
        "redis": ["redis", "ioredis", "bull"],
        "mongodb": ["mongodb", "mongoose", "pymongo"],
        "elasticsearch": ["elasticsearch", "@elastic"],
        "rabbitmq": ["amqp", "amqplib", "pika"],
        "aws": ["aws-sdk", "@aws-sdk", "boto3"],
        "stripe": ["stripe"],
        "sendgrid": ["sendgrid", "@sendgrid"],
        "auth0": ["auth0"],
        "firebase": ["firebase", "firebase-admin"],
        "supabase": ["@supabase/supabase-js", "supabase"]
    }

    for service, indicators in service_indicators.items():
        for indicator in indicators:
            if indicator in deps_content:
                services.append({
                    "name": service,
                    "indicator": indicator
                })
                break

    return services


def suggest_mcp_tools(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest MCP tools based on analysis."""
    tools = []

    # Always include git tools
    tools.extend([
        {"name": "git_status", "category": "git", "recommended": True},
        {"name": "git_diff", "category": "git", "recommended": True},
        {"name": "git_recent_commits", "category": "git", "recommended": True}
    ])

    # Quality tools based on detected commands
    framework = analysis.get("framework", {})
    if framework.get("test_command"):
        tools.append({"name": "run_tests", "category": "quality", "command": framework["test_command"], "recommended": True})
    if framework.get("lint_command"):
        tools.append({"name": "run_lint", "category": "quality", "command": framework["lint_command"], "recommended": True})
    if framework.get("typecheck_command"):
        tools.append({"name": "run_typecheck", "category": "quality", "command": framework["typecheck_command"], "recommended": True})
    if framework.get("build_command"):
        tools.append({"name": "run_build", "category": "quality", "command": framework["build_command"], "recommended": False})

    # Health checks
    if framework.get("dev_server_command"):
        tools.append({"name": "dev_server_health", "category": "health", "recommended": True})

    # Database tools
    database = analysis.get("database", {})
    if database.get("database"):
        tools.append({"name": "db_health", "category": "health", "recommended": True})

    # Service-specific tools
    for service in analysis.get("services", []):
        if service["name"] == "redis":
            tools.append({"name": "redis_health", "category": "health", "recommended": True})

    return tools


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze project for MCP generation")
    parser.add_argument("--dir", default=".", help="Project directory")
    parser.add_argument("--suggest", action="store_true", help="Suggest MCP tools")
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()

    analysis = {
        "package_manager": detect_package_manager(project_dir),
        "framework": detect_framework(project_dir),
        "database": detect_database(project_dir),
        "services": detect_services(project_dir)
    }

    if args.suggest:
        analysis["suggested_tools"] = suggest_mcp_tools(analysis)

    report = {
        "operation": "analyze_project",
        "directory": str(project_dir),
        **analysis
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
