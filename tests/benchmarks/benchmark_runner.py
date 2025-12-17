#!/usr/bin/env python3
"""
PopKit Performance Benchmarking Framework

Measures and compares performance across different modes:
- Solo mode (single agent)
- Power Mode (file-based)
- Power Mode (cloud)

Part of Issue #106 (Performance Benchmarking Framework)
Parent: Epic #104 (PopKit Quality Assurance & Power Mode Value Proposition)

Usage:
    python benchmark_runner.py                    # Run all benchmarks
    python benchmark_runner.py --scenario simple  # Run specific scenario
    python benchmark_runner.py --mode solo        # Run in specific mode
    python benchmark_runner.py --report           # Generate report only
"""

import json
import time
import os
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class BenchmarkMode(Enum):
    """Execution modes for benchmarks."""
    SOLO = "solo"
    POWER_FILE = "power-file"
    POWER_CLOUD = "power-cloud"


class ScenarioType(Enum):
    """Types of benchmark scenarios."""
    SIMPLE_FIX = "simple-fix"
    FEATURE_IMPL = "feature-impl"
    CODE_REVIEW = "code-review"
    MULTI_REFACTOR = "multi-refactor"
    AGENT_ROUTING = "agent-routing"
    SKILL_INVOCATION = "skill-invocation"
    COMMAND_EXECUTION = "command-execution"


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: str
    tokens_used: int = 0
    context_size: int = 0
    memory_mb: float = 0
    files_read: int = 0
    files_written: int = 0
    tools_called: int = 0
    errors_encountered: int = 0


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    scenario: str
    mode: str
    duration_ms: float
    tokens_used: int
    success: bool
    quality_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class BenchmarkComparison:
    """Comparison across different modes."""
    scenario: str
    results: Dict[str, BenchmarkResult] = field(default_factory=dict)
    winner: str = ""
    speedup_percent: float = 0.0
    quality_improvement: float = 0.0
    token_efficiency: float = 0.0


# =============================================================================
# METRIC COLLECTORS
# =============================================================================

class MetricCollector:
    """Collects various performance metrics."""

    def __init__(self):
        self.start_time: float = 0
        self.start_metrics: MetricSnapshot = None
        self.tool_calls: List[Dict] = []
        self.errors: List[str] = []

    def start(self):
        """Start collecting metrics."""
        self.start_time = time.time()
        self.start_metrics = self._capture_snapshot()
        self.tool_calls = []
        self.errors = []

    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool):
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        if not success:
            self.errors.append(f"Tool {tool_name} failed")

    def stop(self) -> Dict[str, Any]:
        """Stop collecting and return metrics."""
        end_time = time.time()
        end_metrics = self._capture_snapshot()

        return {
            "duration_ms": (end_time - self.start_time) * 1000,
            "tool_calls": len(self.tool_calls),
            "tool_breakdown": self._tool_breakdown(),
            "errors": len(self.errors),
            "error_details": self.errors,
            "start": self.start_metrics.timestamp,
            "end": end_metrics.timestamp
        }

    def _capture_snapshot(self) -> MetricSnapshot:
        """Capture current system state."""
        import psutil
        process = psutil.Process(os.getpid())

        return MetricSnapshot(
            timestamp=datetime.now().isoformat(),
            memory_mb=process.memory_info().rss / 1024 / 1024
        )

    def _tool_breakdown(self) -> Dict[str, int]:
        """Get breakdown of tool calls by type."""
        breakdown = {}
        for call in self.tool_calls:
            tool = call["tool"]
            breakdown[tool] = breakdown.get(tool, 0) + 1
        return breakdown


# =============================================================================
# BENCHMARK SCENARIOS
# =============================================================================

class BenchmarkScenario:
    """Base class for benchmark scenarios."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.collector = MetricCollector()

    def setup(self):
        """Setup before running the benchmark."""
        pass

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run the benchmark in specified mode."""
        raise NotImplementedError

    def teardown(self):
        """Cleanup after the benchmark."""
        pass

    def assess_quality(self, result: Any) -> float:
        """Assess quality of the result (0-10 scale)."""
        return 5.0  # Default middle score


class AgentRoutingBenchmark(BenchmarkScenario):
    """Benchmark agent routing performance."""

    def __init__(self):
        super().__init__(
            name="agent-routing",
            description="Measure agent routing speed and accuracy"
        )
        self.test_prompts = [
            ("fix this bug", "bug-whisperer"),
            ("review this code", "code-reviewer"),
            ("check security", "security-auditor"),
            ("optimize performance", "performance-optimizer"),
            ("write tests", "test-writer-fixer"),
            ("design an API", "api-designer"),
            ("refactor this", "refactoring-expert"),
            ("update docs", "documentation-maintainer"),
            ("optimize query", "query-optimizer"),
            ("check accessibility", "accessibility-guardian"),
        ]

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run routing benchmark."""
        self.collector.start()
        started_at = datetime.now().isoformat()

        # Load routing config
        config_path = Path(__file__).parent.parent.parent / "agents" / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)

        keywords_map = config.get("routing", {}).get("keywords", {})

        correct = 0
        total = len(self.test_prompts)

        for prompt, expected_agent in self.test_prompts:
            start = time.time()

            # Simulate routing
            matched_agents = []
            for keyword, agents in keywords_map.items():
                if keyword.lower() in prompt.lower():
                    matched_agents.extend(agents)

            duration = (time.time() - start) * 1000
            success = expected_agent in matched_agents

            self.collector.record_tool_call("route_agent", duration, success)

            if success:
                correct += 1

        metrics = self.collector.stop()
        completed_at = datetime.now().isoformat()

        accuracy = correct / total if total > 0 else 0

        return BenchmarkResult(
            scenario=self.name,
            mode=mode.value,
            duration_ms=metrics["duration_ms"],
            tokens_used=0,  # No tokens for routing
            success=accuracy >= 0.8,
            quality_score=accuracy * 10,
            errors=metrics["error_details"],
            metrics={
                "accuracy": accuracy,
                "correct": correct,
                "total": total,
                "avg_routing_time_ms": metrics["duration_ms"] / total if total > 0 else 0
            },
            started_at=started_at,
            completed_at=completed_at
        )


class SkillInvocationBenchmark(BenchmarkScenario):
    """Benchmark skill loading and invocation."""

    def __init__(self):
        super().__init__(
            name="skill-invocation",
            description="Measure skill file loading and parsing"
        )

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run skill loading benchmark."""
        self.collector.start()
        started_at = datetime.now().isoformat()

        skills_dir = Path(__file__).parent.parent.parent / "skills"
        skill_dirs = list(skills_dir.glob("*/SKILL.md"))

        loaded = 0
        total = len(skill_dirs)
        load_times = []

        for skill_path in skill_dirs:
            start = time.time()

            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for valid frontmatter
                has_frontmatter = content.startswith('---')
                duration = (time.time() - start) * 1000
                load_times.append(duration)

                self.collector.record_tool_call("load_skill", duration, has_frontmatter)

                if has_frontmatter:
                    loaded += 1
            except Exception as e:
                self.collector.errors.append(str(e))

        metrics = self.collector.stop()
        completed_at = datetime.now().isoformat()

        return BenchmarkResult(
            scenario=self.name,
            mode=mode.value,
            duration_ms=metrics["duration_ms"],
            tokens_used=0,
            success=loaded == total,
            quality_score=(loaded / total * 10) if total > 0 else 0,
            errors=metrics["error_details"],
            metrics={
                "skills_loaded": loaded,
                "skills_total": total,
                "avg_load_time_ms": sum(load_times) / len(load_times) if load_times else 0,
                "max_load_time_ms": max(load_times) if load_times else 0,
                "min_load_time_ms": min(load_times) if load_times else 0
            },
            started_at=started_at,
            completed_at=completed_at
        )


class CommandExecutionBenchmark(BenchmarkScenario):
    """Benchmark command file loading."""

    def __init__(self):
        super().__init__(
            name="command-execution",
            description="Measure command loading and parsing"
        )

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run command loading benchmark."""
        self.collector.start()
        started_at = datetime.now().isoformat()

        commands_dir = Path(__file__).parent.parent.parent / "commands"
        command_files = list(commands_dir.glob("*.md"))

        loaded = 0
        total = len(command_files)
        sizes = []

        for cmd_path in command_files:
            start = time.time()

            try:
                with open(cmd_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                sizes.append(len(content))
                duration = (time.time() - start) * 1000

                self.collector.record_tool_call("load_command", duration, True)
                loaded += 1
            except Exception as e:
                self.collector.errors.append(str(e))

        metrics = self.collector.stop()
        completed_at = datetime.now().isoformat()

        return BenchmarkResult(
            scenario=self.name,
            mode=mode.value,
            duration_ms=metrics["duration_ms"],
            tokens_used=0,
            success=loaded == total,
            quality_score=(loaded / total * 10) if total > 0 else 0,
            errors=metrics["error_details"],
            metrics={
                "commands_loaded": loaded,
                "commands_total": total,
                "total_size_bytes": sum(sizes),
                "avg_size_bytes": sum(sizes) / len(sizes) if sizes else 0
            },
            started_at=started_at,
            completed_at=completed_at
        )


class HookExecutionBenchmark(BenchmarkScenario):
    """Benchmark hook execution speed."""

    def __init__(self):
        super().__init__(
            name="hook-execution",
            description="Measure hook response times"
        )

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run hook execution benchmark."""
        self.collector.start()
        started_at = datetime.now().isoformat()

        hooks_dir = Path(__file__).parent.parent.parent / "hooks"
        hook_files = list(hooks_dir.glob("*.py"))

        # Filter out __init__ and test files
        hook_files = [h for h in hook_files if not h.name.startswith('__')]

        valid = 0
        total = len(hook_files)

        for hook_path in hook_files:
            start = time.time()

            try:
                with open(hook_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()

                has_shebang = first_line == "#!/usr/bin/env python3"
                duration = (time.time() - start) * 1000

                self.collector.record_tool_call("check_hook", duration, has_shebang)

                if has_shebang:
                    valid += 1
            except Exception as e:
                self.collector.errors.append(str(e))

        metrics = self.collector.stop()
        completed_at = datetime.now().isoformat()

        return BenchmarkResult(
            scenario=self.name,
            mode=mode.value,
            duration_ms=metrics["duration_ms"],
            tokens_used=0,
            success=valid == total,
            quality_score=(valid / total * 10) if total > 0 else 0,
            errors=metrics["error_details"],
            metrics={
                "hooks_valid": valid,
                "hooks_total": total,
                "validation_rate": valid / total if total > 0 else 0
            },
            started_at=started_at,
            completed_at=completed_at
        )


class ConfigLoadBenchmark(BenchmarkScenario):
    """Benchmark config file loading."""

    def __init__(self):
        super().__init__(
            name="config-load",
            description="Measure config file loading speed"
        )

    def run(self, mode: BenchmarkMode) -> BenchmarkResult:
        """Run config loading benchmark."""
        self.collector.start()
        started_at = datetime.now().isoformat()

        plugin_root = Path(__file__).parent.parent.parent
        config_files = [
            plugin_root / "agents" / "config.json",
            plugin_root / "hooks" / "hooks.json",
            plugin_root / ".claude-plugin" / "plugin.json",
            plugin_root / ".claude-plugin" / "marketplace.json",
            plugin_root / ".mcp.json",
            plugin_root / "power-mode" / "config.json"
        ]

        loaded = 0
        total = len(config_files)
        sizes = []

        for config_path in config_files:
            start = time.time()

            try:
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    sizes.append(config_path.stat().st_size)
                    duration = (time.time() - start) * 1000

                    self.collector.record_tool_call("load_config", duration, True)
                    loaded += 1
            except Exception as e:
                self.collector.errors.append(f"{config_path.name}: {e}")

        metrics = self.collector.stop()
        completed_at = datetime.now().isoformat()

        return BenchmarkResult(
            scenario=self.name,
            mode=mode.value,
            duration_ms=metrics["duration_ms"],
            tokens_used=0,
            success=loaded == total,
            quality_score=(loaded / total * 10) if total > 0 else 0,
            errors=metrics["error_details"],
            metrics={
                "configs_loaded": loaded,
                "configs_total": total,
                "total_size_bytes": sum(sizes),
                "avg_load_time_ms": metrics["duration_ms"] / loaded if loaded > 0 else 0
            },
            started_at=started_at,
            completed_at=completed_at
        )


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

class BenchmarkRunner:
    """Main benchmark runner."""

    def __init__(self):
        self.scenarios: Dict[str, BenchmarkScenario] = {
            "agent-routing": AgentRoutingBenchmark(),
            "skill-invocation": SkillInvocationBenchmark(),
            "command-execution": CommandExecutionBenchmark(),
            "hook-execution": HookExecutionBenchmark(),
            "config-load": ConfigLoadBenchmark(),
        }
        self.results: List[BenchmarkResult] = []
        self.results_dir = Path(__file__).parent / "results"

    def run_scenario(self, scenario_name: str, mode: BenchmarkMode) -> BenchmarkResult:
        """Run a specific scenario."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        scenario = self.scenarios[scenario_name]
        scenario.setup()

        try:
            result = scenario.run(mode)
            self.results.append(result)
            return result
        finally:
            scenario.teardown()

    def run_all(self, mode: BenchmarkMode = BenchmarkMode.SOLO) -> List[BenchmarkResult]:
        """Run all benchmarks."""
        results = []
        for name in self.scenarios:
            result = self.run_scenario(name, mode)
            results.append(result)
        return results

    def compare_modes(self, scenario_name: str) -> BenchmarkComparison:
        """Compare a scenario across all modes."""
        comparison = BenchmarkComparison(scenario=scenario_name)

        for mode in BenchmarkMode:
            result = self.run_scenario(scenario_name, mode)
            comparison.results[mode.value] = result

        # Determine winner (fastest with quality >= 7)
        valid_results = {
            k: v for k, v in comparison.results.items()
            if v.success and v.quality_score >= 7
        }

        if valid_results:
            winner = min(valid_results.items(), key=lambda x: x[1].duration_ms)
            comparison.winner = winner[0]

            # Calculate improvements vs solo
            solo_result = comparison.results.get("solo")
            if solo_result and comparison.winner != "solo":
                winner_result = comparison.results[comparison.winner]
                comparison.speedup_percent = (
                    (solo_result.duration_ms - winner_result.duration_ms)
                    / solo_result.duration_ms * 100
                )
                comparison.quality_improvement = (
                    winner_result.quality_score - solo_result.quality_score
                )

        return comparison

    def generate_report(self) -> str:
        """Generate a markdown report of all results."""
        report = ["# PopKit Performance Benchmark Report\n"]
        report.append(f"**Generated:** {datetime.now().isoformat()}\n")
        report.append(f"**Total Scenarios:** {len(self.results)}\n\n")

        # Summary table
        report.append("## Summary\n\n")
        report.append("| Scenario | Mode | Duration (ms) | Quality | Status |\n")
        report.append("|----------|------|---------------|---------|--------|\n")

        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            report.append(
                f"| {result.scenario} | {result.mode} | "
                f"{result.duration_ms:.2f} | {result.quality_score:.1f}/10 | {status} |\n"
            )

        # Detailed results
        report.append("\n## Detailed Results\n\n")

        for result in self.results:
            report.append(f"### {result.scenario} ({result.mode})\n\n")
            report.append(f"- **Duration:** {result.duration_ms:.2f}ms\n")
            report.append(f"- **Quality Score:** {result.quality_score:.1f}/10\n")
            report.append(f"- **Success:** {'Yes' if result.success else 'No'}\n")

            if result.metrics:
                report.append("\n**Metrics:**\n")
                for key, value in result.metrics.items():
                    report.append(f"- {key}: {value}\n")

            if result.errors:
                report.append("\n**Errors:**\n")
                for error in result.errors:
                    report.append(f"- {error}\n")

            report.append("\n")

        return "".join(report)

    def save_results(self):
        """Save results to JSON file."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Save latest results
        output = {
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in self.results]
        }

        with open(self.results_dir / "benchmark-latest.json", 'w') as f:
            json.dump(output, f, indent=2)

        # Save markdown report
        report = self.generate_report()
        with open(self.results_dir / "benchmark-report.md", 'w') as f:
            f.write(report)


def main():
    parser = argparse.ArgumentParser(description="PopKit Performance Benchmarks")
    parser.add_argument("--scenario", help="Run specific scenario")
    parser.add_argument("--mode", choices=["solo", "power-file", "power-cloud"],
                       default="solo", help="Benchmark mode")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--compare", action="store_true", help="Compare all modes")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    runner = BenchmarkRunner()

    try:
        if args.report:
            # Load existing results
            results_file = runner.results_dir / "benchmark-latest.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    data = json.load(f)
                for r in data["results"]:
                    runner.results.append(BenchmarkResult(**r))
                print(runner.generate_report())
            else:
                print("No results found. Run benchmarks first.")
            return

        mode = BenchmarkMode(args.mode)

        if args.all or (not args.scenario):
            results = runner.run_all(mode)
        elif args.scenario:
            results = [runner.run_scenario(args.scenario, mode)]
        else:
            results = runner.run_all(mode)

        runner.save_results()

        if args.json:
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            print(runner.generate_report())

        # Exit with error if any benchmark failed
        if any(not r.success for r in results):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
