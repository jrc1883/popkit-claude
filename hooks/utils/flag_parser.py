#!/usr/bin/env python3
"""
Flag Parser Utility
Centralized argument and flag parsing for PopKit commands.

Handles short flags (-p), long flags (--power), and positional arguments
for commands like /popkit:work, /popkit:issues, /popkit:power.

Part of the popkit plugin system.
"""

import re
from typing import Dict, List, Optional, Any, Tuple


# =============================================================================
# Work Command Parser
# =============================================================================

def parse_work_args(args: str) -> Dict[str, Any]:
    """Parse /popkit:work command arguments.

    Supported formats:
        /popkit:work #4
        /popkit:work gh-4
        /popkit:work 4
        /popkit:work #4 -p
        /popkit:work #4 --power
        /popkit:work #4 --solo
        /popkit:work #4 --phases explore,implement,test
        /popkit:work #4 --agents reviewer,tester

    Args:
        args: Raw argument string from $ARGUMENTS

    Returns:
        Dict with parsed values:
        - issue_number: int or None
        - force_power: bool (True if -p or --power)
        - force_solo: bool (True if -s or --solo)
        - phases: List[str] or None
        - agents: List[str] or None
        - error: str or None (if parsing failed)
    """
    result = {
        "issue_number": None,
        "force_power": False,
        "force_solo": False,
        "phases": None,
        "agents": None,
        "error": None
    }

    if not args or not args.strip():
        result["error"] = "No arguments provided. Usage: /popkit:work #N [-p|--power] [--solo]"
        return result

    args = args.strip()

    # Extract issue number
    # Formats: #4, gh-4, gh4, 4
    issue_match = re.search(r'(?:#|gh-?)?(\d+)', args, re.IGNORECASE)
    if issue_match:
        result["issue_number"] = int(issue_match.group(1))
    else:
        result["error"] = f"Could not parse issue number from: {args}"
        return result

    # Check for Power Mode flags
    if re.search(r'\s-p(?:\s|$)', args) or re.search(r'--power(?:\s|$)', args):
        result["force_power"] = True

    # Check for Solo mode flag
    if re.search(r'\s-s(?:\s|$)', args) or re.search(r'--solo(?:\s|$)', args):
        result["force_solo"] = True

    # Mutually exclusive check
    if result["force_power"] and result["force_solo"]:
        result["error"] = "Cannot use both --power and --solo flags together"
        return result

    # Parse --phases flag
    phases_match = re.search(r'--phases\s+([a-z,_]+)', args, re.IGNORECASE)
    if phases_match:
        result["phases"] = [p.strip() for p in phases_match.group(1).split(",")]

    # Parse --agents flag
    agents_match = re.search(r'--agents\s+([a-z,_-]+)', args, re.IGNORECASE)
    if agents_match:
        result["agents"] = [a.strip() for a in agents_match.group(1).split(",")]

    return result


# =============================================================================
# Issues Command Parser
# =============================================================================

def parse_issues_args(args: str) -> Dict[str, Any]:
    """Parse /popkit:issues command arguments.

    Supported formats:
        /popkit:issues
        /popkit:issues --power
        /popkit:issues -p
        /popkit:issues --label bug
        /popkit:issues -l feature
        /popkit:issues --state all
        /popkit:issues --assignee @me
        /popkit:issues -n 10

    Args:
        args: Raw argument string from $ARGUMENTS

    Returns:
        Dict with parsed values:
        - filter_power: bool (True if -p or --power)
        - label: str or None
        - state: str (default "open")
        - assignee: str or None
        - limit: int (default 20)
    """
    result = {
        "filter_power": False,
        "label": None,
        "state": "open",
        "assignee": None,
        "limit": 20
    }

    if not args:
        return result

    args = args.strip()

    # Check for Power Mode filter
    if re.search(r'\s-p(?:\s|$)', args) or re.search(r'--power(?:\s|$)', args):
        result["filter_power"] = True

    # Parse --label or -l flag
    label_match = re.search(r'(?:--label|-l)\s+([a-z0-9:_-]+)', args, re.IGNORECASE)
    if label_match:
        result["label"] = label_match.group(1)

    # Parse --state flag
    state_match = re.search(r'--state\s+(open|closed|all)', args, re.IGNORECASE)
    if state_match:
        result["state"] = state_match.group(1).lower()

    # Parse --assignee flag
    assignee_match = re.search(r'--assignee\s+(@?\w+)', args)
    if assignee_match:
        result["assignee"] = assignee_match.group(1)

    # Parse -n or --limit flag
    limit_match = re.search(r'(?:-n|--limit)\s+(\d+)', args)
    if limit_match:
        result["limit"] = int(limit_match.group(1))

    return result


# =============================================================================
# Power Command Parser
# =============================================================================

def parse_power_args(args: str) -> Dict[str, Any]:
    """Parse /popkit:power command arguments.

    Supported formats:
        /popkit:power status
        /popkit:power stop
        /popkit:power "Custom objective"
        /popkit:power "Objective" --phases design,implement,test
        /popkit:power "Objective" --agents reviewer,tester
        /popkit:power "Objective" --timeout 45

    Args:
        args: Raw argument string from $ARGUMENTS

    Returns:
        Dict with parsed values:
        - subcommand: "status" | "stop" | "start"
        - objective: str or None (for custom objectives)
        - phases: List[str] or None
        - agents: List[str] or None
        - timeout: int (default 30, in minutes)
    """
    result = {
        "subcommand": "status",
        "objective": None,
        "phases": None,
        "agents": None,
        "timeout": 30
    }

    if not args:
        return result

    args = args.strip()

    # Check for subcommands
    if args.lower() == "status":
        result["subcommand"] = "status"
        return result

    if args.lower() == "stop":
        result["subcommand"] = "stop"
        return result

    # Otherwise, treat as custom objective
    result["subcommand"] = "start"

    # Extract quoted objective
    objective_match = re.search(r'"([^"]+)"', args)
    if objective_match:
        result["objective"] = objective_match.group(1)
    else:
        # Take first word(s) before any flag as objective
        pre_flag = re.split(r'\s+--', args)[0].strip()
        if pre_flag and not pre_flag.startswith("-"):
            result["objective"] = pre_flag

    # Parse --phases flag
    phases_match = re.search(r'--phases\s+([a-z,_]+)', args, re.IGNORECASE)
    if phases_match:
        result["phases"] = [p.strip() for p in phases_match.group(1).split(",")]

    # Parse --agents flag
    agents_match = re.search(r'--agents\s+([a-z,_-]+)', args, re.IGNORECASE)
    if agents_match:
        result["agents"] = [a.strip() for a in agents_match.group(1).split(",")]

    # Parse --timeout flag
    timeout_match = re.search(r'--timeout\s+(\d+)', args)
    if timeout_match:
        result["timeout"] = int(timeout_match.group(1))

    return result


# =============================================================================
# Thinking Flag Parser
# =============================================================================

def parse_thinking_flags(args: str) -> Dict[str, Any]:
    """Parse extended thinking flags from arguments.

    Supported flags:
        -T, --thinking      Force extended thinking on
        --no-thinking       Force extended thinking off
        --think-budget N    Set thinking budget tokens (default: 10000)

    Args:
        args: Raw argument string from $ARGUMENTS

    Returns:
        Dict with parsed values:
        - force_thinking: bool or None (None = use default per model)
        - budget_tokens: int (default 10000)
    """
    result = {
        "force_thinking": None,  # None = use model default
        "budget_tokens": 10000
    }

    if not args:
        return result

    args = args.strip()

    # Check for force thinking on (-T or --thinking)
    if re.search(r'\s-T(?:\s|$)', f" {args}") or re.search(r'--thinking(?:\s|$)', args):
        result["force_thinking"] = True

    # Check for force thinking off (--no-thinking)
    if re.search(r'--no-thinking(?:\s|$)', args):
        result["force_thinking"] = False

    # Parse --think-budget flag
    # Note: specifying a budget implies thinking should be enabled
    budget_match = re.search(r'--think-budget\s+(\d+)', args)
    if budget_match:
        result["budget_tokens"] = int(budget_match.group(1))
        # If budget specified but no explicit enable/disable, enable thinking
        if result["force_thinking"] is None:
            result["force_thinking"] = True

    return result


# =============================================================================
# Model Flag Parser
# =============================================================================

def parse_model_flag(args: str) -> Dict[str, Any]:
    """Parse model override flag from arguments.

    Supported flags:
        --model haiku      Use Haiku model
        --model sonnet     Use Sonnet model
        --model opus       Use Opus model
        -m haiku           Short form

    Args:
        args: Raw argument string from $ARGUMENTS

    Returns:
        Dict with parsed values:
        - model: str or None (None = use agent default)
    """
    result = {
        "model": None  # None = use configured default per agent
    }

    if not args:
        return result

    args = args.strip()

    # Parse --model or -m flag
    model_match = re.search(r'(?:--model|-m)\s+(haiku|sonnet|opus)', args, re.IGNORECASE)
    if model_match:
        result["model"] = model_match.group(1).lower()

    return result


# =============================================================================
# Generic Flag Utilities
# =============================================================================

def has_flag(args: str, short: str, long: str) -> bool:
    """Check if a flag is present in arguments.

    Args:
        args: Raw argument string
        short: Short flag (e.g., "-p")
        long: Long flag (e.g., "--power")

    Returns:
        True if flag is present
    """
    if not args:
        return False

    # Check short flag (must be followed by space or end)
    if short and re.search(rf'\s{re.escape(short)}(?:\s|$)', f" {args}"):
        return True

    # Check long flag
    if long and re.search(rf'{re.escape(long)}(?:\s|$)', args):
        return True

    return False


def get_flag_value(args: str, flag: str) -> Optional[str]:
    """Get the value of a flag.

    Args:
        args: Raw argument string
        flag: Flag name (e.g., "--label", "-l")

    Returns:
        Flag value or None if not found
    """
    if not args:
        return None

    match = re.search(rf'{re.escape(flag)}\s+(\S+)', args)
    if match:
        return match.group(1)

    return None


def extract_issue_number(text: str) -> Optional[int]:
    """Extract issue number from various formats.

    Formats supported:
        #4, gh-4, gh4, issue 4, 4

    Args:
        text: Text containing issue reference

    Returns:
        Issue number as int or None
    """
    if not text:
        return None

    # Try various patterns
    patterns = [
        r'#(\d+)',           # #4
        r'gh-?(\d+)',        # gh-4, gh4
        r'issue\s*(\d+)',    # issue 4
        r'^(\d+)$',          # just 4
        r'\s(\d+)(?:\s|$)',  # 4 surrounded by spaces
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    # Test parse_work_args
    print("Testing parse_work_args:")
    test_cases = [
        "#4",
        "gh-4",
        "4 -p",
        "#4 --power",
        "#4 --solo",
        "#4 -p --phases explore,implement,test",
        "#4 --agents reviewer,tester",
        "#4 --power --solo",  # Should error
        "",  # Should error
    ]

    for test in test_cases:
        result = parse_work_args(test)
        print(f"  '{test}' -> {result}")

    print("\nTesting parse_issues_args:")
    test_cases = [
        "",
        "--power",
        "-p",
        "--label bug",
        "-l feature --state all",
        "--assignee @me -n 10",
    ]

    for test in test_cases:
        result = parse_issues_args(test)
        print(f"  '{test}' -> {result}")

    print("\nTesting parse_power_args:")
    test_cases = [
        "status",
        "stop",
        '"Build user auth"',
        '"Refactor DB" --phases design,implement',
        '"Security audit" --agents security-auditor --timeout 45',
    ]

    for test in test_cases:
        result = parse_power_args(test)
        print(f"  '{test}' -> {result}")

    print("\nTesting parse_thinking_flags:")
    test_cases = [
        "",
        "-T",
        "--thinking",
        "--no-thinking",
        "-T --think-budget 20000",
        "#4 -p -T",  # Combined with other flags
    ]

    for test in test_cases:
        result = parse_thinking_flags(test)
        print(f"  '{test}' -> {result}")

    print("\nTesting parse_model_flag:")
    test_cases = [
        "",
        "--model haiku",
        "--model sonnet",
        "--model opus",
        "-m opus",
        "#4 -p --model opus",  # Combined with other flags
        "--model HAIKU",  # Case insensitive
    ]

    for test in test_cases:
        result = parse_model_flag(test)
        print(f"  '{test}' -> {result}")
