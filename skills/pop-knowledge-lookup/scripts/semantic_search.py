#!/usr/bin/env python3
"""
Knowledge Semantic Search Script.

Perform semantic and keyword search across cached knowledge sources.

Usage:
    python semantic_search.py QUERY [--mode MODE] [--top-k N]

Modes:
    sources  - Identify relevant sources for a query
    semantic - Vector similarity search (requires embeddings)
    keyword  - Traditional keyword matching
    hybrid   - Combined semantic + keyword search

Output:
    JSON object with search results
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def get_knowledge_dir() -> Path:
    """Get knowledge cache directory."""
    home = Path(os.path.expanduser("~"))
    return home / ".claude" / "config" / "knowledge"


def list_sources() -> List[Dict[str, Any]]:
    """List available knowledge sources."""
    sources_file = get_knowledge_dir() / "sources.json"
    if sources_file.exists():
        return json.loads(sources_file.read_text())
    return []


def load_cached_content() -> Dict[str, str]:
    """Load all cached knowledge content."""
    content_dir = get_knowledge_dir() / "content"
    cached = {}

    if content_dir.exists():
        for file_path in content_dir.glob("*.md"):
            source_id = file_path.stem
            cached[source_id] = file_path.read_text()

    return cached


def tokenize(text: str) -> Set[str]:
    """Tokenize text into word set for keyword matching."""
    words = re.findall(r'\b\w+\b', text.lower())
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'must', 'can',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'as', 'into', 'through', 'during', 'before', 'after', 'above',
                  'below', 'between', 'under', 'again', 'further', 'then', 'once',
                  'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                  'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
                  'just', 'also', 'now', 'here', 'there', 'when', 'where', 'why',
                  'how', 'all', 'each', 'every', 'some', 'any', 'few', 'more',
                  'most', 'other', 'no', 'this', 'that', 'these', 'those', 'it'}
    return set(words) - stop_words


def keyword_search(query: str, content: Dict[str, str], top_k: int = 5) -> List[Dict[str, Any]]:
    """Perform keyword-based search."""
    query_tokens = tokenize(query)
    results = []

    for source_id, text in content.items():
        # Search for matches
        matches = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_tokens = tokenize(line)
            overlap = query_tokens & line_tokens

            if overlap:
                # Calculate relevance score
                score = len(overlap) / len(query_tokens) if query_tokens else 0

                # Get context (surrounding lines)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = '\n'.join(lines[start:end])

                matches.append({
                    "line": i + 1,
                    "score": score,
                    "matched_terms": list(overlap),
                    "context": context[:500]
                })

        if matches:
            # Sort matches by score and take top ones
            matches.sort(key=lambda x: x["score"], reverse=True)
            best_score = max(m["score"] for m in matches)

            results.append({
                "source_id": source_id,
                "score": best_score,
                "match_count": len(matches),
                "best_matches": matches[:3]
            })

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def identify_sources(query: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify which sources are most relevant for a query."""
    query_lower = query.lower()
    relevant = []

    # Mapping of query patterns to source relevance
    source_patterns = {
        "claude-code": ["claude code", "claude", "anthropic", "claude code docs"],
        "hooks": ["hook", "pre-tool", "post-tool", "stop-sequence"],
        "engineering": ["best practice", "engineering", "blog", "pattern"],
        "mcp": ["mcp", "model context protocol", "server", "tool"],
        "commands": ["command", "slash command", "/"],
        "skills": ["skill", "workflow", "agent"]
    }

    for source in sources:
        source_id = source.get("id", source.get("source_id", ""))
        source_name = source.get("name", source_id)
        relevance = 0.0
        reasons = []

        # Check if query keywords match source patterns
        for pattern_key, keywords in source_patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    if pattern_key in source_id.lower() or pattern_key in source_name.lower():
                        relevance += 0.3
                        reasons.append(f"Query matches '{keyword}' → source '{pattern_key}'")

        # Check source description
        description = source.get("description", "")
        if description:
            desc_tokens = tokenize(description)
            query_tokens = tokenize(query)
            overlap = desc_tokens & query_tokens
            if overlap:
                relevance += 0.2 * len(overlap)
                reasons.append(f"Description matches: {list(overlap)[:3]}")

        if relevance > 0:
            relevant.append({
                "source_id": source_id,
                "name": source_name,
                "relevance": min(relevance, 1.0),
                "reasons": reasons
            })

    # Sort by relevance
    relevant.sort(key=lambda x: x["relevance"], reverse=True)
    return relevant


def semantic_search(query: str, content: Dict[str, str], top_k: int = 5) -> List[Dict[str, Any]]:
    """Perform semantic search using embeddings (if available)."""
    results = []

    try:
        # Try to import embedding utilities
        # This would integrate with the actual embedding store
        # For now, we simulate with keyword fallback

        # Check for embedding store availability
        embed_store = get_knowledge_dir() / "embeddings"
        if not embed_store.exists():
            return [{
                "status": "unavailable",
                "reason": "Embeddings not initialized. Run: python hooks/utils/embedding_init.py",
                "fallback": "keyword_search"
            }]

        # Would perform actual vector search here
        # This is a placeholder for the semantic search implementation
        # In production, this would:
        # 1. Get query embedding via Voyage AI
        # 2. Search vector store for similar chunks
        # 3. Return results with similarity scores

        results.append({
            "status": "simulated",
            "note": "Semantic search would use Voyage AI embeddings",
            "recommendation": "Set VOYAGE_API_KEY and run embedding initialization"
        })

    except Exception as e:
        results.append({
            "status": "error",
            "error": str(e),
            "fallback": "keyword_search"
        })

    return results


def hybrid_search(
    query: str,
    content: Dict[str, str],
    top_k: int = 5,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """Perform hybrid search combining semantic and keyword results."""
    keyword_results = keyword_search(query, content, top_k * 2)
    semantic_results = semantic_search(query, content, top_k * 2)

    # Check if semantic search is available
    semantic_available = (
        semantic_results and
        semantic_results[0].get("status") != "unavailable" and
        semantic_results[0].get("status") != "error"
    )

    if not semantic_available:
        # Fall back to keyword only
        return {
            "strategy": "keyword_fallback",
            "reason": semantic_results[0].get("reason", "Semantic search unavailable"),
            "results": keyword_results[:top_k]
        }

    # Merge results using reciprocal rank fusion
    scores = {}
    k = 60  # RRF constant

    for rank, result in enumerate(keyword_results):
        source_id = result["source_id"]
        scores[source_id] = scores.get(source_id, 0) + keyword_weight / (k + rank)

    # Would add semantic results here if available

    # Sort by combined score
    merged = []
    for source_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        merged.append({
            "source_id": source_id,
            "combined_score": round(score, 4),
            "in_keyword_results": source_id in [r["source_id"] for r in keyword_results],
            "in_semantic_results": False  # Would be True if semantic search worked
        })

    return {
        "strategy": "hybrid",
        "semantic_available": semantic_available,
        "results": merged[:top_k]
    }


def check_freshness() -> Dict[str, Any]:
    """Check freshness of cached knowledge."""
    cache_db = get_knowledge_dir() / "cache.db"
    content_dir = get_knowledge_dir() / "content"

    status = {
        "cache_db_exists": cache_db.exists(),
        "content_dir_exists": content_dir.exists(),
        "sources": []
    }

    if content_dir.exists():
        for file_path in content_dir.glob("*.md"):
            stat = file_path.stat()
            age_hours = (datetime.now().timestamp() - stat.st_mtime) / 3600

            status["sources"].append({
                "source_id": file_path.stem,
                "size_bytes": stat.st_size,
                "age_hours": round(age_hours, 1),
                "is_stale": age_hours > 24  # 24-hour TTL
            })

    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Knowledge semantic search")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--mode", choices=["sources", "semantic", "keyword", "hybrid", "status"],
                        default="hybrid", help="Search mode")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--semantic-weight", type=float, default=0.7, help="Semantic score weight")
    parser.add_argument("--keyword-weight", type=float, default=0.3, help="Keyword score weight")
    args = parser.parse_args()

    result = {
        "operation": "knowledge_search",
        "mode": args.mode,
        "timestamp": datetime.now().isoformat()
    }

    if args.mode == "status":
        result["freshness"] = check_freshness()
        print(json.dumps(result, indent=2))
        return 0

    if not args.query:
        print(json.dumps({
            "success": False,
            "error": "Query required for search modes"
        }, indent=2))
        return 1

    result["query"] = args.query

    sources = list_sources()
    content = load_cached_content()

    if args.mode == "sources":
        result["relevant_sources"] = identify_sources(args.query, sources)
    elif args.mode == "semantic":
        result["results"] = semantic_search(args.query, content, args.top_k)
    elif args.mode == "keyword":
        result["results"] = keyword_search(args.query, content, args.top_k)
    elif args.mode == "hybrid":
        hybrid_result = hybrid_search(
            args.query, content, args.top_k,
            args.semantic_weight, args.keyword_weight
        )
        result.update(hybrid_result)

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
