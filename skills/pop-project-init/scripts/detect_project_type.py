#!/usr/bin/env python3
"""
Project Type Detection Script.

Analyze existing files to detect or suggest project type.

Usage:
    python detect_project_type.py [--dir DIR]

Output:
    JSON object with detection results
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_existing_project(project_dir: Path) -> Dict[str, Any]:
    """Detect if there's an existing project and its type."""
    indicators = {
        "has_git": (project_dir / ".git").exists(),
        "has_package_json": (project_dir / "package.json").exists(),
        "has_pyproject": (project_dir / "pyproject.toml").exists(),
        "has_setup_py": (project_dir / "setup.py").exists(),
        "has_cargo": (project_dir / "Cargo.toml").exists(),
        "has_go_mod": (project_dir / "go.mod").exists(),
        "has_readme": (project_dir / "README.md").exists(),
    }

    # Detect specific frameworks
    frameworks = []

    if indicators["has_package_json"]:
        try:
            pkg = json.loads((project_dir / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in deps:
                frameworks.append("nextjs")
            if "react" in deps and "next" not in deps:
                frameworks.append("react")
            if "vue" in deps:
                frameworks.append("vue")
            if "express" in deps:
                frameworks.append("express")
            if "fastify" in deps:
                frameworks.append("fastify")
            if "typescript" in deps:
                frameworks.append("typescript")
        except:
            pass

    if indicators["has_pyproject"]:
        try:
            content = (project_dir / "pyproject.toml").read_text()
            if "fastapi" in content.lower():
                frameworks.append("fastapi")
            if "django" in content.lower():
                frameworks.append("django")
            if "flask" in content.lower():
                frameworks.append("flask")
            if "click" in content.lower():
                frameworks.append("cli-python")
        except:
            pass

    # Detect project category
    category = None
    if any(f in frameworks for f in ["nextjs", "react", "vue"]):
        category = "web-frontend"
    elif any(f in frameworks for f in ["express", "fastify", "fastapi", "django", "flask"]):
        category = "web-backend"
    elif "cli-python" in frameworks or "typescript" in frameworks:
        category = "cli-or-library"

    return {
        "has_existing_project": any([
            indicators["has_package_json"],
            indicators["has_pyproject"],
            indicators["has_cargo"],
            indicators["has_go_mod"]
        ]),
        "indicators": indicators,
        "frameworks": frameworks,
        "category": category
    }


def suggest_project_type(detection: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest project types based on detection."""
    suggestions = []

    if detection["has_existing_project"]:
        if "nextjs" in detection["frameworks"]:
            suggestions.append({
                "type": "nextjs",
                "confidence": "high",
                "reason": "Next.js dependency detected"
            })
        elif "fastapi" in detection["frameworks"]:
            suggestions.append({
                "type": "fastapi",
                "confidence": "high",
                "reason": "FastAPI dependency detected"
            })
    else:
        # No existing project, suggest based on common patterns
        suggestions = [
            {"type": "nextjs", "confidence": "suggested", "reason": "Most popular full-stack framework"},
            {"type": "fastapi", "confidence": "suggested", "reason": "Modern Python API framework"},
            {"type": "cli", "confidence": "suggested", "reason": "Command-line tool"},
            {"type": "library", "confidence": "suggested", "reason": "Reusable package"}
        ]

    return {
        "suggestions": suggestions,
        "recommended": suggestions[0] if suggestions else None
    }


def get_template_info(project_type: str) -> Dict[str, Any]:
    """Get information about available templates."""
    templates = {
        "nextjs": {
            "name": "Next.js Application",
            "description": "Full-stack React framework with App Router",
            "features": ["TypeScript", "Tailwind CSS", "ESLint", "App Router"],
            "optional_features": ["Prisma ORM", "NextAuth.js", "Shadcn/UI"],
            "files_created": [
                "package.json",
                "tsconfig.json",
                "next.config.js",
                "tailwind.config.js",
                "src/app/layout.tsx",
                "src/app/page.tsx",
                ".eslintrc.json",
                ".gitignore",
                "README.md"
            ]
        },
        "fastapi": {
            "name": "FastAPI Service",
            "description": "Python API with async support and OpenAPI docs",
            "features": ["Pydantic Settings", "SQLAlchemy ORM", "Alembic Migrations"],
            "optional_features": ["Redis Cache", "Celery Tasks", "OAuth2"],
            "files_created": [
                "pyproject.toml",
                "src/main.py",
                "src/config.py",
                "src/models/",
                "src/routers/",
                "alembic.ini",
                ".env.example",
                ".gitignore",
                "README.md"
            ]
        },
        "cli": {
            "name": "CLI Tool",
            "description": "Command-line application with rich output",
            "features": ["Click Framework", "Rich Output"],
            "optional_features": ["Config File Support", "Shell Completion"],
            "files_created": [
                "pyproject.toml or package.json",
                "src/cli.py or src/cli.ts",
                "src/commands/",
                ".gitignore",
                "README.md"
            ]
        },
        "library": {
            "name": "Library/Package",
            "description": "Reusable package for npm or PyPI",
            "features": ["TypeScript Types", "Jest Testing"],
            "optional_features": ["ESM + CJS", "Changeset Versioning"],
            "files_created": [
                "package.json or pyproject.toml",
                "src/index.ts or src/__init__.py",
                "tests/",
                "tsconfig.json",
                ".gitignore",
                "README.md"
            ]
        },
        "plugin": {
            "name": "Claude Code Plugin",
            "description": "Plugin with skills, commands, and agents",
            "features": ["Skill Templates", "Command Templates"],
            "optional_features": ["MCP Server", "Hooks"],
            "files_created": [
                ".claude-plugin/plugin.json",
                "skills/",
                "commands/",
                "agents/",
                "README.md"
            ]
        }
    }

    return templates.get(project_type, {})


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Detect project type")
    parser.add_argument("--dir", default=".", help="Project directory")
    parser.add_argument("--type", help="Get info about specific type")
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()

    if args.type:
        # Just get template info
        info = get_template_info(args.type)
        print(json.dumps({
            "operation": "template_info",
            "type": args.type,
            "info": info
        }, indent=2))
        return 0

    # Detect existing project
    detection = detect_existing_project(project_dir)
    suggestions = suggest_project_type(detection)

    report = {
        "operation": "detect_project_type",
        "directory": str(project_dir),
        "detection": detection,
        "suggestions": suggestions["suggestions"],
        "recommended": suggestions["recommended"]
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
