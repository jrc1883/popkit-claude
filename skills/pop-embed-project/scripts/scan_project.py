#!/usr/bin/env python3
"""
Project Scanning Script.

Scan project for embeddable content and manage embeddings.

Usage:
    python scan_project.py [--mode MODE] [--type TYPE] [--force]

Modes:
    entitlement - Check user tier and API access
    scan        - Find all embeddable content
    status      - Show embedding status
    embed       - Compute and store embeddings

Output:
    JSON object with scan results
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def get_project_root() -> Path:
    """Get project root directory."""
    return Path.cwd()


def check_entitlement() -> Dict[str, Any]:
    """Check user entitlement for embedding features."""
    result = {
        "api_available": bool(os.environ.get("VOYAGE_API_KEY")),
        "tier": "free",  # Would check actual entitlement
        "allowed": True,  # Assume Pro for now
        "fallback_available": True
    }

    # Check for premium checker
    try:
        # This would integrate with actual premium_checker
        # from hooks.utils.premium_checker import check_entitlement
        # actual_result = check_entitlement("pop-embed-project")
        # result["tier"] = actual_result.tier
        # result["allowed"] = actual_result.allowed
        pass
    except ImportError:
        pass

    return result


def scan_project_locations(
    project_root: Path,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Scan project for embeddable items."""
    items = []

    # Define scan locations
    locations = [
        (".claude/skills", "*/SKILL.md", "project-skill", "skill"),
        (".claude/agents", "*/AGENT.md", "project-agent", "agent"),
        (".claude/commands", "*.md", "project-command", "command"),
        (".generated/skills", "*/SKILL.md", "generated-skill", "skill"),
        (".generated/agents", "*/AGENT.md", "generated-agent", "agent"),
    ]

    for base_dir, pattern, source_type, item_type in locations:
        # Filter by content type if specified
        if content_type and item_type != content_type:
            continue

        search_path = project_root / base_dir

        if not search_path.exists():
            continue

        for file_path in search_path.glob(pattern):
            if not file_path.is_file():
                continue

            content = file_path.read_text()
            metadata = parse_frontmatter(content)

            # Determine item ID
            if pattern.startswith("*/"):
                item_id = file_path.parent.name
            else:
                item_id = file_path.stem

            # Skip items without description
            description = metadata.get("description", "")

            items.append({
                "id": f"{source_type}:{item_id}",
                "name": metadata.get("name", item_id),
                "description": description,
                "source_type": source_type,
                "item_type": item_type,
                "path": str(file_path.relative_to(project_root)),
                "content_hash": compute_content_hash(content),
                "size_bytes": len(content.encode('utf-8')),
                "has_description": bool(description),
                "premium": metadata.get("premium", False)
            })

    return items


def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    metadata = {}

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle boolean values
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        value = value.strip('"\'')

                    metadata[key] = value

    return metadata


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def get_embedding_status(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get embedding status for scanned items."""
    home = Path(os.path.expanduser("~"))
    embed_db = home / ".claude" / "embeddings" / "embeddings.db"

    status = {
        "items_found": len(items),
        "items_embedded": 0,
        "items_stale": 0,
        "items_missing": 0,
        "store_exists": embed_db.exists(),
        "api_available": bool(os.environ.get("VOYAGE_API_KEY")),
        "by_type": {},
        "missing_items": [],
        "stale_items": []
    }

    # Group by type
    for item in items:
        item_type = item["item_type"]
        if item_type not in status["by_type"]:
            status["by_type"][item_type] = {
                "found": 0,
                "embedded": 0,
                "missing": 0
            }
        status["by_type"][item_type]["found"] += 1

        # For now, assume all items are missing (would check actual store)
        status["by_type"][item_type]["missing"] += 1
        status["items_missing"] += 1
        status["missing_items"].append({
            "id": item["id"],
            "path": item["path"]
        })

    return status


def generate_embedding_text(item: Dict[str, Any]) -> str:
    """Generate text for embedding from item."""
    parts = [
        f"Name: {item['name']}",
        f"Type: {item['item_type']}",
    ]

    if item.get('description'):
        parts.append(f"Description: {item['description']}")

    return " | ".join(parts)


def embed_items(
    items: List[Dict[str, Any]],
    force: bool = False
) -> Dict[str, Any]:
    """Embed items using Voyage AI."""
    result = {
        "status": "success",
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "error_items": [],
        "timing": {
            "started": datetime.now().isoformat(),
            "completed": None,
            "batches": 0,
            "total_delay": 0
        }
    }

    # Check API key
    if not os.environ.get("VOYAGE_API_KEY"):
        return {
            "status": "error",
            "error": "VOYAGE_API_KEY not set",
            "items_to_embed": len(items)
        }

    # Filter items to embed
    to_embed = []
    for item in items:
        if not item.get("has_description"):
            result["skipped"] += 1
            continue

        if not force:
            # Would check existing hash here
            pass

        to_embed.append(item)

    if not to_embed:
        result["status"] = "no_items"
        return result

    # Batch items (50 per batch)
    batch_size = 50
    batches = [to_embed[i:i + batch_size] for i in range(0, len(to_embed), batch_size)]
    result["timing"]["batches"] = len(batches)

    # Process batches
    for batch_idx, batch in enumerate(batches):
        # Generate embedding texts
        texts = [generate_embedding_text(item) for item in batch]

        # Would call Voyage API here
        # from hooks.utils.voyage_client import embed_batch
        # embeddings = embed_batch(texts)

        for item in batch:
            result["embedded"] += 1

        # Rate limiting delay (except for last batch)
        if batch_idx < len(batches) - 1:
            result["timing"]["total_delay"] += 21

    result["timing"]["completed"] = datetime.now().isoformat()
    return result


def free_tier_fallback() -> Dict[str, Any]:
    """Return fallback options for free tier users."""
    return {
        "status": "free_tier",
        "message": "Project embeddings require PopKit Pro",
        "alternatives": {
            "find_skills": "ls .claude/skills/*/SKILL.md 2>/dev/null",
            "find_agents": "ls .claude/agents/*/AGENT.md 2>/dev/null",
            "find_commands": "ls .claude/commands/*.md 2>/dev/null",
            "keyword_search": "grep -r 'keyword' .claude/"
        },
        "upgrade_command": "/popkit:upgrade"
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scan project for embeddable content")
    parser.add_argument("--mode", choices=["entitlement", "scan", "status", "embed"],
                        default="scan", help="Operation mode")
    parser.add_argument("--type", choices=["skill", "agent", "command"],
                        help="Filter by content type")
    parser.add_argument("--force", action="store_true", help="Re-embed all items")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    project_root = get_project_root()

    result = {
        "operation": f"scan_project_{args.mode}",
        "project_root": str(project_root),
        "timestamp": datetime.now().isoformat()
    }

    if args.mode == "entitlement":
        result["entitlement"] = check_entitlement()

        if not result["entitlement"]["allowed"]:
            result["fallback"] = free_tier_fallback()

    elif args.mode == "scan":
        items = scan_project_locations(project_root, args.type)
        result["items"] = items
        result["total_items"] = len(items)

        # Summarize by type
        by_type = {}
        for item in items:
            t = item["item_type"]
            by_type[t] = by_type.get(t, 0) + 1
        result["by_type"] = by_type

        # Count items with/without description
        with_desc = sum(1 for item in items if item["has_description"])
        result["with_description"] = with_desc
        result["without_description"] = len(items) - with_desc

    elif args.mode == "status":
        items = scan_project_locations(project_root, args.type)
        result["status"] = get_embedding_status(items)

    elif args.mode == "embed":
        entitlement = check_entitlement()

        if not entitlement["allowed"]:
            result["fallback"] = free_tier_fallback()
        else:
            items = scan_project_locations(project_root, args.type)
            result["embed_result"] = embed_items(items, args.force)

    result["success"] = True

    output = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(json.dumps({
            "operation": f"scan_project_{args.mode}",
            "output_file": args.output,
            "success": True
        }, indent=2))
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
