#!/usr/bin/env python3
"""
Measure Context Window Usage.

Analyzes context window efficiency across skills, agents, and commands.

Usage:
    python measure_context.py [project_dir]

Output:
    JSON object with context usage metrics
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: ~4 chars per token)."""
    return len(text) // 4


def analyze_skill_context(project_dir: Path) -> Dict[str, Any]:
    """Analyze context usage in skills."""
    skills_dir = project_dir / "skills"
    if not skills_dir.exists():
        return {"total": 0, "skills": [], "issues": []}

    skills = []
    issues = []
    total_tokens = 0

    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and skill_dir.name.startswith("pop-"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                tokens = estimate_tokens(content)
                total_tokens += tokens

                skill_data = {
                    "name": skill_dir.name,
                    "tokens": tokens,
                    "chars": len(content),
                    "lines": len(content.split("\n"))
                }

                # Check against targets
                if tokens > 4000:
                    skill_data["status"] = "critical"
                    issues.append({
                        "skill": skill_dir.name,
                        "issue": "Exceeds 4000 token limit",
                        "tokens": tokens,
                        "severity": "high"
                    })
                elif tokens > 2000:
                    skill_data["status"] = "warning"
                    issues.append({
                        "skill": skill_dir.name,
                        "issue": "Exceeds 2000 token target",
                        "tokens": tokens,
                        "severity": "medium"
                    })
                else:
                    skill_data["status"] = "good"

                skills.append(skill_data)

    # Sort by token count descending
    skills.sort(key=lambda x: x["tokens"], reverse=True)

    return {
        "total_skills": len(skills),
        "total_tokens": total_tokens,
        "average_tokens": round(total_tokens / len(skills)) if skills else 0,
        "skills": skills[:20],  # Top 20 by size
        "issues": issues
    }


def analyze_agent_context(project_dir: Path) -> Dict[str, Any]:
    """Analyze context usage in agents."""
    agents_dir = project_dir / "agents"
    if not agents_dir.exists():
        return {"total": 0, "agents": [], "issues": []}

    agents = []
    issues = []
    total_tokens = 0

    # Check tier directories
    for tier_dir in agents_dir.iterdir():
        if tier_dir.is_dir() and (tier_dir.name.startswith("tier-") or tier_dir.name == "feature-workflow"):
            tier_name = tier_dir.name

            for agent_dir in tier_dir.iterdir():
                if agent_dir.is_dir():
                    agent_md = agent_dir / "AGENT.md"
                    if agent_md.exists():
                        content = agent_md.read_text(encoding="utf-8", errors="ignore")
                        tokens = estimate_tokens(content)
                        total_tokens += tokens

                        agent_data = {
                            "name": agent_dir.name,
                            "tier": tier_name,
                            "tokens": tokens,
                            "chars": len(content)
                        }

                        # Check against targets
                        if tokens > 8000:
                            agent_data["status"] = "critical"
                            issues.append({
                                "agent": agent_dir.name,
                                "tier": tier_name,
                                "issue": "Exceeds 8000 token limit",
                                "tokens": tokens,
                                "severity": "high"
                            })
                        elif tokens > 5000:
                            agent_data["status"] = "warning"
                            issues.append({
                                "agent": agent_dir.name,
                                "tier": tier_name,
                                "issue": "Exceeds 5000 token target",
                                "tokens": tokens,
                                "severity": "medium"
                            })
                        else:
                            agent_data["status"] = "good"

                        agents.append(agent_data)

    # Sort by token count descending
    agents.sort(key=lambda x: x["tokens"], reverse=True)

    return {
        "total_agents": len(agents),
        "total_tokens": total_tokens,
        "average_tokens": round(total_tokens / len(agents)) if agents else 0,
        "agents": agents[:20],
        "issues": issues
    }


def analyze_command_context(project_dir: Path) -> Dict[str, Any]:
    """Analyze context usage in commands."""
    commands_dir = project_dir / "commands"
    if not commands_dir.exists():
        return {"total": 0, "commands": [], "issues": []}

    commands = []
    issues = []
    total_tokens = 0

    for cmd_file in commands_dir.glob("*.md"):
        content = cmd_file.read_text(encoding="utf-8", errors="ignore")
        tokens = estimate_tokens(content)
        total_tokens += tokens

        cmd_data = {
            "name": cmd_file.stem,
            "tokens": tokens,
            "chars": len(content)
        }

        # Commands should be concise
        if tokens > 3000:
            cmd_data["status"] = "warning"
            issues.append({
                "command": cmd_file.stem,
                "issue": "Command doc exceeds 3000 tokens",
                "tokens": tokens,
                "severity": "low"
            })
        else:
            cmd_data["status"] = "good"

        commands.append(cmd_data)

    commands.sort(key=lambda x: x["tokens"], reverse=True)

    return {
        "total_commands": len(commands),
        "total_tokens": total_tokens,
        "average_tokens": round(total_tokens / len(commands)) if commands else 0,
        "commands": commands[:10],
        "issues": issues
    }


def analyze_config_size(project_dir: Path) -> Dict[str, Any]:
    """Analyze size of configuration files."""
    config_files = [
        ("agents/config.json", 10000),
        (".claude-plugin/plugin.json", 2000),
        ("hooks/hooks.json", 3000),
        (".mcp.json", 2000),
    ]

    configs = []
    issues = []

    for config_path, threshold in config_files:
        full_path = project_dir / config_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            tokens = estimate_tokens(content)

            config_data = {
                "path": config_path,
                "tokens": tokens,
                "threshold": threshold
            }

            if tokens > threshold:
                config_data["status"] = "warning"
                issues.append({
                    "config": config_path,
                    "issue": f"Exceeds {threshold} token target",
                    "tokens": tokens,
                    "severity": "medium"
                })
            else:
                config_data["status"] = "good"

            configs.append(config_data)

    return {
        "configs": configs,
        "issues": issues
    }


def calculate_context_score(
    skills: Dict,
    agents: Dict,
    commands: Dict,
    configs: Dict
) -> Dict[str, Any]:
    """Calculate overall context efficiency score."""
    score = 100

    # Deduct for skill issues
    for issue in skills.get("issues", []):
        if issue["severity"] == "high":
            score -= 10
        elif issue["severity"] == "medium":
            score -= 5

    # Deduct for agent issues
    for issue in agents.get("issues", []):
        if issue["severity"] == "high":
            score -= 10
        elif issue["severity"] == "medium":
            score -= 5

    # Deduct for config issues
    for issue in configs.get("issues", []):
        score -= 3

    # Bonus for efficient skills
    if skills.get("average_tokens", 0) < 1500:
        score += 5

    return {
        "score": max(0, min(100, score)),
        "total_context_tokens": (
            skills.get("total_tokens", 0) +
            agents.get("total_tokens", 0) +
            commands.get("total_tokens", 0)
        )
    }


def main():
    # Get project directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Analyze context usage
    skills = analyze_skill_context(project_dir)
    agents = analyze_agent_context(project_dir)
    commands = analyze_command_context(project_dir)
    configs = analyze_config_size(project_dir)

    # Calculate score
    scoring = calculate_context_score(skills, agents, commands, configs)

    # Determine status
    if scoring["score"] >= 90:
        status = "excellent"
    elif scoring["score"] >= 70:
        status = "good"
    elif scoring["score"] >= 50:
        status = "needs_optimization"
    else:
        status = "critical"

    report = {
        "assessment": "context-usage",
        "project_dir": str(project_dir),
        "context_score": scoring["score"],
        "total_tokens": scoring["total_context_tokens"],
        "status": status,
        "breakdown": {
            "skills": skills,
            "agents": agents,
            "commands": commands,
            "configs": configs
        },
        "all_issues": (
            skills.get("issues", []) +
            agents.get("issues", []) +
            commands.get("issues", []) +
            configs.get("issues", [])
        )
    }

    print(json.dumps(report, indent=2))
    return 0 if scoring["score"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
