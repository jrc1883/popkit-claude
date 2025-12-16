#!/usr/bin/env python3
"""
PopKit Behavior Test Runner

Tests PopKit's orchestration BEHAVIOR (not just output):
- Did the right agent get invoked?
- Were the right tools used?
- Did workflows execute in the correct order?
- Were skills suggested appropriately?

Usage:
    python run_behavior_tests.py                    # Run all behavior tests
    python run_behavior_tests.py --record           # Record new behavior snapshots
    python run_behavior_tests.py --test routing    # Run specific test category
    python run_behavior_tests.py --verbose          # Show detailed output

Part of Issue #258 (PopKit Self-Testing Framework)
"""

import json
import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BehaviorTrace:
    """Recorded trace of PopKit behavior during a test."""
    timestamp: str
    test_name: str
    prompt: str
    agents_invoked: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    skills_suggested: List[str] = field(default_factory=list)
    workflow_phases: List[str] = field(default_factory=list)
    user_interactions: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0


@dataclass
class BehaviorTestResult:
    """Result of a behavior test."""
    name: str
    passed: bool
    category: str
    message: str = ""
    trace: Optional[BehaviorTrace] = None


# Directory paths
TESTS_DIR = Path(__file__).parent
PLUGIN_ROOT = TESTS_DIR.parent.parent
RECORDINGS_DIR = TESTS_DIR / "recordings"
SNAPSHOTS_DIR = TESTS_DIR / "snapshots"

# Ensure directories exist
RECORDINGS_DIR.mkdir(exist_ok=True)
SNAPSHOTS_DIR.mkdir(exist_ok=True)


def load_test_definitions() -> Dict:
    """Load behavior test definitions."""
    test_file = TESTS_DIR / "test-orchestration-behavior.json"
    if not test_file.exists():
        print(f"Error: Test definitions not found at {test_file}")
        sys.exit(1)

    with open(test_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def record_behavior(test_name: str, prompt: str, args: argparse.Namespace) -> BehaviorTrace:
    """
    Record PopKit behavior by running a command and capturing agent invocations.

    This is a STUB implementation - full implementation requires:
    1. Hook integration to intercept tool calls
    2. Agent tracking in pre-tool-use/post-tool-use hooks
    3. Trace serialization to JSON

    For now, returns a mock trace structure.
    """
    trace = BehaviorTrace(
        timestamp=datetime.now().isoformat(),
        test_name=test_name,
        prompt=prompt
    )

    if args.verbose:
        print(f"[RECORD] Test: {test_name}")
        print(f"[RECORD] Prompt: {prompt}")
        print("[RECORD] Note: Behavior recording requires hook integration (not yet implemented)")

    # TODO: Implement actual recording via hooks
    # This would involve:
    # 1. Running Claude Code with the prompt
    # 2. Hooks capture agent invocations, tool usage, etc.
    # 3. Parse hook output to build the trace

    return trace


def assert_agent_invoked(trace: BehaviorTrace, expected_agent: str) -> bool:
    """Assert that a specific agent was invoked."""
    return expected_agent in trace.agents_invoked


def assert_tools_used(trace: BehaviorTrace, expected_tools: List[str]) -> bool:
    """Assert that specific tools were used."""
    return all(tool in trace.tools_used for tool in expected_tools)


def assert_skill_suggested(trace: BehaviorTrace, expected_skill: str) -> bool:
    """Assert that a specific skill was suggested."""
    return expected_skill in trace.skills_suggested


def run_routing_behavior_tests(definitions: Dict, args: argparse.Namespace) -> List[BehaviorTestResult]:
    """Run routing behavior tests."""
    results = []
    tests = definitions.get("routing_behavior_tests", [])

    for test in tests:
        name = test["name"]
        prompt = test["prompt"]
        expected = test["expected_behavior"]

        if args.verbose:
            print(f"\nRunning: {name}")
            print(f"Prompt: {prompt}")

        if args.record:
            # Record actual behavior
            trace = record_behavior(name, prompt, args)

            # Save snapshot
            snapshot_file = SNAPSHOTS_DIR / f"{name.replace(' ', '-')}.json"
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "test": name,
                    "trace": trace.__dict__
                }, f, indent=2)

            if args.verbose:
                print(f"Snapshot saved: {snapshot_file}")

        # For now, mark as skipped since recording not implemented
        results.append(BehaviorTestResult(
            name=name,
            passed=False,
            category="routing_behavior",
            message="Skipped: Behavior recording not yet implemented (requires hook integration)"
        ))

    return results


def run_agent_invocation_tests(definitions: Dict, args: argparse.Namespace) -> List[BehaviorTestResult]:
    """Run agent invocation behavior tests."""
    results = []
    tests = definitions.get("agent_invocation_tests", [])

    for test in tests:
        name = test["name"]

        # Skipped for now - requires implementation
        results.append(BehaviorTestResult(
            name=name,
            passed=False,
            category="agent_invocation",
            message="Skipped: Not yet implemented"
        ))

    return results


def run_workflow_execution_tests(definitions: Dict, args: argparse.Namespace) -> List[BehaviorTestResult]:
    """Run workflow execution behavior tests."""
    results = []
    tests = definitions.get("workflow_execution_tests", [])

    for test in tests:
        name = test["name"]

        # Skipped for now - requires implementation
        results.append(BehaviorTestResult(
            name=name,
            passed=False,
            category="workflow_execution",
            message="Skipped: Not yet implemented"
        ))

    return results


def print_summary(results: List[BehaviorTestResult]):
    """Print test summary."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed and "Skipped" not in r.message)
    skipped = sum(1 for r in results if "Skipped" in r.message)

    print("\n" + "="*60)
    print("BEHAVIOR TEST SUMMARY")
    print("="*60)
    print(f"Total:   {total}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}")
    print("="*60)

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r.passed and "Skipped" not in r.message:
                print(f"  - {r.name}: {r.message}")


def main():
    parser = argparse.ArgumentParser(description="Run PopKit behavior tests")
    parser.add_argument("--record", action="store_true", help="Record new behavior snapshots")
    parser.add_argument("--test", type=str, help="Run specific test category")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("PopKit Behavior Test Runner")
    print(f"Issue: #258 (Self-Testing Framework)")
    print()

    definitions = load_test_definitions()
    all_results = []

    # Run test categories
    if not args.test or args.test == "routing":
        all_results.extend(run_routing_behavior_tests(definitions, args))

    if not args.test or args.test == "invocation":
        all_results.extend(run_agent_invocation_tests(definitions, args))

    if not args.test or args.test == "workflow":
        all_results.extend(run_workflow_execution_tests(definitions, args))

    print_summary(all_results)

    # Exit with non-zero if any tests failed
    failed = sum(1 for r in all_results if not r.passed and "Skipped" not in r.message)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
