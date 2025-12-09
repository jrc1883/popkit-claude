#!/usr/bin/env python3
"""
PopKit Plugin Test Runner

Comprehensive test runner for validating all plugin components:
- Commands
- Skills
- Agents (routing)
- Hooks
- Structure

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --category structure
    python run_tests.py --category routing
    python run_tests.py --verbose
    python run_tests.py --json

Part of Issue #105 (Comprehensive Test Suite)
"""

import json
import sys
import os
import re
import glob
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    category: str
    message: str = ""
    duration_ms: float = 0


@dataclass
class TestSummary:
    """Summary of all test results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = field(default_factory=list)
    duration_ms: float = 0


# Get the plugin root directory
PLUGIN_ROOT = Path(__file__).parent.parent
TESTS_DIR = Path(__file__).parent


def load_json_file(filepath: Path) -> Dict:
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except FileNotFoundError:
        return {"error": "File not found"}


def run_structure_tests() -> List[TestResult]:
    """Run plugin structure tests."""
    results = []
    test_file = TESTS_DIR / "structure" / "test-plugin-structure.json"

    if not test_file.exists():
        return [TestResult(
            name="load structure tests",
            passed=False,
            category="structure",
            message="Test file not found"
        )]

    config = load_json_file(test_file)
    if "error" in config:
        return [TestResult(
            name="load structure tests",
            passed=False,
            category="structure",
            message=config["error"]
        )]

    for test in config.get("tests", []):
        test_name = test.get("name", "unnamed test")
        test_type = test.get("type", "")
        path = test.get("path", "")

        if test_type == "file_exists":
            full_path = PLUGIN_ROOT / path
            exists = full_path.exists()

            if exists and test.get("must_be_valid_json"):
                content = load_json_file(full_path)
                if "error" in content:
                    results.append(TestResult(
                        name=test_name,
                        passed=False,
                        category="structure",
                        message=content["error"]
                    ))
                    continue

            results.append(TestResult(
                name=test_name,
                passed=exists,
                category="structure",
                message="" if exists else f"File not found: {path}"
            ))

        elif test_type == "directory_pattern":
            matches = list(PLUGIN_ROOT.glob(path))
            count = len(matches)
            min_count = test.get("min_count", 0)
            expected_count = test.get("expected_count")

            passed = count >= min_count
            message = f"Found {count} files"
            if expected_count and count != expected_count:
                message += f" (expected {expected_count})"

            results.append(TestResult(
                name=test_name,
                passed=passed,
                category="structure",
                message=message
            ))

    return results


def run_routing_tests() -> List[TestResult]:
    """Run agent routing tests."""
    results = []
    test_file = TESTS_DIR / "routing" / "test-agent-routing.json"

    if not test_file.exists():
        return [TestResult(
            name="load routing tests",
            passed=False,
            category="routing",
            message="Test file not found"
        )]

    config = load_json_file(test_file)
    if "error" in config:
        return [TestResult(
            name="load routing tests",
            passed=False,
            category="routing",
            message=config["error"]
        )]

    # Load agent config
    agent_config_path = PLUGIN_ROOT / "agents" / "config.json"
    agent_config = load_json_file(agent_config_path)
    if "error" in agent_config:
        return [TestResult(
            name="load agent config",
            passed=False,
            category="routing",
            message=agent_config["error"]
        )]

    keywords_map = agent_config.get("routing", {}).get("keywords", {})
    file_patterns = agent_config.get("routing", {}).get("filePatterns", {})
    error_patterns = agent_config.get("routing", {}).get("errorPatterns", {})

    # Test keyword routing
    for test in config.get("keyword_tests", []):
        test_name = test.get("name", "unnamed test")
        prompt = test.get("prompt", "").lower()
        expected_agent = test.get("expected_agent", "")

        # Check if any keyword matches
        matched_agents = []
        for keyword, agents in keywords_map.items():
            if keyword.lower() in prompt:
                matched_agents.extend(agents)

        passed = expected_agent in matched_agents
        results.append(TestResult(
            name=test_name,
            passed=passed,
            category="routing",
            message="" if passed else f"Expected {expected_agent}, matched {matched_agents}"
        ))

    # Test file pattern routing
    for test in config.get("file_pattern_tests", []):
        test_name = test.get("name", "unnamed test")
        pattern = test.get("pattern", "")
        expected = test.get("expected_agent") or test.get("expected_agents", [])
        if isinstance(expected, str):
            expected = [expected]

        # Find agents for this pattern
        matched_agents = file_patterns.get(pattern, [])

        # Check if expected agents are in matched
        passed = any(agent in matched_agents for agent in expected)
        results.append(TestResult(
            name=test_name,
            passed=passed,
            category="routing",
            message="" if passed else f"Expected {expected}, got {matched_agents}"
        ))

    # Test error pattern routing
    for test in config.get("error_pattern_tests", []):
        test_name = test.get("name", "unnamed test")
        pattern = test.get("pattern", "")
        expected_agent = test.get("expected_agent", "")

        matched_agents = error_patterns.get(pattern, [])
        passed = expected_agent in matched_agents
        results.append(TestResult(
            name=test_name,
            passed=passed,
            category="routing",
            message="" if passed else f"Expected {expected_agent}, got {matched_agents}"
        ))

    return results


def run_command_tests() -> List[TestResult]:
    """Run command structure tests."""
    results = []
    test_file = TESTS_DIR / "commands" / "test-command-structure.json"

    if not test_file.exists():
        return [TestResult(
            name="load command tests",
            passed=False,
            category="commands",
            message="Test file not found"
        )]

    config = load_json_file(test_file)
    if "error" in config:
        return [TestResult(
            name="load command tests",
            passed=False,
            category="commands",
            message=config["error"]
        )]

    for test in config.get("tests", []):
        test_name = test.get("name", "unnamed test")
        command_file = test.get("file", "")
        required_sections = test.get("required_sections", [])

        # Check file exists
        full_path = PLUGIN_ROOT / command_file
        if not full_path.exists():
            results.append(TestResult(
                name=test_name,
                passed=False,
                category="commands",
                message=f"File not found: {command_file}"
            ))
            continue

        # Check for required sections
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            missing_sections = []
            for section in required_sections:
                if f"## {section}" not in content and f"# {section}" not in content:
                    missing_sections.append(section)

            if missing_sections:
                results.append(TestResult(
                    name=test_name,
                    passed=False,
                    category="commands",
                    message=f"Missing sections: {missing_sections}"
                ))
            else:
                results.append(TestResult(
                    name=test_name,
                    passed=True,
                    category="commands"
                ))
        except Exception as e:
            results.append(TestResult(
                name=test_name,
                passed=False,
                category="commands",
                message=str(e)
            ))

    return results


def run_skill_tests() -> List[TestResult]:
    """Run skill structure tests."""
    results = []
    test_file = TESTS_DIR / "skills" / "test-skill-structure.json"

    if not test_file.exists():
        return [TestResult(
            name="load skill tests",
            passed=False,
            category="skills",
            message="Test file not found"
        )]

    config = load_json_file(test_file)
    if "error" in config:
        return [TestResult(
            name="load skill tests",
            passed=False,
            category="skills",
            message=config["error"]
        )]

    for test in config.get("tests", []):
        test_name = test.get("name", "unnamed test")
        skill_file = test.get("file", "")
        description_pattern = test.get("description_pattern", "")

        # Check file exists
        full_path = PLUGIN_ROOT / skill_file
        if not full_path.exists():
            results.append(TestResult(
                name=test_name,
                passed=False,
                category="skills",
                message=f"File not found: {skill_file}"
            ))
            continue

        # Check for frontmatter with description
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for YAML frontmatter
            if not content.startswith('---'):
                results.append(TestResult(
                    name=test_name,
                    passed=False,
                    category="skills",
                    message="Missing YAML frontmatter"
                ))
                continue

            # Extract frontmatter
            parts = content.split('---', 2)
            if len(parts) < 3:
                results.append(TestResult(
                    name=test_name,
                    passed=False,
                    category="skills",
                    message="Invalid frontmatter format"
                ))
                continue

            frontmatter = parts[1]

            # Check for description
            if 'description:' not in frontmatter:
                results.append(TestResult(
                    name=test_name,
                    passed=False,
                    category="skills",
                    message="Missing description in frontmatter"
                ))
                continue

            results.append(TestResult(
                name=test_name,
                passed=True,
                category="skills"
            ))

        except Exception as e:
            results.append(TestResult(
                name=test_name,
                passed=False,
                category="skills",
                message=str(e)
            ))

    return results


def run_hook_tests() -> List[TestResult]:
    """Run hook inventory tests."""
    results = []
    test_file = TESTS_DIR / "hooks" / "test-hook-inventory.json"

    if not test_file.exists():
        return [TestResult(
            name="load hook tests",
            passed=False,
            category="hooks",
            message="Test file not found"
        )]

    config = load_json_file(test_file)
    if "error" in config:
        return [TestResult(
            name="load hook tests",
            passed=False,
            category="hooks",
            message=config["error"]
        )]

    for hook in config.get("hooks", []):
        hook_name = hook.get("name", "unnamed hook")
        hook_file = hook.get("file", "")

        # Check file exists
        full_path = PLUGIN_ROOT / hook_file
        exists = full_path.exists()

        if not exists:
            results.append(TestResult(
                name=f"hook {hook_name} exists",
                passed=False,
                category="hooks",
                message=f"File not found: {hook_file}"
            ))
            continue

        # Check for valid Python shebang
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            valid_shebang = first_line == "#!/usr/bin/env python3"
            results.append(TestResult(
                name=f"hook {hook_name} has valid shebang",
                passed=valid_shebang,
                category="hooks",
                message="" if valid_shebang else f"Invalid shebang: {first_line}"
            ))
        except Exception as e:
            results.append(TestResult(
                name=f"hook {hook_name} readable",
                passed=False,
                category="hooks",
                message=str(e)
            ))

    return results


def print_results(summary: TestSummary, verbose: bool = False):
    """Print test results to console."""
    print("\n" + "=" * 60)
    print("PopKit Plugin Test Results")
    print("=" * 60)

    # Group by category
    by_category: Dict[str, List[TestResult]] = {}
    for result in summary.results:
        if result.category not in by_category:
            by_category[result.category] = []
        by_category[result.category].append(result)

    for category, results in by_category.items():
        print(f"\n[{category.upper()}]")
        for result in results:
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"  {status} {result.name}")
            if not result.passed and result.message:
                print(f"         {result.message}")

    print("\n" + "-" * 60)
    print(f"Results: {summary.passed} passed, {summary.failed} failed, {summary.skipped} skipped")
    print(f"Duration: {summary.duration_ms:.1f}ms")
    print("-" * 60 + "\n")


def save_results(summary: TestSummary, output_path: Path):
    """Save results to JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "duration_ms": summary.duration_ms
        },
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "category": r.category,
                "message": r.message
            }
            for r in summary.results
        ]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="PopKit Plugin Test Runner")
    parser.add_argument("--category", choices=["structure", "routing", "commands", "skills", "hooks"],
                       help="Run only specific category of tests")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    start_time = datetime.now()

    # Run tests based on category
    all_results: List[TestResult] = []

    categories = [args.category] if args.category else ["structure", "routing", "commands", "skills", "hooks"]

    for category in categories:
        if category == "structure":
            all_results.extend(run_structure_tests())
        elif category == "routing":
            all_results.extend(run_routing_tests())
        elif category == "commands":
            all_results.extend(run_command_tests())
        elif category == "skills":
            all_results.extend(run_skill_tests())
        elif category == "hooks":
            all_results.extend(run_hook_tests())

    # Calculate summary
    duration = (datetime.now() - start_time).total_seconds() * 1000
    summary = TestSummary(
        total=len(all_results),
        passed=sum(1 for r in all_results if r.passed),
        failed=sum(1 for r in all_results if not r.passed),
        results=all_results,
        duration_ms=duration
    )

    # Output results
    if args.json:
        output = {
            "summary": {
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "duration_ms": summary.duration_ms
            },
            "results": [
                {"name": r.name, "passed": r.passed, "category": r.category, "message": r.message}
                for r in summary.results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print_results(summary, args.verbose)

    # Save results
    results_dir = TESTS_DIR / "results"
    save_results(summary, results_dir / "latest.json")

    # Exit with appropriate code
    sys.exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    main()
