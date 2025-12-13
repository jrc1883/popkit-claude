#!/usr/bin/env python3
"""
Content Chunking Script.

Discover, chunk, and prepare project content for embedding.

Usage:
    python chunk_content.py [--mode MODE] [--type TYPE] [--project PATH]

Modes:
    discover - Find all embeddable content
    chunk    - Split content into embedding-friendly chunks
    embed    - Compute embeddings (requires VOYAGE_API_KEY)
    status   - Show embedding status

Output:
    JSON object with discovered/chunked/embedded content
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def get_project_root(path: Optional[str] = None) -> Path:
    """Get project root directory."""
    if path:
        return Path(path).resolve()
    return Path.cwd()


def discover_content(project_root: Path, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover all embeddable content in the project."""
    items = []

    # Content type patterns
    patterns = {
        "skill": [
            (".claude/skills", "*/SKILL.md", "project-skill"),
            (".generated/skills", "*/SKILL.md", "generated-skill"),
        ],
        "agent": [
            (".claude/agents", "*/AGENT.md", "project-agent"),
            (".generated/agents", "*/AGENT.md", "generated-agent"),
        ],
        "command": [
            (".claude/commands", "*.md", "project-command"),
        ],
    }

    # Filter by type if specified
    if content_type:
        patterns = {k: v for k, v in patterns.items() if k == content_type}

    for category, locations in patterns.items():
        for base_dir, pattern, source_type in locations:
            search_path = project_root / base_dir

            if not search_path.exists():
                continue

            for file_path in search_path.glob(pattern):
                if file_path.is_file():
                    content = file_path.read_text()
                    metadata = parse_frontmatter(content)

                    # Generate item ID
                    if pattern == "*/SKILL.md" or pattern == "*/AGENT.md":
                        item_id = file_path.parent.name
                    else:
                        item_id = file_path.stem

                    items.append({
                        "id": f"{source_type}:{item_id}",
                        "type": category,
                        "source_type": source_type,
                        "path": str(file_path.relative_to(project_root)),
                        "name": metadata.get("name", item_id),
                        "description": metadata.get("description", ""),
                        "content_hash": compute_hash(content),
                        "size_bytes": len(content.encode('utf-8'))
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
                    value = value.strip().strip('"\'')
                    metadata[key] = value

    return metadata


def compute_hash(content: str) -> str:
    """Compute content hash for change detection."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def chunk_content(content: str, item_type: str) -> List[Dict[str, Any]]:
    """Split content into embedding-friendly chunks."""
    chunks = []

    # Parse frontmatter
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    # Extract sections
    sections = []
    current_section = {"title": "Overview", "content": [], "level": 0}

    for line in body.split('\n'):
        # Check for headers
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line)

        if header_match:
            # Save current section if it has content
            if current_section["content"]:
                sections.append(current_section)

            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_section = {"title": title, "content": [], "level": level}
        else:
            current_section["content"].append(line)

    # Save last section
    if current_section["content"]:
        sections.append(current_section)

    # Convert sections to chunks
    for i, section in enumerate(sections):
        section_content = '\n'.join(section["content"]).strip()

        if not section_content:
            continue

        # Skip very short sections
        if len(section_content) < 20:
            continue

        chunks.append({
            "chunk_id": f"section-{i}",
            "title": section["title"],
            "level": section["level"],
            "content": section_content[:2000],  # Limit chunk size
            "word_count": len(section_content.split())
        })

    return chunks


def generate_embedding_description(item: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
    """Generate an embedding-friendly description for an item."""
    parts = []

    # Start with name and description
    parts.append(f"Name: {item['name']}")
    if item.get('description'):
        parts.append(f"Description: {item['description']}")

    # Add type context
    type_context = {
        "skill": "Claude Code skill for specialized tasks",
        "agent": "Claude Code agent for automated workflows",
        "command": "Slash command for quick actions"
    }
    if item['type'] in type_context:
        parts.append(f"Type: {type_context[item['type']]}")

    # Add key sections
    for chunk in chunks[:3]:  # First 3 chunks
        if chunk["title"] not in ["Template Variables", "Metadata"]:
            parts.append(f"{chunk['title']}: {chunk['content'][:200]}")

    return ' | '.join(parts)


def check_embedding_status(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check embedding status for discovered items."""
    # This would integrate with the actual embedding store
    # For now, we simulate by checking for an embeddings file

    home = Path(os.path.expanduser("~"))
    embed_db = home / ".claude" / "embeddings" / "embeddings.db"

    status = {
        "total_items": len(items),
        "embedded_items": 0,
        "stale_items": 0,
        "missing_items": 0,
        "api_available": bool(os.environ.get("VOYAGE_API_KEY")),
        "store_exists": embed_db.exists(),
        "by_type": {}
    }

    # Group by type
    for item in items:
        item_type = item["type"]
        if item_type not in status["by_type"]:
            status["by_type"][item_type] = {
                "total": 0,
                "embedded": 0,
                "missing": 0
            }
        status["by_type"][item_type]["total"] += 1
        status["by_type"][item_type]["missing"] += 1
        status["missing_items"] += 1

    return status


def prepare_for_embedding(items: List[Dict[str, Any]], project_root: Path) -> List[Dict[str, Any]]:
    """Prepare items for embedding by chunking and generating descriptions."""
    prepared = []

    for item in items:
        file_path = project_root / item["path"]

        if not file_path.exists():
            continue

        content = file_path.read_text()
        chunks = chunk_content(content, item["type"])
        description = generate_embedding_description(item, chunks)

        prepared.append({
            **item,
            "chunks": chunks,
            "embedding_description": description,
            "chunk_count": len(chunks)
        })

    return prepared


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Chunk content for embedding")
    parser.add_argument("--mode", choices=["discover", "chunk", "embed", "status"],
                        default="discover", help="Operation mode")
    parser.add_argument("--type", choices=["skill", "agent", "command"],
                        help="Filter by content type")
    parser.add_argument("--project", help="Project root path")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    project_root = get_project_root(args.project)

    result = {
        "operation": f"chunk_content_{args.mode}",
        "project_root": str(project_root),
        "timestamp": datetime.now().isoformat()
    }

    if args.mode == "discover":
        items = discover_content(project_root, args.type)
        result["items"] = items
        result["total_items"] = len(items)

        # Group by type
        by_type = {}
        for item in items:
            t = item["type"]
            by_type[t] = by_type.get(t, 0) + 1
        result["by_type"] = by_type

    elif args.mode == "chunk":
        items = discover_content(project_root, args.type)
        prepared = prepare_for_embedding(items, project_root)
        result["items"] = prepared
        result["total_items"] = len(prepared)
        result["total_chunks"] = sum(item["chunk_count"] for item in prepared)

    elif args.mode == "status":
        items = discover_content(project_root, args.type)
        result["status"] = check_embedding_status(items)
        result["items_found"] = len(items)

    elif args.mode == "embed":
        items = discover_content(project_root, args.type)
        prepared = prepare_for_embedding(items, project_root)

        if not os.environ.get("VOYAGE_API_KEY"):
            result["success"] = False
            result["error"] = "VOYAGE_API_KEY not set"
            result["items_to_embed"] = len(prepared)
        else:
            # Would call actual embedding API here
            result["items_prepared"] = len(prepared)
            result["note"] = "Actual embedding requires voyage_client integration"
            result["success"] = True

    result["success"] = result.get("success", True)

    output = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(json.dumps({
            "operation": f"chunk_content_{args.mode}",
            "output_file": args.output,
            "success": True
        }, indent=2))
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
