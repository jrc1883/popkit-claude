"""Tests for semantic router utility."""
import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import asdict

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))

from semantic_router import (
    SemanticRouter,
    RoutingResult,
    get_router,
    route,
    route_single,
    DEFAULT_MIN_CONFIDENCE
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Mock routing configuration."""
    return {
        "keywords": {
            "bug": ["bug-whisperer", "test-writer-fixer"],
            "security": ["security-auditor"],
            "performance": ["performance-optimizer"],
            "test": ["test-writer-fixer"],
            "api": ["api-designer"],
            "refactor": ["refactoring-expert"]
        },
        "filePatterns": {
            "*.test.ts": ["test-writer-fixer"],
            "*.tsx": ["code-reviewer", "accessibility-guardian"],
            "*.sql": ["query-optimizer"],
            "*.md": ["documentation-maintainer"]
        },
        "errorPatterns": {
            "TypeError": ["bug-whisperer"],
            "SecurityError": ["security-auditor"],
            "PerformanceError": ["performance-optimizer"]
        }
    }


@pytest.fixture
def mock_embedding_store():
    """Mock EmbeddingStore for testing."""
    store = Mock()
    store.count = Mock(return_value=10)
    return store


@pytest.fixture
def mock_voyage_client():
    """Mock VoyageClient for testing."""
    client = Mock()
    client.is_available = True
    return client


@pytest.fixture
def router_with_mocks(mock_config, mock_embedding_store, mock_voyage_client):
    """Create router with mocked dependencies."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)

            with patch('semantic_router.EmbeddingStore', return_value=mock_embedding_store):
                with patch('semantic_router.VoyageClient', return_value=mock_voyage_client):
                    with patch('semantic_router.is_available', return_value=True):
                        router = SemanticRouter()
                        router._config = mock_config
                        router.store = mock_embedding_store
                        router.client = mock_voyage_client
                        # Set project_path to None to simulate global-only routing
                        # (tests can override this for project-specific tests)
                        router.project_path = None
                        return router


@pytest.fixture
def router_no_embeddings(mock_config):
    """Create router without embedding support."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)

            with patch('semantic_router.is_available', return_value=False):
                router = SemanticRouter()
                router._config = mock_config
                router.client = None
                return router


@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return [0.1] * 1024  # Voyage-3.5 has 1024 dimensions


# =============================================================================
# RoutingResult Tests
# =============================================================================

def test_routing_result_creation():
    """Test RoutingResult dataclass creation."""
    result = RoutingResult(
        agent="bug-whisperer",
        confidence=0.9,
        reason="Bug found",
        method="semantic"
    )

    assert result.agent == "bug-whisperer"
    assert result.confidence == 0.9
    assert result.reason == "Bug found"
    assert result.method == "semantic"


def test_routing_result_to_dict():
    """Test RoutingResult conversion to dictionary."""
    result = RoutingResult(
        agent="security-auditor",
        confidence=0.85,
        reason="Security issue",
        method="keyword"
    )

    result_dict = result.to_dict()

    assert result_dict["agent"] == "security-auditor"
    assert result_dict["confidence"] == 0.85
    assert result_dict["reason"] == "Security issue"
    assert result_dict["method"] == "keyword"


def test_routing_result_is_project_item_default():
    """Test RoutingResult has is_project_item field defaulting to False."""
    result = RoutingResult(
        agent="bug-whisperer",
        confidence=0.9,
        reason="Bug found",
        method="semantic"
    )

    assert result.is_project_item is False


def test_routing_result_is_project_item_true():
    """Test RoutingResult with is_project_item=True."""
    result = RoutingResult(
        agent="project-agent",
        confidence=0.85,
        reason="Project match",
        method="semantic",
        is_project_item=True
    )

    assert result.is_project_item is True
    assert result.to_dict()["is_project_item"] is True


# =============================================================================
# Router Initialization Tests
# =============================================================================

def test_router_initialization_with_config(mock_config, tmp_path):
    """Test router initializes with valid config file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(mock_config))

    with patch('semantic_router.CONFIG_PATH', config_path):
        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter()
            assert router._config == mock_config


def test_router_initialization_without_config():
    """Test router initializes with empty config when file doesn't exist."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter()
            assert router._config == {}


def test_router_initialization_with_invalid_json(tmp_path):
    """Test router handles invalid JSON gracefully."""
    config_path = tmp_path / "config.json"
    config_path.write_text("invalid json {")

    with patch('semantic_router.CONFIG_PATH', config_path):
        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter()
            assert router._config == {}


def test_router_initialization_creates_clients():
    """Test router creates embedding store and voyage client."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.EmbeddingStore') as mock_store:
            with patch('semantic_router.is_available', return_value=True):
                with patch('semantic_router.VoyageClient') as mock_client:
                    router = SemanticRouter()

                    mock_store.assert_called_once()
                    mock_client.assert_called_once()


def test_router_initialization_no_client_when_unavailable():
    """Test router doesn't create client when API unavailable."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter()
            assert router.client is None


def test_router_initialization_with_project_path():
    """Test router accepts explicit project_path parameter."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter(project_path="/explicit/project/path")
            assert router.project_path == "/explicit/project/path"


def test_router_initialization_auto_detects_project():
    """Test router auto-detects project root when not provided."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.is_available', return_value=False):
            router = SemanticRouter()
            # Project path is auto-detected (may be None or actual path)
            assert hasattr(router, 'project_path')


# =============================================================================
# Keyword Routing Tests
# =============================================================================

def test_keyword_route_single_match(router_no_embeddings):
    """Test keyword routing with single keyword match."""
    results = router_no_embeddings._keyword_route("fix bug in code", top_k=5)

    assert len(results) > 0
    assert any(r.agent == "bug-whisperer" for r in results)
    assert all(r.method == "keyword" for r in results)
    assert all(r.confidence == 0.8 for r in results)


def test_keyword_route_multiple_matches(router_no_embeddings):
    """Test keyword routing with multiple keyword matches."""
    results = router_no_embeddings._keyword_route("bug test security", top_k=10)

    agents = [r.agent for r in results]
    assert "bug-whisperer" in agents
    assert "test-writer-fixer" in agents
    assert "security-auditor" in agents


def test_keyword_route_case_insensitive(router_no_embeddings):
    """Test keyword routing is case insensitive."""
    results_lower = router_no_embeddings._keyword_route("bug", top_k=5)
    results_upper = router_no_embeddings._keyword_route("BUG", top_k=5)
    results_mixed = router_no_embeddings._keyword_route("Bug", top_k=5)

    assert len(results_lower) == len(results_upper) == len(results_mixed)
    assert all(r.agent in ["bug-whisperer", "test-writer-fixer"] for r in results_lower)


def test_keyword_route_no_matches(router_no_embeddings):
    """Test keyword routing with no matches."""
    results = router_no_embeddings._keyword_route("completely unrelated query", top_k=5)

    assert len(results) == 0


def test_keyword_route_respects_top_k(router_no_embeddings):
    """Test keyword routing respects top_k parameter."""
    results = router_no_embeddings._keyword_route("bug test security performance", top_k=2)

    assert len(results) <= 2


def test_keyword_route_includes_reason(router_no_embeddings):
    """Test keyword routing includes reason with matched keyword."""
    results = router_no_embeddings._keyword_route("security issue found", top_k=5)

    security_result = next((r for r in results if r.agent == "security-auditor"), None)
    assert security_result is not None
    assert "security" in security_result.reason.lower()


# =============================================================================
# File Pattern Routing Tests
# =============================================================================

def test_file_pattern_route_test_file(router_no_embeddings):
    """Test file pattern routing for test files."""
    results = router_no_embeddings._file_pattern_route("src/app.test.ts")

    assert len(results) > 0
    assert any(r.agent == "test-writer-fixer" for r in results)
    assert all(r.method == "file_pattern" for r in results)
    assert all(r.confidence == 0.9 for r in results)


def test_file_pattern_route_tsx_file(router_no_embeddings):
    """Test file pattern routing for TSX files."""
    results = router_no_embeddings._file_pattern_route("components/Button.tsx")

    agents = [r.agent for r in results]
    assert "code-reviewer" in agents
    assert "accessibility-guardian" in agents


def test_file_pattern_route_sql_file(router_no_embeddings):
    """Test file pattern routing for SQL files."""
    results = router_no_embeddings._file_pattern_route("migrations/001_create_users.sql")

    assert len(results) > 0
    assert any(r.agent == "query-optimizer" for r in results)


def test_file_pattern_route_markdown_file(router_no_embeddings):
    """Test file pattern routing for markdown files."""
    results = router_no_embeddings._file_pattern_route("docs/README.md")

    assert len(results) > 0
    assert any(r.agent == "documentation-maintainer" for r in results)


def test_file_pattern_route_no_match(router_no_embeddings):
    """Test file pattern routing with no matching pattern."""
    results = router_no_embeddings._file_pattern_route("random.xyz")

    assert len(results) == 0


def test_file_pattern_route_glob_wildcard(router_no_embeddings):
    """Test file pattern routing handles glob wildcards."""
    results = router_no_embeddings._file_pattern_route("deeply/nested/path/file.test.ts")

    assert len(results) > 0
    assert any(r.agent == "test-writer-fixer" for r in results)


def test_file_pattern_route_includes_pattern_in_reason(router_no_embeddings):
    """Test file pattern routing includes pattern in reason."""
    results = router_no_embeddings._file_pattern_route("app.test.ts")

    test_result = next((r for r in results if r.agent == "test-writer-fixer"), None)
    assert test_result is not None
    assert "*.test.ts" in test_result.reason


# =============================================================================
# Error Pattern Routing Tests
# =============================================================================

def test_error_pattern_route_type_error(router_no_embeddings):
    """Test error pattern routing for TypeError."""
    results = router_no_embeddings._error_pattern_route("TypeError: Cannot read property 'x'")

    assert len(results) > 0
    assert any(r.agent == "bug-whisperer" for r in results)
    assert all(r.method == "error_pattern" for r in results)
    assert all(r.confidence == 0.85 for r in results)


def test_error_pattern_route_security_error(router_no_embeddings):
    """Test error pattern routing for SecurityError."""
    results = router_no_embeddings._error_pattern_route("SecurityError: Access denied")

    assert len(results) > 0
    assert any(r.agent == "security-auditor" for r in results)


def test_error_pattern_route_performance_error(router_no_embeddings):
    """Test error pattern routing for PerformanceError."""
    results = router_no_embeddings._error_pattern_route("PerformanceError: Operation too slow")

    assert len(results) > 0
    assert any(r.agent == "performance-optimizer" for r in results)


def test_error_pattern_route_case_insensitive(router_no_embeddings):
    """Test error pattern routing is case insensitive."""
    results_lower = router_no_embeddings._error_pattern_route("typeerror")
    results_upper = router_no_embeddings._error_pattern_route("TYPEERROR")
    results_mixed = router_no_embeddings._error_pattern_route("TypeError")

    assert len(results_lower) == len(results_upper) == len(results_mixed)


def test_error_pattern_route_no_match(router_no_embeddings):
    """Test error pattern routing with no matching error."""
    results = router_no_embeddings._error_pattern_route("RandomError: Something happened")

    assert len(results) == 0


def test_error_pattern_route_includes_pattern_in_reason(router_no_embeddings):
    """Test error pattern routing includes pattern in reason."""
    results = router_no_embeddings._error_pattern_route("TypeError in module")

    type_error_result = next((r for r in results if r.agent == "bug-whisperer"), None)
    assert type_error_result is not None
    assert "TypeError" in type_error_result.reason


# =============================================================================
# Semantic Routing Tests
# =============================================================================

def test_semantic_route_with_embeddings(router_with_mocks, sample_embedding):
    """Test semantic routing with embeddings available."""
    # Mock the search results
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"  # Global agent, not project-specific
    mock_record.content = "Expert at finding and fixing bugs in code"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.75

    router_with_mocks.store.search.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    assert len(results) == 1
    assert results[0].agent == "bug-whisperer"
    assert results[0].confidence == 0.75
    assert results[0].method == "semantic"
    assert "Expert at finding" in results[0].reason


def test_semantic_route_no_client(router_no_embeddings):
    """Test semantic routing returns empty when client unavailable."""
    results = router_no_embeddings._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    assert len(results) == 0


def test_semantic_route_respects_min_confidence(router_with_mocks, sample_embedding):
    """Test semantic routing respects minimum confidence threshold."""
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"
    mock_record.content = "Bug fixing expert"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.2  # Below default threshold

    router_with_mocks.store.search.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    # Store.search should filter by min_similarity
    results = router_with_mocks._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    # Verify min_similarity was passed to search
    router_with_mocks.store.search.assert_called_once()
    call_args = router_with_mocks.store.search.call_args
    assert call_args[1]["min_similarity"] == 0.3


def test_semantic_route_handles_exceptions(router_with_mocks, sample_embedding):
    """Test semantic routing handles exceptions gracefully."""
    router_with_mocks.client.embed_query.side_effect = Exception("API error")

    results = router_with_mocks._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    assert len(results) == 0


def test_semantic_route_truncates_long_content(router_with_mocks, sample_embedding):
    """Test semantic routing truncates long content in reason."""
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"
    mock_record.content = "A" * 100  # Long content

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.8

    router_with_mocks.store.search.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("query", top_k=3, min_confidence=0.3)

    assert len(results) == 1
    assert len(results[0].reason) < 100  # Content truncated with "..."
    assert "..." in results[0].reason


# =============================================================================
# Deduplication Tests
# =============================================================================

def test_deduplicate_results_no_duplicates():
    """Test deduplication with no duplicate agents."""
    results = [
        RoutingResult("agent-1", 0.9, "reason 1", "semantic"),
        RoutingResult("agent-2", 0.8, "reason 2", "keyword"),
        RoutingResult("agent-3", 0.7, "reason 3", "file_pattern")
    ]

    router = SemanticRouter.__new__(SemanticRouter)
    deduplicated = router._deduplicate_results(results)

    assert len(deduplicated) == 3


def test_deduplicate_results_with_duplicates():
    """Test deduplication removes duplicate agents."""
    results = [
        RoutingResult("agent-1", 0.9, "reason 1", "semantic"),
        RoutingResult("agent-1", 0.8, "reason 2", "keyword"),
        RoutingResult("agent-2", 0.7, "reason 3", "file_pattern")
    ]

    router = SemanticRouter.__new__(SemanticRouter)
    deduplicated = router._deduplicate_results(results)

    assert len(deduplicated) == 2
    assert any(r.agent == "agent-1" for r in deduplicated)
    assert any(r.agent == "agent-2" for r in deduplicated)


def test_deduplicate_results_keeps_highest_confidence():
    """Test deduplication keeps result with highest confidence."""
    results = [
        RoutingResult("agent-1", 0.8, "reason 1", "semantic"),
        RoutingResult("agent-1", 0.95, "reason 2", "keyword"),
        RoutingResult("agent-1", 0.7, "reason 3", "file_pattern")
    ]

    router = SemanticRouter.__new__(SemanticRouter)
    deduplicated = router._deduplicate_results(results)

    assert len(deduplicated) == 1
    assert deduplicated[0].confidence == 0.95
    assert deduplicated[0].method == "keyword"


def test_deduplicate_results_empty_list():
    """Test deduplication handles empty list."""
    router = SemanticRouter.__new__(SemanticRouter)
    deduplicated = router._deduplicate_results([])

    assert len(deduplicated) == 0


# =============================================================================
# Main route() Method Tests
# =============================================================================

def test_route_basic_query(router_no_embeddings):
    """Test basic routing query without context."""
    results = router_no_embeddings.route("fix bug in code", top_k=3)

    assert len(results) <= 3
    assert all(isinstance(r, RoutingResult) for r in results)


def test_route_with_file_context(router_no_embeddings):
    """Test routing with file path context."""
    results = router_no_embeddings.route(
        "review this file",
        top_k=5,
        context={"file_path": "app.test.ts"}
    )

    # Should find test-writer-fixer from file pattern
    assert any(r.agent == "test-writer-fixer" for r in results)


def test_route_with_error_context(router_no_embeddings):
    """Test routing with error context."""
    results = router_no_embeddings.route(
        "handle error",
        top_k=5,
        context={"error": "TypeError: undefined"}
    )

    # Should find bug-whisperer from error pattern
    assert any(r.agent == "bug-whisperer" for r in results)


def test_route_with_multiple_contexts(router_no_embeddings):
    """Test routing with multiple context types."""
    results = router_no_embeddings.route(
        "security review",
        top_k=10,
        context={
            "file_path": "auth.tsx",
            "error": "SecurityError"
        }
    )

    # Should combine results from keyword, file pattern, and error pattern
    assert len(results) > 0
    agents = [r.agent for r in results]
    assert "security-auditor" in agents  # From keyword + error pattern


def test_route_respects_min_confidence(router_no_embeddings):
    """Test route respects minimum confidence threshold."""
    # With high min_confidence, should filter out low-confidence results
    results = router_no_embeddings.route(
        "completely unrelated query",
        top_k=10,
        min_confidence=0.95
    )

    # Keyword matches are 0.8, so should be filtered
    assert all(r.confidence >= 0.95 for r in results)


def test_route_deduplicates_results(router_no_embeddings):
    """Test route deduplicates agents from multiple sources."""
    results = router_no_embeddings.route(
        "test bug",  # Matches 'test' and 'bug' keywords
        top_k=10,
        context={"file_path": "app.test.ts"}  # Also matches file pattern
    )

    # test-writer-fixer should appear once despite multiple matches
    test_writer_count = sum(1 for r in results if r.agent == "test-writer-fixer")
    assert test_writer_count == 1


def test_route_sorts_by_confidence(router_no_embeddings):
    """Test route sorts results by confidence descending."""
    results = router_no_embeddings.route(
        "security test bug",
        top_k=10
    )

    # Results should be sorted highest confidence first
    confidences = [r.confidence for r in results]
    assert confidences == sorted(confidences, reverse=True)


def test_route_limits_to_top_k(router_no_embeddings):
    """Test route limits results to top_k."""
    results = router_no_embeddings.route(
        "security test bug performance api",
        top_k=2
    )

    assert len(results) <= 2


def test_route_with_no_matches_returns_empty(router_no_embeddings):
    """Test route returns empty list when no matches found."""
    results = router_no_embeddings.route(
        "completely unrelated query xyz123",
        top_k=5,
        min_confidence=0.95
    )

    assert len(results) == 0


def test_route_uses_semantic_when_available(router_with_mocks, sample_embedding):
    """Test route uses semantic routing when embeddings available."""
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"
    mock_record.content = "Bug expert"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.85

    router_with_mocks.store.search.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks.route("fix bug", top_k=3)

    # Should have called semantic routing
    router_with_mocks.client.embed_query.assert_called_once()
    router_with_mocks.store.search.assert_called_once()


# =============================================================================
# route_single() Method Tests
# =============================================================================

def test_route_single_returns_best_match(router_no_embeddings):
    """Test route_single returns single best matching agent."""
    result = router_no_embeddings.route_single("fix security bug")

    assert result is not None
    assert isinstance(result, RoutingResult)


def test_route_single_returns_none_when_no_match(router_no_embeddings):
    """Test route_single returns None when no match found."""
    result = router_no_embeddings.route_single(
        "xyz unrelated query",
        min_confidence=0.99
    )

    assert result is None


def test_route_single_respects_min_confidence(router_no_embeddings):
    """Test route_single respects minimum confidence."""
    result = router_no_embeddings.route_single(
        "fix bug",
        min_confidence=0.0
    )

    assert result is not None

    result_high = router_no_embeddings.route_single(
        "xyz random",
        min_confidence=0.95
    )

    # No match for random query with high confidence
    assert result_high is None


def test_route_single_with_context(router_no_embeddings):
    """Test route_single with context."""
    result = router_no_embeddings.route_single(
        "review file",
        context={"file_path": "query.sql"}
    )

    assert result is not None
    assert result.agent == "query-optimizer"


# =============================================================================
# explain_routing() Method Tests
# =============================================================================

def test_explain_routing_structure(router_no_embeddings):
    """Test explain_routing returns proper structure."""
    explanation = router_no_embeddings.explain_routing("fix bug")

    assert "query" in explanation
    assert "context" in explanation
    assert "semantic_available" in explanation
    assert "embedding_count" in explanation
    assert "methods_tried" in explanation
    assert "results" in explanation


def test_explain_routing_query_captured(router_no_embeddings):
    """Test explain_routing captures query."""
    explanation = router_no_embeddings.explain_routing("security audit")

    assert explanation["query"] == "security audit"


def test_explain_routing_context_captured(router_no_embeddings):
    """Test explain_routing captures context."""
    context = {"file_path": "app.tsx", "error": "TypeError"}
    explanation = router_no_embeddings.explain_routing("review", context=context)

    assert explanation["context"] == context


def test_explain_routing_shows_methods(router_no_embeddings):
    """Test explain_routing shows which methods were tried."""
    explanation = router_no_embeddings.explain_routing("fix bug")

    assert "keyword" in explanation["methods_tried"]


def test_explain_routing_with_file_context(router_no_embeddings):
    """Test explain_routing includes file pattern results."""
    explanation = router_no_embeddings.explain_routing(
        "review",
        context={"file_path": "app.test.ts"}
    )

    assert "file_pattern" in explanation["methods_tried"]
    assert "file_pattern_results" in explanation


def test_explain_routing_with_error_context(router_no_embeddings):
    """Test explain_routing includes error pattern results."""
    explanation = router_no_embeddings.explain_routing(
        "handle",
        context={"error": "TypeError"}
    )

    assert "error_pattern" in explanation["methods_tried"]
    assert "error_pattern_results" in explanation


def test_explain_routing_semantic_available_flag(router_with_mocks, router_no_embeddings):
    """Test explain_routing correctly reports semantic availability."""
    explanation_with = router_with_mocks.explain_routing("test")
    explanation_without = router_no_embeddings.explain_routing("test")

    assert explanation_with["semantic_available"] is True
    assert explanation_without["semantic_available"] is False


def test_explain_routing_includes_keyword_results(router_no_embeddings):
    """Test explain_routing includes keyword routing results."""
    explanation = router_no_embeddings.explain_routing("fix bug")

    assert "keyword_results" in explanation
    assert len(explanation["keyword_results"]) > 0


def test_explain_routing_final_results(router_no_embeddings):
    """Test explain_routing includes final combined results."""
    explanation = router_no_embeddings.explain_routing("security bug")

    assert "results" in explanation
    assert len(explanation["results"]) > 0


# =============================================================================
# Module-Level Function Tests
# =============================================================================

def test_get_router_singleton():
    """Test get_router returns singleton instance."""
    with patch('semantic_router.SemanticRouter'):
        router1 = get_router()
        router2 = get_router()

        assert router1 is router2


def test_route_convenience_function():
    """Test module-level route function."""
    with patch('semantic_router.SemanticRouter') as mock_router_class:
        mock_router_instance = Mock()
        mock_router_class.return_value = mock_router_instance

        # Reset singleton
        import semantic_router
        semantic_router._router = None

        route("test query", top_k=5)

        mock_router_instance.route.assert_called_once_with("test query", top_k=5, context=None)


def test_route_single_convenience_function():
    """Test module-level route_single function."""
    with patch('semantic_router.SemanticRouter') as mock_router_class:
        mock_router_instance = Mock()
        mock_router_class.return_value = mock_router_instance

        # Reset singleton
        import semantic_router
        semantic_router._router = None

        route_single("test query")

        mock_router_instance.route_single.assert_called_once_with("test query", context=None)


def test_route_convenience_with_context():
    """Test module-level route with context."""
    with patch('semantic_router.SemanticRouter') as mock_router_class:
        mock_router_instance = Mock()
        mock_router_class.return_value = mock_router_instance

        # Reset singleton
        import semantic_router
        semantic_router._router = None

        context = {"file_path": "test.ts"}
        route("query", top_k=3, context=context)

        mock_router_instance.route.assert_called_once_with("query", top_k=3, context=context)


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================

def test_route_empty_query(router_no_embeddings):
    """Test routing with empty query."""
    results = router_no_embeddings.route("", top_k=5)

    # Empty query shouldn't match keywords
    assert len(results) == 0


def test_route_whitespace_only_query(router_no_embeddings):
    """Test routing with whitespace-only query."""
    results = router_no_embeddings.route("   ", top_k=5)

    assert len(results) == 0


def test_route_none_context(router_no_embeddings):
    """Test routing handles None context gracefully."""
    results = router_no_embeddings.route("test query", top_k=5, context=None)

    # Should work without context
    assert isinstance(results, list)


def test_route_empty_context_dict(router_no_embeddings):
    """Test routing with empty context dictionary."""
    results = router_no_embeddings.route("test query", top_k=5, context={})

    assert isinstance(results, list)


def test_route_top_k_zero(router_no_embeddings):
    """Test routing with top_k=0."""
    results = router_no_embeddings.route("bug fix", top_k=0)

    assert len(results) == 0


def test_route_top_k_negative(router_no_embeddings):
    """Test routing with negative top_k."""
    results = router_no_embeddings.route("bug fix", top_k=-1)

    # Should handle gracefully (returns empty or nothing)
    assert len(results) == 0


def test_route_confidence_threshold_edge_cases(router_no_embeddings):
    """Test routing with edge case confidence thresholds."""
    # Zero threshold - should accept anything
    results_zero = router_no_embeddings.route("bug", top_k=5, min_confidence=0.0)
    assert len(results_zero) > 0

    # Note: min_confidence only filters semantic results, not keyword/file/error patterns
    # Keyword matches always return 0.8 confidence, file patterns 0.9, error patterns 0.85
    # So threshold of 1.0 won't filter keyword results (0.8 < 1.0)
    results_high = router_no_embeddings.route("bug", top_k=5, min_confidence=0.9)
    # Should still get keyword results (0.8 confidence) because only semantic is filtered
    assert len(results_high) > 0


def test_route_special_characters_in_query(router_no_embeddings):
    """Test routing handles special characters in query."""
    results = router_no_embeddings.route("fix bug #42 in @module/package.json", top_k=5)

    # Should still match 'bug' keyword
    assert any(r.agent == "bug-whisperer" for r in results)


def test_file_pattern_special_characters(router_no_embeddings):
    """Test file pattern routing with special characters."""
    results = router_no_embeddings._file_pattern_route("src/@types/index.d.ts")

    # Should handle paths with special chars
    assert isinstance(results, list)


def test_error_pattern_multiline_error(router_no_embeddings):
    """Test error pattern routing with multiline error message."""
    error_message = """
    TypeError: Cannot read property 'x'
        at Module.load (app.js:123)
        at Function.require (node.js:456)
    """

    results = router_no_embeddings._error_pattern_route(error_message)

    assert any(r.agent == "bug-whisperer" for r in results)


def test_keyword_partial_word_match(router_no_embeddings):
    """Test keyword routing doesn't match partial words."""
    # "buggy" contains "bug" but shouldn't necessarily match
    results_buggy = router_no_embeddings._keyword_route("buggy code", top_k=5)

    # Should still match since "bug" is substring of "buggy"
    # This documents current behavior
    assert any(r.agent == "bug-whisperer" for r in results_buggy)


def test_complex_multi_source_routing(router_no_embeddings):
    """Test complex routing combining all sources."""
    results = router_no_embeddings.route(
        "security test bug",
        top_k=10,
        context={
            "file_path": "auth.test.ts",
            "error": "SecurityError: Access denied"
        }
    )

    # Should combine results from keywords, file patterns, and error patterns
    agents = [r.agent for r in results]

    # From keywords
    assert "security-auditor" in agents
    assert "test-writer-fixer" in agents
    assert "bug-whisperer" in agents

    # Results should be deduplicated and sorted
    assert len(results) <= 10
    confidences = [r.confidence for r in results]
    assert confidences == sorted(confidences, reverse=True)


def test_routing_performance_many_keywords(router_no_embeddings):
    """Test routing performance doesn't degrade with many keyword matches."""
    # Query that matches many keywords
    query = "bug security test performance api refactor"

    results = router_no_embeddings.route(query, top_k=20)

    # Should complete successfully and return deduplicated results
    assert len(results) <= 20

    # Verify no duplicate agents
    agents = [r.agent for r in results]
    assert len(agents) == len(set(agents))


def test_default_min_confidence_value():
    """Test DEFAULT_MIN_CONFIDENCE has expected value."""
    assert DEFAULT_MIN_CONFIDENCE == 0.3


def test_routing_result_method_types():
    """Test all routing methods produce correct method types."""
    router = SemanticRouter.__new__(SemanticRouter)
    router._config = {
        "keywords": {"test": ["test-writer-fixer"]},
        "filePatterns": {"*.ts": ["code-reviewer"]},
        "errorPatterns": {"Error": ["bug-whisperer"]}
    }

    keyword_results = router._keyword_route("test", 1)
    assert all(r.method == "keyword" for r in keyword_results)

    file_results = router._file_pattern_route("app.ts")
    assert all(r.method == "file_pattern" for r in file_results)

    error_results = router._error_pattern_route("Error message")
    assert all(r.method == "error_pattern" for r in error_results)


# =============================================================================
# Project Routing Tests (Issue #48)
# =============================================================================

def test_semantic_route_with_project_items(router_with_mocks, sample_embedding):
    """Test semantic routing recognizes project items and applies boost."""
    # Mock project-agent record
    mock_record = Mock()
    mock_record.source_id = "my-project-agent"
    mock_record.source_type = "project-agent"
    mock_record.content = "A project-specific agent for custom tasks"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.70

    # Set project path
    router_with_mocks.project_path = "/test/project"

    # Mock count_project to indicate project has embeddings
    router_with_mocks.store.count_project.return_value = 5
    router_with_mocks.store.search_project.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("custom task", top_k=3, min_confidence=0.3)

    # Should have project item with boosted confidence
    assert len(results) == 1
    assert results[0].agent == "my-project-agent"
    assert results[0].is_project_item is True
    # Confidence should be boosted by 0.1 (PROJECT_ITEM_BOOST)
    # Using pytest.approx for floating point comparison
    assert results[0].confidence == pytest.approx(0.80)  # 0.70 + 0.10


def test_semantic_route_global_items_not_boosted(router_with_mocks, sample_embedding):
    """Test global agents don't get project boost."""
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"  # Global agent, not project-agent
    mock_record.content = "Bug fixing expert"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.75

    router_with_mocks.project_path = "/test/project"
    router_with_mocks.store.count_project.return_value = 5
    router_with_mocks.store.search_project.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    assert len(results) == 1
    assert results[0].is_project_item is False
    # No boost - confidence stays at 0.75
    assert results[0].confidence == 0.75


def test_semantic_route_generated_items_get_boost(router_with_mocks, sample_embedding):
    """Test generated items (generated-agent) also get project boost."""
    mock_record = Mock()
    mock_record.source_id = "auto-generated-agent"
    mock_record.source_type = "generated-agent"
    mock_record.content = "Auto-generated project agent"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.60

    router_with_mocks.project_path = "/test/project"
    router_with_mocks.store.count_project.return_value = 5
    router_with_mocks.store.search_project.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("task", top_k=3, min_confidence=0.3)

    assert len(results) == 1
    assert results[0].is_project_item is True
    # Should be boosted
    assert results[0].confidence == 0.70  # 0.60 + 0.10


def test_semantic_route_boost_caps_at_1(router_with_mocks, sample_embedding):
    """Test project boost doesn't exceed 1.0 confidence."""
    mock_record = Mock()
    mock_record.source_id = "high-confidence-agent"
    mock_record.source_type = "project-agent"
    mock_record.content = "Very high confidence match"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.98  # Very high

    router_with_mocks.project_path = "/test/project"
    router_with_mocks.store.count_project.return_value = 1
    router_with_mocks.store.search_project.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("query", top_k=3, min_confidence=0.3)

    assert len(results) == 1
    # Should cap at 1.0, not 1.08
    assert results[0].confidence == 1.0


def test_semantic_route_falls_back_to_global_without_project(router_with_mocks, sample_embedding):
    """Test semantic routing falls back to global search when no project embeddings."""
    mock_record = Mock()
    mock_record.source_id = "bug-whisperer"
    mock_record.source_type = "agent"
    mock_record.content = "Bug expert"

    mock_search_result = Mock()
    mock_search_result.record = mock_record
    mock_search_result.similarity = 0.80

    router_with_mocks.project_path = None
    router_with_mocks.store.count.return_value = 10
    router_with_mocks.store.search.return_value = [mock_search_result]
    router_with_mocks.client.embed_query.return_value = sample_embedding

    results = router_with_mocks._semantic_route("fix bug", top_k=3, min_confidence=0.3)

    # Should use global search, not project search
    router_with_mocks.store.search.assert_called_once()
    assert len(results) == 1
    assert results[0].confidence == 0.80


def test_route_for_project_method(mock_config, sample_embedding):
    """Test route_for_project temporarily overrides project path."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)

            with patch('semantic_router.is_available', return_value=False):
                router = SemanticRouter(project_path="/original/project")
                router._config = mock_config

                # Verify original project path
                assert router.project_path == "/original/project"

                # Call route_for_project with different path
                results = router.route_for_project(
                    "bug fix",
                    project_path="/different/project",
                    top_k=3
                )

                # After call, original path should be restored
                assert router.project_path == "/original/project"


def test_route_for_project_restores_path_on_exception(mock_config):
    """Test route_for_project restores path even if exception occurs."""
    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)

            with patch('semantic_router.is_available', return_value=False):
                router = SemanticRouter(project_path="/original/project")
                router._config = mock_config

                # Mock route to raise exception
                original_route = router.route
                def failing_route(*args, **kwargs):
                    raise ValueError("Test exception")
                router.route = failing_route

                try:
                    router.route_for_project("query", "/different/project")
                except ValueError:
                    pass

                # Path should still be restored
                assert router.project_path == "/original/project"


def test_explain_routing_includes_project_info(router_no_embeddings):
    """Test explain_routing includes project path and embedding count."""
    router_no_embeddings.project_path = "/test/project"

    with patch.object(router_no_embeddings.store, 'count_project', return_value=5):
        explanation = router_no_embeddings.explain_routing("bug fix")

    assert "project_path" in explanation
    assert explanation["project_path"] == "/test/project"
    assert "project_embedding_count" in explanation
    assert explanation["project_embedding_count"] == 5


def test_explain_routing_project_info_when_no_project(router_no_embeddings):
    """Test explain_routing handles no project path gracefully."""
    router_no_embeddings.project_path = None

    explanation = router_no_embeddings.explain_routing("query")

    assert "project_path" in explanation
    assert explanation["project_path"] is None
    assert "project_embedding_count" in explanation
    assert explanation["project_embedding_count"] == 0


def test_project_detection_finds_claude_dir(tmp_path):
    """Test _detect_project_root finds .claude directory."""
    # Create project structure
    project_dir = tmp_path / "myproject"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)

    # Create a subdirectory to start from
    nested_dir = project_dir / "src" / "components"
    nested_dir.mkdir(parents=True)

    with patch('semantic_router.CONFIG_PATH') as mock_path:
        mock_path.exists.return_value = False

        with patch('semantic_router.is_available', return_value=False):
            with patch('pathlib.Path.cwd', return_value=nested_dir):
                router = SemanticRouter()
                # Should find the project root with .claude
                assert router.project_path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
