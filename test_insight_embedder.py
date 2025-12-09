#!/usr/bin/env python3
"""Test the insight embedder with cloud API."""

import os
import sys

# Set API key
os.environ["POPKIT_API_KEY"] = "pk_live_8b8fe06d0c565cff0409c2231268aef1bd0a5cf29bd4746d"

# Add power-mode to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "power-mode"))

from insight_embedder import InsightEmbedder

def main():
    print("=" * 50)
    print("Insight Embedder Cloud Test")
    print("=" * 50)

    embedder = InsightEmbedder()

    print(f"\nMode: {embedder.mode}")
    print(f"Available: {embedder.available}")

    if embedder.mode != "cloud":
        print("[WARN] Not using cloud mode!")
        return

    # Test embedding
    print("\n[TEST] Embedding new insight...")
    insight_id, result = embedder.embed_insight(
        content="Database connection pool configured at src/db/pool.ts with max 10 connections",
        from_agent="test-agent",
        insight_type="discovery"
    )

    print(f"  Insight ID: {insight_id}")
    print(f"  Status: {result.get('status')}")
    print(f"  Summary: {result.get('summary')}")

    if result.get("status") == "duplicate":
        print(f"  Duplicate of: {result.get('duplicate', {}).get('id')}")
        print(f"  Similarity: {result.get('duplicate', {}).get('similarity'):.4f}")
    elif result.get("tokens"):
        print(f"  Tokens: {result.get('tokens')}")
        print(f"  Cost: ${result.get('cost', 0):.8f}")

    # Test search
    print("\n[TEST] Searching for auth-related insights...")
    results = embedder.search_relevant(
        context="authentication login jwt oauth security",
        exclude_agent="other-agent",
        limit=5
    )

    print(f"  Found: {len(results)} results")
    for r in results:
        print(f"    - [{r.get('similarity', 0):.3f}] {r.get('id')}: {r.get('summary', 'N/A')}")

    # Get stats
    print("\n[TEST] Getting usage stats...")
    stats = embedder.get_stats()
    print(f"  Mode: {stats.get('mode')}")
    if "usage" in stats:
        usage = stats["usage"]
        today = usage.get('today', {})
        print(f"  Tokens today: {today.get('tokens', 0)}")
        print(f"  Requests today: {today.get('requests', 0)}")
        print(f"  Cost today: ${today.get('cost', 0):.6f}")
        print(f"  Total insights: {usage.get('total_insights', 0)}")

    print("\n" + "=" * 50)
    print("[OK] Cloud embedding test completed!")


if __name__ == "__main__":
    main()
