#!/usr/bin/env python3
"""
Generate embeddings for all PopKit agents.

Stores embeddings in:
- SQLite (local fallback)
- Upstash Vector (cloud, Pro tier)
"""

import json
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "utils"))

from embedding_store import EmbeddingStore, EmbeddingRecord
from voyage_client import embed as get_voyage_embeddings


def load_agent_descriptions():
    """Load all agent descriptions from config and agent files."""
    config_path = Path(__file__).parent.parent / "agents" / "config.json"

    with open(config_path, 'r') as f:
        config = json.load(f)

    agents = {}

    # Tier 1: Always-active agents
    tier1_dir = Path(__file__).parent.parent / "agents" / "tier-1-always-active"
    for agent_dir in tier1_dir.glob("*"):
        if not agent_dir.is_dir():
            continue

        agent_file = agent_dir / "AGENT.md"
        if agent_file.exists():
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract description from frontmatter
                # Simplified: just use first 200 chars
                description = content[:200]
                agents[agent_dir.name] = {
                    'tier': 'tier-1-always-active',
                    'description': description
                }

    # Tier 2: On-demand agents
    tier2_dir = Path(__file__).parent.parent / "agents" / "tier-2-on-demand"
    for agent_dir in tier2_dir.glob("*"):
        if not agent_dir.is_dir():
            continue

        agent_file = agent_dir / "AGENT.md"
        if agent_file.exists():
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
                description = content[:200]
                agents[agent_dir.name] = {
                    'tier': 'tier-2-on-demand',
                    'description': description
                }

    return agents


def generate_embeddings(agents: dict):
    """Generate embeddings for all agents."""
    store = EmbeddingStore()

    descriptions = [a['description'] for a in agents.values()]
    agent_ids = list(agents.keys())

    print(f"Generating embeddings for {len(agents)} agents...")

    # Get embeddings from Voyage AI
    embeddings = get_voyage_embeddings(descriptions)

    print(f"Generated {len(embeddings)} embeddings")

    # Store in SQLite
    for agent_id, embedding, agent_data in zip(agent_ids, embeddings, agents.values()):
        record = EmbeddingRecord(
            id=f"agent:{agent_id}",
            content=agent_data['description'],
            embedding=embedding,
            source_type="agent",
            source_id=agent_id,
            metadata={
                'tier': agent_data['tier']
            }
        )

        store.store(record)
        print(f"Stored embedding for {agent_id}")

    print(f"\nStored {len(agents)} agent embeddings in SQLite")
    print(f"Note: Upstash Vector already has 30 agents uploaded manually")


if __name__ == '__main__':
    agents = load_agent_descriptions()
    generate_embeddings(agents)
