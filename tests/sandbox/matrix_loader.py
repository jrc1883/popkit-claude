#!/usr/bin/env python3
"""
Test Matrix Loader - Utilities for loading and filtering test definitions.

Part of Issue #230: Test Matrix Definition

Usage:
    python matrix_loader.py                    # List all tests
    python matrix_loader.py --suite smoke      # List smoke tests
    python matrix_loader.py --priority P0      # List P0 tests
    python matrix_loader.py --type skill       # List skill tests
    python matrix_loader.py --tags core        # List tests with 'core' tag
    python matrix_loader.py --stats            # Show statistics
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass


@dataclass
class TestCase:
    """Represents a single test case from the matrix."""
    id: str
    name: str
    description: str
    type: str  # skill, command, scenario
    target: Optional[str]
    priority: str
    timeout_seconds: int
    inputs: Dict[str, Any]
    expected: Dict[str, Any]
    tags: List[str]
    setup: Optional[Dict[str, Any]] = None
    cleanup: Optional[Dict[str, Any]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    runner: str = "local"
    requires: Optional[Dict[str, bool]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], defaults: Dict[str, Any]) -> 'TestCase':
        """Create TestCase from dictionary with defaults."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            type=data["type"],
            target=data.get("target"),
            priority=data["priority"],
            timeout_seconds=data.get("timeout_seconds", defaults.get("timeout_seconds", 120)),
            inputs=data.get("inputs", {}),
            expected=data.get("expected", {}),
            tags=data.get("tags", []),
            setup=data.get("setup"),
            cleanup=data.get("cleanup"),
            steps=data.get("steps"),
            runner=data.get("runner", defaults.get("runner", "local")),
            requires=data.get("requires")
        )


class TestMatrix:
    """Loader and filter for the test matrix."""

    def __init__(self, matrix_path: Optional[Path] = None):
        """Load test matrix from file."""
        if matrix_path is None:
            matrix_path = Path(__file__).parent / "test_matrix.json"

        with open(matrix_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        self.version = self._data.get("version", "1.0.0")
        self.defaults = self._data.get("defaults", {})
        self.priority_definitions = self._data.get("priority_definitions", {})
        self.test_suites = self._data.get("test_suites", {})

        # Parse all tests
        self.tests: List[TestCase] = [
            TestCase.from_dict(t, self.defaults)
            for t in self._data.get("tests", [])
        ]

    def get_test(self, test_id: str) -> Optional[TestCase]:
        """Get a specific test by ID."""
        for test in self.tests:
            if test.id == test_id:
                return test
        return None

    def filter_by_priority(self, priorities: List[str]) -> List[TestCase]:
        """Filter tests by priority levels."""
        return [t for t in self.tests if t.priority in priorities]

    def filter_by_type(self, types: List[str]) -> List[TestCase]:
        """Filter tests by type (skill, command, scenario)."""
        return [t for t in self.tests if t.type in types]

    def filter_by_tags(self, tags: List[str], match_all: bool = False) -> List[TestCase]:
        """Filter tests by tags.

        Args:
            tags: List of tags to match
            match_all: If True, test must have all tags. If False, any tag matches.
        """
        results = []
        tag_set = set(tags)
        for test in self.tests:
            test_tags = set(test.tags)
            if match_all:
                if tag_set.issubset(test_tags):
                    results.append(test)
            else:
                if tag_set.intersection(test_tags):
                    results.append(test)
        return results

    def filter_by_runner(self, runner: str) -> List[TestCase]:
        """Filter tests by runner type (local, e2b)."""
        return [t for t in self.tests if t.runner == runner]

    def get_suite(self, suite_name: str) -> List[TestCase]:
        """Get tests for a specific test suite."""
        suite = self.test_suites.get(suite_name)
        if not suite:
            return []

        filter_config = suite.get("filter", {})
        results = self.tests.copy()

        # Apply priority filter
        if "priority" in filter_config:
            results = [t for t in results if t.priority in filter_config["priority"]]

        # Apply type filter
        if "type" in filter_config:
            results = [t for t in results if t.type in filter_config["type"]]

        # Apply tags filter
        if "tags" in filter_config:
            tag_set = set(filter_config["tags"])
            results = [t for t in results if tag_set.intersection(set(t.tags))]

        return results

    def get_all_tags(self) -> Set[str]:
        """Get all unique tags across all tests."""
        tags = set()
        for test in self.tests:
            tags.update(test.tags)
        return tags

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the test matrix."""
        by_priority = {}
        by_type = {}
        by_runner = {}

        for test in self.tests:
            by_priority[test.priority] = by_priority.get(test.priority, 0) + 1
            by_type[test.type] = by_type.get(test.type, 0) + 1
            by_runner[test.runner] = by_runner.get(test.runner, 0) + 1

        return {
            "total_tests": len(self.tests),
            "by_priority": by_priority,
            "by_type": by_type,
            "by_runner": by_runner,
            "all_tags": sorted(self.get_all_tags()),
            "test_suites": list(self.test_suites.keys())
        }


def main():
    """CLI for test matrix operations."""
    parser = argparse.ArgumentParser(description="Test Matrix Loader")
    parser.add_argument("--suite", help="Filter by test suite name")
    parser.add_argument("--priority", help="Filter by priority (P0, P1, P2)")
    parser.add_argument("--type", help="Filter by type (skill, command, scenario)")
    parser.add_argument("--tags", help="Filter by tags (comma-separated)")
    parser.add_argument("--runner", help="Filter by runner (local, e2b)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    matrix = TestMatrix()

    if args.stats:
        stats = matrix.get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("Test Matrix Statistics")
            print("=" * 40)
            print(f"Total tests: {stats['total_tests']}")
            print(f"\nBy Priority:")
            for p, count in sorted(stats['by_priority'].items()):
                print(f"  {p}: {count}")
            print(f"\nBy Type:")
            for t, count in sorted(stats['by_type'].items()):
                print(f"  {t}: {count}")
            print(f"\nBy Runner:")
            for r, count in sorted(stats['by_runner'].items()):
                print(f"  {r}: {count}")
            print(f"\nAll Tags: {', '.join(stats['all_tags'])}")
            print(f"\nTest Suites: {', '.join(stats['test_suites'])}")
        return

    # Apply filters
    tests = matrix.tests

    if args.suite:
        tests = matrix.get_suite(args.suite)
    elif args.priority:
        tests = matrix.filter_by_priority([args.priority])
    elif args.type:
        tests = matrix.filter_by_type([args.type])
    elif args.tags:
        tests = matrix.filter_by_tags(args.tags.split(","))
    elif args.runner:
        tests = matrix.filter_by_runner(args.runner)

    # Output results
    if args.json:
        output = [{"id": t.id, "name": t.name, "type": t.type, "priority": t.priority} for t in tests]
        print(json.dumps(output, indent=2))
    else:
        print(f"Found {len(tests)} tests:")
        print("-" * 60)
        for test in tests:
            print(f"[{test.priority}] {test.id}")
            print(f"      {test.name}")
            print(f"      Type: {test.type} | Target: {test.target or 'N/A'}")
            print()


if __name__ == "__main__":
    main()
