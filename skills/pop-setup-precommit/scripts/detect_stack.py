#!/usr/bin/env python3
"""
Stack Detection Script for Pre-commit Setup.

Analyze project to determine appropriate pre-commit hooks.

Usage:
    python detect_stack.py [--dir DIR]

Output:
    JSON object with detection results
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_language(project_dir: Path) -> Dict[str, Any]:
    """Detect primary language and related tools."""
    result = {
        "primary_language": None,
        "secondary_languages": [],
        "package_manager": None
    }

    # Check for Node.js
    if (project_dir / "package.json").exists():
        result["primary_language"] = "javascript"
        result["package_manager"] = "npm"

        pkg = json.loads((project_dir / "package.json").read_text())
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        if "typescript" in deps:
            result["primary_language"] = "typescript"

        if (project_dir / "pnpm-lock.yaml").exists():
            result["package_manager"] = "pnpm"
        elif (project_dir / "yarn.lock").exists():
            result["package_manager"] = "yarn"

    # Check for Python
    elif (project_dir / "pyproject.toml").exists() or (project_dir / "setup.py").exists():
        result["primary_language"] = "python"
        result["package_manager"] = "pip"

        if (project_dir / "poetry.lock").exists():
            result["package_manager"] = "poetry"
        elif (project_dir / "Pipfile.lock").exists():
            result["package_manager"] = "pipenv"
        elif (project_dir / "uv.lock").exists():
            result["package_manager"] = "uv"

    # Check for Go
    elif (project_dir / "go.mod").exists():
        result["primary_language"] = "go"
        result["package_manager"] = "go"

    # Check for Rust
    elif (project_dir / "Cargo.toml").exists():
        result["primary_language"] = "rust"
        result["package_manager"] = "cargo"

    return result


def detect_existing_tools(project_dir: Path) -> Dict[str, Any]:
    """Detect existing linters and formatters."""
    tools = {
        "linters": [],
        "formatters": [],
        "type_checkers": [],
        "test_runners": []
    }

    # JavaScript/TypeScript tools
    eslint_configs = [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", "eslint.config.js"]
    if any((project_dir / f).exists() for f in eslint_configs):
        tools["linters"].append("eslint")

    prettier_configs = [".prettierrc", ".prettierrc.js", ".prettierrc.json", "prettier.config.js"]
    if any((project_dir / f).exists() for f in prettier_configs):
        tools["formatters"].append("prettier")

    if (project_dir / "tsconfig.json").exists():
        tools["type_checkers"].append("typescript")

    # Python tools
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text().lower()
        if "ruff" in content:
            tools["linters"].append("ruff")
            tools["formatters"].append("ruff")
        if "black" in content:
            tools["formatters"].append("black")
        if "isort" in content:
            tools["formatters"].append("isort")
        if "mypy" in content:
            tools["type_checkers"].append("mypy")
        if "pytest" in content:
            tools["test_runners"].append("pytest")

    # Check for package.json devDependencies
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        pkg = json.loads(pkg_json.read_text())
        dev_deps = pkg.get("devDependencies", {})

        if "jest" in dev_deps:
            tools["test_runners"].append("jest")
        if "vitest" in dev_deps:
            tools["test_runners"].append("vitest")

    return tools


def detect_existing_hooks(project_dir: Path) -> Dict[str, Any]:
    """Detect existing pre-commit configuration."""
    result = {
        "framework": None,
        "config_file": None,
        "hooks_installed": False
    }

    # Check for pre-commit
    if (project_dir / ".pre-commit-config.yaml").exists():
        result["framework"] = "pre-commit"
        result["config_file"] = ".pre-commit-config.yaml"

    # Check for Husky
    elif (project_dir / ".husky").exists():
        result["framework"] = "husky"
        result["config_file"] = ".husky/"

    # Check for Lefthook
    elif (project_dir / "lefthook.yml").exists():
        result["framework"] = "lefthook"
        result["config_file"] = "lefthook.yml"

    # Check if hooks are installed
    git_hooks = project_dir / ".git" / "hooks" / "pre-commit"
    if git_hooks.exists():
        result["hooks_installed"] = True

    return result


def suggest_hooks(language: str, existing_tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest appropriate hooks based on language and existing tools."""
    suggestions = []

    # General hooks (always recommended)
    suggestions.extend([
        {"hook": "trailing-whitespace", "category": "general", "recommended": True},
        {"hook": "end-of-file-fixer", "category": "general", "recommended": True},
        {"hook": "check-yaml", "category": "general", "recommended": True},
    ])

    # Language-specific hooks
    if language in ["javascript", "typescript"]:
        if "eslint" in existing_tools.get("linters", []):
            suggestions.append({"hook": "eslint", "category": "lint", "recommended": True})
        if "prettier" in existing_tools.get("formatters", []):
            suggestions.append({"hook": "prettier", "category": "format", "recommended": True})
        if "typescript" in existing_tools.get("type_checkers", []):
            suggestions.append({"hook": "tsc", "category": "typecheck", "recommended": True})

    elif language == "python":
        if "ruff" in existing_tools.get("linters", []):
            suggestions.append({"hook": "ruff", "category": "lint", "recommended": True})
            suggestions.append({"hook": "ruff-format", "category": "format", "recommended": True})
        else:
            if "black" in existing_tools.get("formatters", []):
                suggestions.append({"hook": "black", "category": "format", "recommended": True})
            if "isort" in existing_tools.get("formatters", []):
                suggestions.append({"hook": "isort", "category": "format", "recommended": True})

        if "mypy" in existing_tools.get("type_checkers", []):
            suggestions.append({"hook": "mypy", "category": "typecheck", "recommended": True})

    # Commit message hooks
    suggestions.append({"hook": "commitlint", "category": "commit-msg", "recommended": True})

    return suggestions


def recommend_framework(language: str, package_manager: str) -> str:
    """Recommend a pre-commit framework based on project."""
    # For Node.js projects, Husky is more native
    if language in ["javascript", "typescript"] and package_manager in ["npm", "yarn", "pnpm"]:
        return "husky"

    # For Python projects or mixed, pre-commit is more versatile
    return "pre-commit"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Detect stack for pre-commit setup")
    parser.add_argument("--dir", default=".", help="Project directory")
    parser.add_argument("--suggest", action="store_true", help="Suggest hooks")
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()

    language_info = detect_language(project_dir)
    existing_tools = detect_existing_tools(project_dir)
    existing_hooks = detect_existing_hooks(project_dir)

    analysis = {
        "language": language_info,
        "existing_tools": existing_tools,
        "existing_hooks": existing_hooks
    }

    if args.suggest:
        primary_lang = language_info["primary_language"] or "generic"
        analysis["suggested_hooks"] = suggest_hooks(primary_lang, existing_tools)
        analysis["recommended_framework"] = recommend_framework(
            primary_lang,
            language_info["package_manager"] or ""
        )

    report = {
        "operation": "detect_stack",
        "directory": str(project_dir),
        **analysis
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
