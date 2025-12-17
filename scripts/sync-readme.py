#!/usr/bin/env python3
"""
README Auto-Generation Sync Script

Scans commands and agents directories, extracts metadata,
and updates AUTO-GEN sections in README.md.

Usage:
    python scripts/sync-readme.py [--dry-run]
"""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional


def extract_frontmatter(file_path: Path) -> Optional[Dict]:
    """Extract YAML frontmatter from markdown file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
    except Exception:
        pass
    return None


def get_commands(commands_dir: Path) -> List[Dict]:
    """Scan commands directory and extract metadata."""
    commands = []
    for cmd_file in sorted(commands_dir.glob('*.md')):
        if cmd_file.name.startswith('_'):
            continue

        meta = extract_frontmatter(cmd_file)
        if not meta:
            # Try to extract from content
            content = cmd_file.read_text(encoding='utf-8')
            name = cmd_file.stem
            # Look for description in first paragraph
            lines = content.split('\n')
            desc = ''
            for line in lines:
                if line.strip() and not line.startswith('#') and not line.startswith('-'):
                    desc = line.strip()[:80]
                    break
            commands.append({'name': name, 'description': desc})
        else:
            commands.append({
                'name': meta.get('name', cmd_file.stem),
                'description': meta.get('description', '')[:80]
            })
    return commands


def get_agents(agents_dir: Path) -> Dict[str, List[Dict]]:
    """Scan agents directory and extract metadata by tier."""
    tiers = {
        'tier-1-always-active': [],
        'tier-2-on-demand': [],
        'feature-workflow': []
    }

    for tier_name in tiers.keys():
        tier_dir = agents_dir / tier_name
        if not tier_dir.exists():
            continue

        for agent_dir in sorted(tier_dir.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name.startswith('_'):
                continue

            agent_file = agent_dir / 'AGENT.md'
            if not agent_file.exists():
                continue

            meta = extract_frontmatter(agent_file)
            if meta:
                tiers[tier_name].append({
                    'name': meta.get('name', agent_dir.name),
                    'description': meta.get('description', '')[:60]
                })
            else:
                # Extract from content
                content = agent_file.read_text(encoding='utf-8')
                name = agent_dir.name
                desc = ''
                for line in content.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        desc = line.strip()[:60]
                        break
                tiers[tier_name].append({'name': name, 'description': desc})

    return tiers


def generate_commands_table(commands: List[Dict]) -> str:
    """Generate markdown table for commands."""
    lines = [
        "| Command | Description |",
        "|---------|-------------|"
    ]
    for cmd in commands:
        lines.append(f"| `/popkit:{cmd['name']}` | {cmd['description']} |")
    return '\n'.join(lines)


def generate_agents_section(tiers: Dict[str, List[Dict]]) -> str:
    """Generate markdown for agents by tier."""
    tier_names = {
        'tier-1-always-active': 'Tier 1: Always Active',
        'tier-2-on-demand': 'Tier 2: On-Demand',
        'feature-workflow': 'Feature Workflow'
    }

    lines = []
    for tier_key, tier_label in tier_names.items():
        agents = tiers.get(tier_key, [])
        if not agents:
            continue

        lines.append(f"### {tier_label} ({len(agents)} agents)")
        lines.append("")
        lines.append("| Agent | Purpose |")
        lines.append("|-------|---------|")
        for agent in agents:
            lines.append(f"| **{agent['name']}** | {agent['description']} |")
        lines.append("")

    return '\n'.join(lines)


def update_readme(readme_path: Path, section_name: str, content: str, dry_run: bool = False) -> bool:
    """Update a specific AUTO-GEN section in README."""
    start_marker = f"<!-- AUTO-GEN:{section_name} START -->"
    end_marker = f"<!-- AUTO-GEN:{section_name} END -->"

    readme_content = readme_path.read_text(encoding='utf-8')

    pattern = re.compile(
        rf'{re.escape(start_marker)}.*?{re.escape(end_marker)}',
        re.DOTALL
    )

    replacement = f"{start_marker}\n{content}\n{end_marker}"

    if pattern.search(readme_content):
        new_content = pattern.sub(replacement, readme_content)
        if not dry_run:
            readme_path.write_text(new_content, encoding='utf-8')
        return True
    else:
        print(f"Warning: Markers for {section_name} not found in README", file=sys.stderr)
        return False


def main():
    dry_run = '--dry-run' in sys.argv

    # Find paths
    script_dir = Path(__file__).parent
    plugin_dir = script_dir.parent
    readme_path = plugin_dir / 'README.md'
    commands_dir = plugin_dir / 'commands'
    agents_dir = plugin_dir / 'agents'

    if not readme_path.exists():
        print(f"Error: README not found at {readme_path}", file=sys.stderr)
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Syncing README...")

    # Generate commands section
    if commands_dir.exists():
        commands = get_commands(commands_dir)
        commands_table = generate_commands_table(commands)
        if update_readme(readme_path, 'COMMANDS', commands_table, dry_run):
            print(f"  [OK] Updated COMMANDS ({len(commands)} commands)")

    # Generate agents section
    if agents_dir.exists():
        tiers = get_agents(agents_dir)
        agents_content = generate_agents_section(tiers)
        total_agents = sum(len(agents) for agents in tiers.values())
        if update_readme(readme_path, 'AGENTS', agents_content, dry_run):
            print(f"  [OK] Updated AGENTS ({total_agents} agents)")

    print("Done!")


if __name__ == '__main__':
    main()
