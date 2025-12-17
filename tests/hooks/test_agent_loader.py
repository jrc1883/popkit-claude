# packages/plugin/tests/hooks/test_agent_loader.py
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))

from agent_loader import AgentLoader, load_relevant_agents


def test_load_relevant_agents_semantic():
    """Load top relevant agents using semantic search"""
    loader = AgentLoader()

    # Simulate user query
    query = "fix the login bug"

    # Load top 5 agents
    agents = loader.load(query, top_k=5)

    assert len(agents) <= 5
    assert all('agent_id' in a for a in agents)
    assert all('similarity' in a for a in agents)


def test_load_relevant_agents_fallback_to_keywords():
    """Falls back to keyword matching if embeddings fail"""
    loader = AgentLoader(use_embeddings=False)

    query = "security vulnerability in authentication"
    agents = loader.load(query, top_k=5)

    # Should find security-auditor via keyword
    agent_ids = [a['agent_id'] for a in agents]
    assert 'security-auditor' in agent_ids


def test_load_relevant_agents_always_include_tier1():
    """Always include some Tier 1 agents"""
    loader = AgentLoader()

    query = "random task"
    agents = loader.load(query, top_k=10)

    # At least 3 tier-1 agents should be included
    tier1_count = sum(1 for a in agents if a.get('tier') == 'tier-1-always-active')
    assert tier1_count >= 3
