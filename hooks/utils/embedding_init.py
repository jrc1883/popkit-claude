#!/usr/bin/env python3
"""
Embedding Initialization

Pre-computes embeddings for skills, agents, and commands.
Run during plugin initialization or on-demand.

Part of PopKit Issue #19 (Embeddings Enhancement).
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from voyage_client import VoyageClient, is_available
from embedding_store import EmbeddingStore, EmbeddingRecord

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get popkit root (parent of hooks/)
POPKIT_ROOT = Path(__file__).parent.parent.parent


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_yaml_frontmatter(content: str) -> Dict[str, str]:
    """Extract YAML frontmatter from markdown file."""
    if not content.startswith("---"):
        return {}

    end = content.find("---", 3)
    if end < 0:
        return {}

    frontmatter = content[3:end].strip()
    result = {}

    for line in frontmatter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            result[key] = value

    return result


def extract_skill_descriptions() -> List[Dict[str, Any]]:
    """
    Extract descriptions from all SKILL.md files.

    Returns:
        List of skill info dictionaries
    """
    skills = []
    skills_dir = POPKIT_ROOT / "skills"

    if not skills_dir.exists():
        return skills

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter = extract_yaml_frontmatter(content)

            description = frontmatter.get("description", "")
            if not description:
                continue

            skills.append({
                "id": f"skill:{skill_dir.name}",
                "name": skill_dir.name,
                "description": description,
                "source_type": "skill",
                "path": str(skill_file)
            })
        except Exception as e:
            print(f"Warning: Failed to read {skill_file}: {e}")

    return skills


def extract_agent_descriptions() -> List[Dict[str, Any]]:
    """
    Extract descriptions from all AGENT.md files.

    Returns:
        List of agent info dictionaries
    """
    agents = []
    agents_dir = POPKIT_ROOT / "agents"

    if not agents_dir.exists():
        return agents

    tiers = ["tier-1-always-active", "tier-2-on-demand", "feature-workflow"]

    for tier in tiers:
        tier_dir = agents_dir / tier
        if not tier_dir.exists():
            continue

        for agent_dir in tier_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            agent_file = agent_dir / "AGENT.md"
            if not agent_file.exists():
                continue

            try:
                content = agent_file.read_text(encoding="utf-8")
                frontmatter = extract_yaml_frontmatter(content)

                description = frontmatter.get("description", "")
                if not description:
                    continue

                agents.append({
                    "id": f"agent:{agent_dir.name}",
                    "name": agent_dir.name,
                    "description": description,
                    "source_type": "agent",
                    "tier": tier,
                    "path": str(agent_file)
                })
            except Exception as e:
                print(f"Warning: Failed to read {agent_file}: {e}")

    return agents


def extract_command_descriptions() -> List[Dict[str, Any]]:
    """
    Extract descriptions from all command .md files.

    Returns:
        List of command info dictionaries
    """
    commands = []
    commands_dir = POPKIT_ROOT / "commands"

    if not commands_dir.exists():
        return commands

    for cmd_file in commands_dir.glob("*.md"):
        try:
            content = cmd_file.read_text(encoding="utf-8")
            frontmatter = extract_yaml_frontmatter(content)

            description = frontmatter.get("description", "")
            if not description:
                continue

            cmd_name = cmd_file.stem
            commands.append({
                "id": f"command:{cmd_name}",
                "name": cmd_name,
                "description": description,
                "source_type": "command",
                "path": str(cmd_file)
            })
        except Exception as e:
            print(f"Warning: Failed to read {cmd_file}: {e}")

    return commands


# =============================================================================
# EMBEDDING COMPUTATION
# =============================================================================

def compute_and_store_embeddings(
    items: List[Dict[str, Any]],
    client: VoyageClient,
    store: EmbeddingStore,
    batch_size: int = 50
) -> Tuple[int, int]:
    """
    Compute embeddings for items and store them.

    Args:
        items: List of item dictionaries with 'description'
        client: VoyageClient instance
        store: EmbeddingStore instance
        batch_size: Number of items to embed per API call

    Returns:
        Tuple of (success_count, error_count)
    """
    if not items:
        return 0, 0

    success = 0
    errors = 0

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        descriptions = [item["description"] for item in batch]

        try:
            embeddings = client.embed(descriptions, input_type="document")

            for item, embedding in zip(batch, embeddings):
                record = EmbeddingRecord(
                    id=item["id"],
                    content=item["description"],
                    embedding=embedding,
                    source_type=item["source_type"],
                    source_id=item["name"],
                    metadata={
                        k: v for k, v in item.items()
                        if k not in ["id", "description", "source_type", "name"]
                    },
                    created_at=datetime.now().isoformat()
                )
                store.store(record)
                success += 1

        except Exception as e:
            print(f"Error embedding batch {i//batch_size + 1}: {e}")
            errors += len(batch)

    return success, errors


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def initialize_embeddings(
    force: bool = False,
    skills: bool = True,
    agents: bool = True,
    commands: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Initialize embeddings for all PopKit components.

    Args:
        force: Re-compute even if embeddings exist
        skills: Include skills
        agents: Include agents
        commands: Include commands
        verbose: Print progress

    Returns:
        Dictionary with results
    """
    results = {
        "status": "success",
        "skills": {"extracted": 0, "embedded": 0, "errors": 0},
        "agents": {"extracted": 0, "embedded": 0, "errors": 0},
        "commands": {"extracted": 0, "embedded": 0, "errors": 0},
        "total": 0,
        "errors": 0
    }

    # Check API availability
    if not is_available():
        results["status"] = "error"
        results["error"] = "VOYAGE_API_KEY not set"
        return results

    client = VoyageClient()
    store = EmbeddingStore()

    # Check if already initialized
    if not force and store.count() > 0:
        results["status"] = "already_initialized"
        results["existing_count"] = store.count()
        if verbose:
            print(f"Already initialized with {store.count()} embeddings. Use --force to re-compute.")
        return results

    # Clear if forcing
    if force:
        cleared = store.clear()
        if verbose:
            print(f"Cleared {cleared} existing embeddings")

    # Rate limit delay for free tier (3 RPM)
    # Each type makes 1 API call, so we need 21s between calls to stay under limit
    rate_limit_delay = 21

    # Process skills
    if skills:
        if verbose:
            print("\nExtracting skills...")
        skill_items = extract_skill_descriptions()
        results["skills"]["extracted"] = len(skill_items)

        if skill_items:
            if verbose:
                print(f"Embedding {len(skill_items)} skills...")
            success, errors = compute_and_store_embeddings(skill_items, client, store)
            results["skills"]["embedded"] = success
            results["skills"]["errors"] = errors

    # Process agents
    if agents:
        # Wait for rate limit if we just embedded skills
        if skills and results["skills"]["embedded"] > 0:
            if verbose:
                print(f"\nWaiting {rate_limit_delay}s for rate limit...")
            time.sleep(rate_limit_delay)

        if verbose:
            print("\nExtracting agents...")
        agent_items = extract_agent_descriptions()
        results["agents"]["extracted"] = len(agent_items)

        if agent_items:
            if verbose:
                print(f"Embedding {len(agent_items)} agents...")
            success, errors = compute_and_store_embeddings(agent_items, client, store)
            results["agents"]["embedded"] = success
            results["agents"]["errors"] = errors

    # Process commands
    if commands:
        # Wait for rate limit if we just embedded agents
        if agents and results["agents"]["embedded"] > 0:
            if verbose:
                print(f"\nWaiting {rate_limit_delay}s for rate limit...")
            time.sleep(rate_limit_delay)

        if verbose:
            print("\nExtracting commands...")
        command_items = extract_command_descriptions()
        results["commands"]["extracted"] = len(command_items)

        if command_items:
            if verbose:
                print(f"Embedding {len(command_items)} commands...")
            success, errors = compute_and_store_embeddings(command_items, client, store)
            results["commands"]["embedded"] = success
            results["commands"]["errors"] = errors

    # Calculate totals
    results["total"] = (
        results["skills"]["embedded"] +
        results["agents"]["embedded"] +
        results["commands"]["embedded"]
    )
    results["errors"] = (
        results["skills"]["errors"] +
        results["agents"]["errors"] +
        results["commands"]["errors"]
    )

    if verbose:
        print(f"\n{'='*50}")
        print(f"Embedding initialization complete!")
        print(f"  Skills:   {results['skills']['embedded']}/{results['skills']['extracted']}")
        print(f"  Agents:   {results['agents']['embedded']}/{results['agents']['extracted']}")
        print(f"  Commands: {results['commands']['embedded']}/{results['commands']['extracted']}")
        print(f"  Total:    {results['total']} embeddings")
        if results["errors"]:
            print(f"  Errors:   {results['errors']}")

    return results


def get_embedding_status() -> Dict[str, Any]:
    """
    Get current embedding status without making changes.

    Returns:
        Status dictionary
    """
    store = EmbeddingStore()

    return {
        "available": is_available(),
        "stats": store.stats(),
        "has_embeddings": store.count() > 0
    }


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize PopKit embeddings"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-computation of all embeddings"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show current status only"
    )
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="Only process skills"
    )
    parser.add_argument(
        "--agents-only",
        action="store_true",
        help="Only process agents"
    )
    parser.add_argument(
        "--commands-only",
        action="store_true",
        help="Only process commands"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (JSON output only)"
    )

    args = parser.parse_args()

    if args.status:
        status = get_embedding_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)

    # Determine what to process
    if args.skills_only:
        result = initialize_embeddings(
            force=args.force,
            skills=True, agents=False, commands=False,
            verbose=not args.quiet
        )
    elif args.agents_only:
        result = initialize_embeddings(
            force=args.force,
            skills=False, agents=True, commands=False,
            verbose=not args.quiet
        )
    elif args.commands_only:
        result = initialize_embeddings(
            force=args.force,
            skills=False, agents=False, commands=True,
            verbose=not args.quiet
        )
    else:
        result = initialize_embeddings(
            force=args.force,
            verbose=not args.quiet
        )

    if args.quiet:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["status"] in ["success", "already_initialized"] else 1)
