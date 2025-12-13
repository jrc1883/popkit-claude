#!/usr/bin/env python3
"""
Skill Generator Script.

Generate a new PopKit skill with full resource structure.

Usage:
    python generate_skill.py SKILL_NAME [OPTIONS]

Output:
    Creates skill directory with all resources
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


SKILLS_DIR = Path(__file__).parent.parent.parent  # skills/ directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "skill"


def create_directory_structure(skill_path: Path, options: Dict[str, bool]) -> list:
    """Create the skill directory structure."""
    created = []

    # Create main skill directory
    skill_path.mkdir(parents=True, exist_ok=True)
    created.append(str(skill_path))

    # Create subdirectories based on options
    if options.get("has_workflow", True):
        (skill_path / "workflows").mkdir(exist_ok=True)
        created.append(str(skill_path / "workflows"))

    if options.get("has_scripts", True):
        (skill_path / "scripts").mkdir(exist_ok=True)
        created.append(str(skill_path / "scripts"))

    if options.get("has_checklists", True):
        (skill_path / "checklists").mkdir(exist_ok=True)
        created.append(str(skill_path / "checklists"))

    if options.get("has_templates", False):
        (skill_path / "templates").mkdir(exist_ok=True)
        created.append(str(skill_path / "templates"))

    return created


def render_template(template_path: Path, variables: Dict[str, Any]) -> str:
    """Render a template with variables (simple mustache-like substitution)."""
    if not template_path.exists():
        return ""

    content = template_path.read_text()

    # Simple variable substitution
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if isinstance(value, list):
            value = "\n".join(f'    - "{v}"' for v in value)
        elif isinstance(value, bool):
            value = str(value).lower()
        content = content.replace(placeholder, str(value))

    return content


def generate_skill_md(skill_path: Path, config: Dict[str, Any]) -> Path:
    """Generate the SKILL.md file."""
    template = TEMPLATES_DIR / "SKILL.md.template"

    variables = {
        "SKILL_NAME": config["name"],
        "DESCRIPTION": config["description"],
        "CATEGORY": config.get("category", "utility"),
        "KEYWORDS": config.get("keywords", [config["name"].replace("pop-", "")]),
        "USE_CASE_1": f"You need to {config['description'].lower()}",
        "USE_CASE_2": "The project matches the skill's triggers",
        "USE_CASE_3": "You invoke the skill manually",
        "HAS_WORKFLOW": config.get("has_workflow", True),
        "HAS_SCRIPTS": config.get("has_scripts", True),
        "HAS_CHECKLISTS": config.get("has_checklists", True),
        "HAS_TEMPLATES": config.get("has_templates", False),
        "PHASE_1_NAME": "Prepare",
        "PHASE_1_DESCRIPTION": "Gather information and validate inputs",
        "PHASE_2_NAME": "Execute",
        "PHASE_2_DESCRIPTION": "Perform the main operation",
        "PHASE_3_NAME": "Verify",
        "PHASE_3_DESCRIPTION": "Verify results and cleanup"
    }

    content = render_template(template, variables)

    # Clean up unrendered conditionals
    import re
    content = re.sub(r'\{\{#\w+\}\}.*?\{\{/\w+\}\}', '', content, flags=re.DOTALL)
    content = re.sub(r'\{\{\w+\}\}', '', content)

    output_path = skill_path / "SKILL.md"
    output_path.write_text(content)
    return output_path


def generate_workflow(skill_path: Path, config: Dict[str, Any]) -> Optional[Path]:
    """Generate the workflow JSON file."""
    if not config.get("has_workflow", True):
        return None

    template = TEMPLATES_DIR / "workflows" / "workflow.json.template"

    variables = {
        "SKILL_NAME": config["name"],
        "DESCRIPTION": config["description"],
        "PHASE_1_NAME": "Prepare",
        "PHASE_1_DESCRIPTION": "Gather information and validate inputs",
        "PHASE_2_NAME": "Execute",
        "PHASE_2_DESCRIPTION": "Perform the main operation",
        "PHASE_3_NAME": "Verify",
        "PHASE_3_DESCRIPTION": "Verify results and cleanup"
    }

    content = render_template(template, variables)

    output_path = skill_path / "workflows" / f"{config['name']}-workflow.json"
    output_path.write_text(content)
    return output_path


def generate_main_script(skill_path: Path, config: Dict[str, Any]) -> Optional[Path]:
    """Generate the main Python script."""
    if not config.get("has_scripts", True):
        return None

    template = TEMPLATES_DIR / "scripts" / "main.py.template"

    variables = {
        "SKILL_NAME": config["name"],
        "DESCRIPTION": config["description"]
    }

    content = render_template(template, variables)

    output_path = skill_path / "scripts" / "main.py"
    output_path.write_text(content)

    # Make executable on Unix
    try:
        os.chmod(output_path, 0o755)
    except:
        pass

    return output_path


def generate_checklist(skill_path: Path, config: Dict[str, Any]) -> Optional[Path]:
    """Generate the checklist JSON file."""
    if not config.get("has_checklists", True):
        return None

    template = TEMPLATES_DIR / "checklists" / "checklist.json.template"

    variables = {
        "SKILL_NAME": config["name"],
        "DESCRIPTION": config["description"]
    }

    content = render_template(template, variables)

    output_path = skill_path / "checklists" / "checklist.json"
    output_path.write_text(content)
    return output_path


def generate_skill(config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a complete skill with all resources."""
    skill_name = config["name"]
    skill_path = SKILLS_DIR / skill_name

    if skill_path.exists():
        return {
            "success": False,
            "error": f"Skill already exists: {skill_name}"
        }

    created_files = []

    # Create directory structure
    options = {
        "has_workflow": config.get("has_workflow", True),
        "has_scripts": config.get("has_scripts", True),
        "has_checklists": config.get("has_checklists", True),
        "has_templates": config.get("has_templates", False)
    }

    directories = create_directory_structure(skill_path, options)

    # Generate files
    skill_md = generate_skill_md(skill_path, config)
    created_files.append(str(skill_md))

    if options["has_workflow"]:
        workflow = generate_workflow(skill_path, config)
        if workflow:
            created_files.append(str(workflow))

    if options["has_scripts"]:
        script = generate_main_script(skill_path, config)
        if script:
            created_files.append(str(script))

    if options["has_checklists"]:
        checklist = generate_checklist(skill_path, config)
        if checklist:
            created_files.append(str(checklist))

    return {
        "success": True,
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "directories_created": directories,
        "files_created": created_files
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate a new PopKit skill")
    parser.add_argument("name", help="Skill name (e.g., pop-deploy-kubernetes)")
    parser.add_argument("--description", "-d", required=True, help="Skill description")
    parser.add_argument("--category", "-c", default="utility",
                        choices=["dev-workflow", "deployment", "quality", "setup",
                                 "analysis", "documentation", "integration", "utility"],
                        help="Skill category")
    parser.add_argument("--no-workflow", action="store_true", help="Skip workflow generation")
    parser.add_argument("--no-scripts", action="store_true", help="Skip script generation")
    parser.add_argument("--no-checklists", action="store_true", help="Skip checklist generation")
    parser.add_argument("--with-templates", action="store_true", help="Include templates directory")
    parser.add_argument("--keywords", nargs="+", help="Trigger keywords")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    args = parser.parse_args()

    # Validate skill name
    if not args.name.startswith("pop-"):
        print(json.dumps({
            "success": False,
            "error": "Skill name must start with 'pop-'"
        }, indent=2))
        return 1

    config = {
        "name": args.name,
        "description": args.description,
        "category": args.category,
        "keywords": args.keywords or [args.name.replace("pop-", "")],
        "has_workflow": not args.no_workflow,
        "has_scripts": not args.no_scripts,
        "has_checklists": not args.no_checklists,
        "has_templates": args.with_templates
    }

    if args.dry_run:
        skill_path = SKILLS_DIR / config["name"]
        print(json.dumps({
            "operation": "generate_skill",
            "dry_run": True,
            "config": config,
            "would_create": {
                "directory": str(skill_path),
                "files": [
                    "SKILL.md",
                    f"workflows/{config['name']}-workflow.json" if config["has_workflow"] else None,
                    "scripts/main.py" if config["has_scripts"] else None,
                    "checklists/checklist.json" if config["has_checklists"] else None
                ]
            }
        }, indent=2))
        return 0

    result = generate_skill(config)

    print(json.dumps({
        "operation": "generate_skill",
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
