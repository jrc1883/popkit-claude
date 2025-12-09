#!/usr/bin/env python3
"""
Project-Local Embedding Management

Scans project directories for skills, agents, and commands.
Handles incremental updates and auto-embedding after generation.

Part of PopKit Issue #46 (Project Embeddings).
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add utils to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from embedding_store import EmbeddingStore, EmbeddingRecord
from voyage_client import VoyageClient, is_available as voyage_available

# =============================================================================
# CONFIGURATION
# =============================================================================

# Project item paths to scan (relative to project root)
PROJECT_PATHS = {
    "project-skill": [".claude/skills/*/SKILL.md"],
    "project-agent": [".claude/agents/*/AGENT.md"],
    "project-command": [".claude/commands/*.md"],
    "generated-skill": [".generated/skills/*/SKILL.md"],
    "generated-agent": [".generated/agents/*/AGENT.md"],
}

# Rate limiting for Voyage free tier (3 RPM)
RATE_LIMIT_DELAY = 21  # seconds between batches
BATCH_SIZE = 50  # items per API call


# =============================================================================
# PROJECT DETECTION
# =============================================================================

def get_project_root(start_path: Optional[str] = None) -> Optional[str]:
    """
    Detect project root by looking for .claude/ directory.

    Args:
        start_path: Starting path (defaults to cwd)

    Returns:
        Project root path or None
    """
    current = Path(start_path) if start_path else Path.cwd()

    # Walk up the directory tree
    for path in [current] + list(current.parents):
        if (path / ".claude").is_dir():
            return str(path)
        if (path / ".git").is_dir():
            # Found git root but no .claude, use this
            return str(path)

    return None


# =============================================================================
# YAML FRONTMATTER EXTRACTION
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


# =============================================================================
# SCANNING FUNCTIONS
# =============================================================================

def scan_project_items(project_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scan project for embeddable items.

    Looks in .claude/ and .generated/ directories for:
    - Skills (SKILL.md files with description frontmatter)
    - Agents (AGENT.md files with description frontmatter)
    - Commands (.md files with description frontmatter)

    Args:
        project_root: Project directory path (auto-detected if None)

    Returns:
        List of item dictionaries with:
        - id: Unique identifier (e.g., "project-skill:myproject:auth")
        - name: Item name (directory or file name)
        - description: Content to embed (from frontmatter)
        - source_type: One of project-skill, project-agent, etc.
        - path: Absolute file path
        - project_path: Project root path
    """
    root = Path(project_root) if project_root else Path(get_project_root() or ".")

    if not root.exists():
        return []

    items = []
    project_name = root.name

    for source_type, patterns in PROJECT_PATHS.items():
        for pattern in patterns:
            # Resolve glob pattern
            for file_path in root.glob(pattern):
                if not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    frontmatter = extract_yaml_frontmatter(content)

                    description = frontmatter.get("description", "")
                    if not description:
                        continue  # Skip items without description

                    # Determine item name
                    if "SKILL.md" in file_path.name or "AGENT.md" in file_path.name:
                        name = file_path.parent.name
                    else:
                        name = file_path.stem

                    item_id = f"{source_type}:{project_name}:{name}"

                    items.append({
                        "id": item_id,
                        "name": name,
                        "description": description,
                        "source_type": source_type,
                        "path": str(file_path),
                        "project_path": str(root)
                    })

                except Exception as e:
                    print(f"Warning: Failed to read {file_path}: {e}")

    return items


# =============================================================================
# EMBEDDING FUNCTIONS
# =============================================================================

def embed_project_items(
    project_root: Optional[str] = None,
    force: bool = False,
    source_types: Optional[List[str]] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Embed project items incrementally.

    Only embeds items that have changed since last embedding,
    unless force=True is specified.

    Args:
        project_root: Project directory path (auto-detected if None)
        force: Re-embed even if content unchanged
        source_types: Filter to specific types (e.g., ["project-skill"])
        verbose: Print progress messages

    Returns:
        Results dictionary:
        {
            "status": "success" | "error" | "no_items",
            "embedded": int,
            "skipped": int,
            "errors": int,
            "by_type": {source_type: count, ...}
        }
    """
    results = {
        "status": "success",
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "by_type": {}
    }

    # Check API availability
    if not voyage_available():
        results["status"] = "error"
        results["error"] = "VOYAGE_API_KEY not set"
        return results

    # Get project root
    root = project_root or get_project_root()
    if not root:
        results["status"] = "error"
        results["error"] = "Could not detect project root"
        return results

    # Scan for items
    if verbose:
        print(f"Scanning project: {root}")

    items = scan_project_items(root)

    # Filter by source types if specified
    if source_types:
        items = [i for i in items if i["source_type"] in source_types]

    if not items:
        results["status"] = "no_items"
        if verbose:
            print("No embeddable items found")
        return results

    if verbose:
        print(f"Found {len(items)} items")

    # Initialize store and client
    store = EmbeddingStore()
    client = VoyageClient()

    # Separate items that need embedding
    items_to_embed = []

    for item in items:
        if force or store.needs_update(item["id"], item["description"]):
            items_to_embed.append(item)
        else:
            results["skipped"] += 1
            source_type = item["source_type"]
            if source_type not in results["by_type"]:
                results["by_type"][source_type] = {"embedded": 0, "skipped": 0}
            results["by_type"][source_type]["skipped"] = \
                results["by_type"].get(source_type, {}).get("skipped", 0) + 1

    if verbose:
        print(f"Items to embed: {len(items_to_embed)}, skipped: {results['skipped']}")

    if not items_to_embed:
        return results

    # Embed in batches with rate limiting
    for i in range(0, len(items_to_embed), BATCH_SIZE):
        batch = items_to_embed[i:i + BATCH_SIZE]

        # Rate limit between batches
        if i > 0:
            if verbose:
                print(f"Waiting {RATE_LIMIT_DELAY}s for rate limit...")
            time.sleep(RATE_LIMIT_DELAY)

        try:
            descriptions = [item["description"] for item in batch]
            embeddings = client.embed(descriptions, input_type="document")

            for item, embedding in zip(batch, embeddings):
                record = EmbeddingRecord(
                    id=item["id"],
                    content=item["description"],
                    embedding=embedding,
                    source_type=item["source_type"],
                    source_id=item["name"],
                    metadata={"path": item["path"]},
                    created_at=datetime.now().isoformat(),
                    project_path=item["project_path"]
                )
                store.store(record)
                results["embedded"] += 1

                source_type = item["source_type"]
                if source_type not in results["by_type"]:
                    results["by_type"][source_type] = {"embedded": 0, "skipped": 0}
                results["by_type"][source_type]["embedded"] = \
                    results["by_type"].get(source_type, {}).get("embedded", 0) + 1

        except Exception as e:
            print(f"Error embedding batch: {e}")
            results["errors"] += len(batch)

    if verbose:
        print(f"\nEmbedding complete!")
        print(f"  Embedded: {results['embedded']}")
        print(f"  Skipped: {results['skipped']}")
        if results["errors"]:
            print(f"  Errors: {results['errors']}")

    return results


def auto_embed_item(file_path: str, source_type: str) -> bool:
    """
    Auto-embed a single item after generation.

    Called by generators after creating new items.
    Does not apply rate limiting (assumes single item).

    Args:
        file_path: Path to the generated file
        source_type: One of project-skill, project-agent, etc.

    Returns:
        True if embedding succeeded, False otherwise
    """
    if not voyage_available():
        return False

    path = Path(file_path)
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
        frontmatter = extract_yaml_frontmatter(content)

        description = frontmatter.get("description", "")
        if not description:
            return False

        # Get project root
        project_root = get_project_root(str(path.parent))
        if not project_root:
            project_root = str(path.parent)

        project_name = Path(project_root).name

        # Determine item name
        if "SKILL.md" in path.name or "AGENT.md" in path.name:
            name = path.parent.name
        else:
            name = path.stem

        item_id = f"{source_type}:{project_name}:{name}"

        # Embed
        client = VoyageClient()
        store = EmbeddingStore()

        embedding = client.embed_single(description, input_type="document")

        record = EmbeddingRecord(
            id=item_id,
            content=description,
            embedding=embedding,
            source_type=source_type,
            source_id=name,
            metadata={"path": str(path)},
            created_at=datetime.now().isoformat(),
            project_path=project_root
        )
        store.store(record)

        return True

    except Exception as e:
        print(f"Error auto-embedding {file_path}: {e}")
        return False


# =============================================================================
# STATUS FUNCTIONS
# =============================================================================

def get_project_embedding_status(project_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Get embedding status for current project.

    Compares items found in project directories with what's
    already embedded in the database.

    Args:
        project_root: Project directory path (auto-detected if None)

    Returns:
        Status dictionary:
        {
            "project_path": "/path/to/project",
            "items_found": 15,
            "items_embedded": 12,
            "items_stale": 2,
            "items_missing": 3,
            "by_type": {
                "project-skill": {"found": 5, "embedded": 4, "stale": 0, "missing": 1},
                ...
            },
            "api_available": True
        }
    """
    root = project_root or get_project_root()

    status = {
        "project_path": root,
        "items_found": 0,
        "items_embedded": 0,
        "items_stale": 0,
        "items_missing": 0,
        "by_type": {},
        "api_available": voyage_available()
    }

    if not root:
        status["error"] = "Could not detect project root"
        return status

    # Scan for items
    items = scan_project_items(root)
    status["items_found"] = len(items)

    # Check each item's status
    store = EmbeddingStore()

    for item in items:
        source_type = item["source_type"]

        if source_type not in status["by_type"]:
            status["by_type"][source_type] = {
                "found": 0,
                "embedded": 0,
                "stale": 0,
                "missing": 0
            }

        status["by_type"][source_type]["found"] += 1

        # Check if embedded
        existing = store.get(item["id"])

        if existing:
            status["items_embedded"] += 1
            status["by_type"][source_type]["embedded"] += 1

            # Check if stale (content changed)
            if store.needs_update(item["id"], item["description"]):
                status["items_stale"] += 1
                status["by_type"][source_type]["stale"] += 1
        else:
            status["items_missing"] += 1
            status["by_type"][source_type]["missing"] += 1

    return status


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Manage project-local embeddings"
    )
    parser.add_argument(
        "command",
        choices=["scan", "embed", "status"],
        help="Command to run"
    )
    parser.add_argument(
        "--project", "-p",
        help="Project root path (auto-detected if not specified)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-embedding of all items"
    )
    parser.add_argument(
        "--type", "-t",
        action="append",
        dest="types",
        help="Filter to specific source types"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (minimal output)"
    )

    args = parser.parse_args()

    if args.command == "scan":
        items = scan_project_items(args.project)

        if args.json:
            print(json.dumps(items, indent=2))
        else:
            print(f"Found {len(items)} items:\n")
            for item in items:
                print(f"  [{item['source_type']}] {item['name']}")
                print(f"    {item['description'][:60]}...")
                print()

    elif args.command == "embed":
        result = embed_project_items(
            project_root=args.project,
            force=args.force,
            source_types=args.types,
            verbose=not args.quiet
        )

        if args.json or args.quiet:
            print(json.dumps(result, indent=2))

    elif args.command == "status":
        status = get_project_embedding_status(args.project)

        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"Project: {status['project_path']}")
            print(f"API Available: {status['api_available']}")
            print()
            print(f"Items Found:    {status['items_found']}")
            print(f"Items Embedded: {status['items_embedded']}")
            print(f"Items Stale:    {status['items_stale']}")
            print(f"Items Missing:  {status['items_missing']}")

            if status["by_type"]:
                print("\nBy Type:")
                for stype, counts in status["by_type"].items():
                    print(f"  {stype}: {counts['embedded']}/{counts['found']}")
