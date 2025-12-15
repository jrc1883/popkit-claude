"""
Benchmark response utility for PopKit skills (Issue #237)

When POPKIT_BENCHMARK_MODE is set, skills can use this module
to get pre-defined responses instead of calling AskUserQuestion.

This enables automated benchmarking of PopKit workflows without
requiring human interaction.

Usage in skills:
    from hooks.utils.benchmark_responses import (
        is_benchmark_mode,
        get_response,
        should_skip_question
    )

    if should_skip_question("Auth method", "What authentication method?"):
        response = get_response("Auth method", "What authentication method?")
        # Use response instead of calling AskUserQuestion
    else:
        # Normal AskUserQuestion flow
"""

import os
import json
import re
from typing import Optional, Dict, Any, Union, List

# Environment variable checks
BENCHMARK_MODE = os.environ.get('POPKIT_BENCHMARK_MODE', '').lower() == 'true'
RESPONSE_FILE = os.environ.get('POPKIT_BENCHMARK_RESPONSES', '')

# Cache for loaded responses
_responses_cache: Optional[Dict[str, Any]] = None


def is_benchmark_mode() -> bool:
    """Check if running in benchmark mode.

    Returns:
        True if POPKIT_BENCHMARK_MODE is set to 'true'
    """
    return BENCHMARK_MODE


def load_responses() -> Dict[str, Any]:
    """Load benchmark responses from the response file.

    Returns:
        Dictionary containing:
        - responses: Map of question headers to responses
        - standardAutoApprove: Patterns for auto-approve
        - explicitDeclines: Patterns for explicit decline
    """
    global _responses_cache

    if _responses_cache is not None:
        return _responses_cache

    if not RESPONSE_FILE or not os.path.exists(RESPONSE_FILE):
        _responses_cache = {
            'responses': {},
            'standardAutoApprove': [],
            'explicitDeclines': []
        }
        return _responses_cache

    try:
        with open(RESPONSE_FILE, 'r', encoding='utf-8') as f:
            _responses_cache = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[benchmark_responses] Warning: Failed to load response file: {e}")
        _responses_cache = {
            'responses': {},
            'standardAutoApprove': [],
            'explicitDeclines': []
        }

    return _responses_cache


def get_response(
    question_header: str,
    question_text: str = ''
) -> Optional[Union[str, bool, List[str], Dict[str, str]]]:
    """Get pre-defined response for a question.

    Args:
        question_header: The header of the AskUserQuestion (e.g., "Auth method")
        question_text: Full question text for pattern matching

    Returns:
        One of:
        - str: Single selection response
        - bool: True for auto-approve, False for decline
        - List[str]: Multi-selection response
        - Dict with 'other' key: Free-text response
        - None: No response defined, should prompt user
    """
    if not is_benchmark_mode():
        return None

    data = load_responses()

    # Check explicit declines first (always return false/no)
    for pattern in data.get('explicitDeclines', []):
        try:
            if re.search(pattern, question_text, re.IGNORECASE):
                return False
        except re.error:
            continue

    # Check for explicit response by header
    responses = data.get('responses', {})
    if question_header in responses:
        return responses[question_header]

    # Check standard auto-approve patterns
    for pattern in data.get('standardAutoApprove', []):
        try:
            if re.search(pattern, question_text, re.IGNORECASE):
                return True  # Select first/recommended option
        except re.error:
            continue

    # Default: return True to auto-select first option
    # This ensures benchmarks don't block on unexpected questions
    return True


def should_skip_question(
    question_header: str,
    question_text: str = ''
) -> bool:
    """Check if we should skip AskUserQuestion and use a default response.

    Args:
        question_header: The header of the AskUserQuestion
        question_text: Full question text

    Returns:
        True if in benchmark mode and a response can be determined
    """
    if not is_benchmark_mode():
        return False

    response = get_response(question_header, question_text)
    return response is not None


def format_response_for_tool(
    response: Union[str, bool, List[str], Dict[str, str]],
    question_header: str,
    options: Optional[List[Dict[str, str]]] = None
) -> Dict[str, str]:
    """Format a response for use as an AskUserQuestion tool result.

    Args:
        response: The response from get_response()
        question_header: The header of the question
        options: Available options from the question (for matching)

    Returns:
        Dictionary in the format expected by AskUserQuestion tool result:
        {"header": "selected_value"}
    """
    if response is True:
        # Auto-approve: select first option if available
        if options and len(options) > 0:
            return {question_header: options[0].get('label', '')}
        return {question_header: 'yes'}

    if response is False:
        # Explicit decline: select "no" or last option
        if options:
            # Look for an option that seems like "no"
            for opt in options:
                label = opt.get('label', '').lower()
                if label in ('no', 'skip', 'cancel', 'decline', 'not now'):
                    return {question_header: opt.get('label', '')}
            # Fall back to last option
            return {question_header: options[-1].get('label', '')}
        return {question_header: 'no'}

    if isinstance(response, str):
        # Direct string response
        return {question_header: response}

    if isinstance(response, list):
        # Multi-select response - join with comma
        return {question_header: ', '.join(response)}

    if isinstance(response, dict) and 'other' in response:
        # Free-text "Other" response
        return {question_header: response['other']}

    # Unknown format, default to first option
    if options and len(options) > 0:
        return {question_header: options[0].get('label', '')}

    return {question_header: str(response)}


def log_benchmark_response(
    question_header: str,
    question_text: str,
    response: Any
) -> None:
    """Log a benchmark response for debugging.

    This helps track which responses were auto-selected during benchmarks.
    """
    import sys

    # Only log in verbose mode or when debugging
    if os.environ.get('POPKIT_BENCHMARK_VERBOSE', '').lower() == 'true':
        print(
            f"[benchmark] Auto-response: {question_header} = {response} "
            f"(question: {question_text[:50]}...)",
            file=sys.stderr
        )
