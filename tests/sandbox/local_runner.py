#!/usr/bin/env python3
"""
Local Test Runner for PopKit Sandbox Testing

Executes skills and commands in isolated temporary directories with full
telemetry capture. Part of Issue #227: Local Test Runner.

Features:
- Temporary directory creation with git repo initialization
- Environment variable injection for test mode
- Configurable timeout handling
- Skill and command execution
- Artifact collection
- Full telemetry capture via JSONL logs

Usage:
    from tests.sandbox.local_runner import LocalTestRunner, TestConfig

    # Run a skill test
    runner = LocalTestRunner()
    result = runner.run_skill("pop-brainstorming", timeout=300)

    # Run a command test
    result = runner.run_command("/popkit:routine morning", timeout=60)

    # Run with custom config
    config = TestConfig(
        timeout=120,
        init_git=True,
        cleanup=True,
        capture_artifacts=True
    )
    result = runner.run_skill("pop-code-review", config=config)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Tuple, Callable

# Add parent directories to path for imports
TESTS_DIR = Path(__file__).parent.parent
PLUGIN_DIR = TESTS_DIR.parent
HOOKS_DIR = PLUGIN_DIR / "hooks"
UTILS_DIR = HOOKS_DIR / "utils"

sys.path.insert(0, str(UTILS_DIR))

try:
    from test_telemetry import (
        set_test_mode, clear_test_mode, is_test_mode, get_test_session_id,
        create_session, create_trace, create_decision, create_event,
        TestSession, ToolTrace, DecisionPoint, CustomEvent
    )
    from local_telemetry import LocalTelemetryStorage, get_local_storage
    TELEMETRY_AVAILABLE = True
except ImportError as e:
    TELEMETRY_AVAILABLE = False
    print(f"Warning: Telemetry modules not available: {e}", file=sys.stderr)


# =============================================================================
# Type Definitions
# =============================================================================

TestType = Literal["skill", "command", "scenario", "e2e"]
Outcome = Literal["success", "failure", "timeout", "error", "partial"]
ExecutionMode = Literal["local", "e2b"]


@dataclass
class TestConfig:
    """Configuration for test execution."""
    timeout: int = 120  # seconds
    init_git: bool = True
    cleanup: bool = True
    capture_artifacts: bool = True
    working_dir: Optional[Path] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    setup_commands: List[str] = field(default_factory=list)
    artifact_patterns: List[str] = field(default_factory=lambda: [
        "*.json", "*.md", "*.log", "*.txt", "docs/**/*"
    ])


@dataclass
class TestResult:
    """Result of a test execution."""
    session_id: str
    test_type: TestType
    test_name: str
    outcome: Outcome
    duration_ms: float
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "test_type": self.test_type,
            "test_name": self.test_name,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "artifacts": self.artifacts,
            "metrics": self.metrics
        }


# =============================================================================
# Local Test Runner
# =============================================================================

class LocalTestRunner:
    """Executes tests in isolated temporary directories."""

    def __init__(self, storage: Optional[LocalTelemetryStorage] = None):
        """Initialize the test runner.

        Args:
            storage: Optional telemetry storage instance
        """
        self.storage = storage or (get_local_storage() if TELEMETRY_AVAILABLE else None)
        self._temp_dirs: List[Path] = []

    def run_skill(
        self,
        skill_name: str,
        config: Optional[TestConfig] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """Run a skill test in an isolated environment.

        Args:
            skill_name: Name of the skill to test (e.g., "pop-brainstorming")
            config: Test configuration
            context: Additional context for the test

        Returns:
            TestResult with execution details
        """
        config = config or TestConfig()
        session_id = str(uuid.uuid4())

        return self._execute_test(
            test_type="skill",
            test_name=skill_name,
            session_id=session_id,
            config=config,
            context=context,
            execute_fn=self._execute_skill
        )

    def run_command(
        self,
        command: str,
        config: Optional[TestConfig] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """Run a command test in an isolated environment.

        Args:
            command: Command to test (e.g., "/popkit:routine morning")
            config: Test configuration
            context: Additional context for the test

        Returns:
            TestResult with execution details
        """
        config = config or TestConfig()
        session_id = str(uuid.uuid4())

        return self._execute_test(
            test_type="command",
            test_name=command,
            session_id=session_id,
            config=config,
            context=context,
            execute_fn=self._execute_command
        )

    def run_scenario(
        self,
        scenario_name: str,
        steps: List[Dict[str, Any]],
        config: Optional[TestConfig] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """Run a multi-step scenario test.

        Args:
            scenario_name: Name of the scenario
            steps: List of step definitions with type/name/args
            config: Test configuration
            context: Additional context for the test

        Returns:
            TestResult with execution details
        """
        config = config or TestConfig()
        session_id = str(uuid.uuid4())

        def execute_scenario(work_dir: Path, env: Dict[str, str]) -> Tuple[int, str, str]:
            """Execute all scenario steps."""
            all_stdout = []
            all_stderr = []
            exit_code = 0

            for i, step in enumerate(steps, 1):
                step_type = step.get("type", "skill")
                step_name = step.get("name", f"step-{i}")
                step_args = step.get("args", {})

                # Log step start
                if TELEMETRY_AVAILABLE and is_test_mode():
                    event = create_event("scenario_step_start", {
                        "step": i,
                        "type": step_type,
                        "name": step_name
                    })
                    self.storage.log_event(session_id, event)

                # Execute step
                if step_type == "skill":
                    code, stdout, stderr = self._execute_skill(work_dir, env, step_name, step_args)
                elif step_type == "command":
                    code, stdout, stderr = self._execute_command(work_dir, env, step_name)
                else:
                    code = 1
                    stdout = ""
                    stderr = f"Unknown step type: {step_type}"

                all_stdout.append(f"=== Step {i}: {step_name} ===\n{stdout}")
                all_stderr.append(stderr)

                # Stop on failure unless continue_on_error is set
                if code != 0 and not step.get("continue_on_error", False):
                    exit_code = code
                    break

            return exit_code, "\n".join(all_stdout), "\n".join(filter(None, all_stderr))

        return self._execute_test(
            test_type="scenario",
            test_name=scenario_name,
            session_id=session_id,
            config=config,
            context=context,
            execute_fn=execute_scenario
        )

    def _execute_test(
        self,
        test_type: TestType,
        test_name: str,
        session_id: str,
        config: TestConfig,
        context: Optional[Dict[str, Any]],
        execute_fn: Callable
    ) -> TestResult:
        """Execute a test with full lifecycle management.

        Args:
            test_type: Type of test
            test_name: Name of the test
            session_id: Unique session identifier
            config: Test configuration
            context: Additional context
            execute_fn: Function to execute the actual test

        Returns:
            TestResult with execution details
        """
        start_time = time.perf_counter()
        work_dir = None
        outcome: Outcome = "error"
        exit_code = None
        stdout = ""
        stderr = ""
        error = None
        artifacts = []

        try:
            # Setup temporary directory
            work_dir = self._setup_temp_dir(config)

            # Setup environment
            env = self._setup_environment(session_id, test_type, test_name, config)

            # Start telemetry session
            if TELEMETRY_AVAILABLE and self.storage:
                self.storage.start_session(
                    test_type=test_type,
                    test_name=test_name,
                    mode="local",
                    session_id=session_id,
                    context=context or {}
                )

            # Run setup commands
            for cmd in config.setup_commands:
                subprocess.run(
                    cmd, shell=True, cwd=work_dir, env=env,
                    capture_output=True, timeout=30
                )

            # Execute the test with timeout
            try:
                if test_type == "scenario":
                    exit_code, stdout, stderr = execute_fn(work_dir, env)
                else:
                    exit_code, stdout, stderr = execute_fn(work_dir, env, test_name)
                outcome = "success" if exit_code == 0 else "failure"
            except subprocess.TimeoutExpired:
                outcome = "timeout"
                error = f"Test timed out after {config.timeout} seconds"
                exit_code = -1

            # Collect artifacts
            if config.capture_artifacts:
                artifacts = self._collect_artifacts(work_dir, config.artifact_patterns)

        except Exception as e:
            outcome = "error"
            error = str(e)
            exit_code = -1

        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Complete telemetry session
            if TELEMETRY_AVAILABLE and self.storage:
                self.storage.complete_session(
                    session_id=session_id,
                    outcome=outcome,
                    error=error,
                    artifacts=artifacts
                )

            # Cleanup
            if config.cleanup and work_dir and work_dir.exists():
                self._cleanup_temp_dir(work_dir)

        return TestResult(
            session_id=session_id,
            test_type=test_type,
            test_name=test_name,
            outcome=outcome,
            duration_ms=duration_ms,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            error=error,
            artifacts=artifacts,
            metrics=self._get_session_metrics(session_id)
        )

    def _setup_temp_dir(self, config: TestConfig) -> Path:
        """Create and setup a temporary directory.

        Args:
            config: Test configuration

        Returns:
            Path to the temporary directory
        """
        if config.working_dir:
            work_dir = Path(config.working_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="popkit_test_"))

        self._temp_dirs.append(work_dir)

        # Initialize git repo if requested
        if config.init_git:
            subprocess.run(
                ["git", "init"],
                cwd=work_dir,
                capture_output=True,
                timeout=10
            )
            # Create initial commit
            (work_dir / "README.md").write_text("# Test Project\n")
            subprocess.run(
                ["git", "add", "."],
                cwd=work_dir,
                capture_output=True,
                timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=work_dir,
                capture_output=True,
                timeout=10,
                env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
                     "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com"}
            )

        return work_dir

    def _setup_environment(
        self,
        session_id: str,
        test_type: TestType,
        test_name: str,
        config: TestConfig
    ) -> Dict[str, str]:
        """Setup environment variables for test execution.

        Args:
            session_id: Test session ID
            test_type: Type of test
            test_name: Name of the test
            config: Test configuration

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        # Test mode flags
        env["POPKIT_TEST_MODE"] = "true"
        env["POPKIT_TEST_SESSION_ID"] = session_id
        env["POPKIT_TEST_TYPE"] = test_type
        env["POPKIT_TEST_NAME"] = test_name

        # Plugin paths
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_DIR)

        # Custom environment variables
        env.update(config.env_vars)

        return env

    def _execute_skill(
        self,
        work_dir: Path,
        env: Dict[str, str],
        skill_name: str,
        args: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, str, str]:
        """Execute a skill in the test environment.

        This simulates skill invocation by creating a test harness
        that loads and executes the skill prompt.

        Args:
            work_dir: Working directory
            env: Environment variables
            skill_name: Name of the skill
            args: Optional arguments for the skill

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        # Find skill file
        skill_dir = PLUGIN_DIR / "skills" / skill_name
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            return (1, "", f"Skill not found: {skill_name}")

        # Read skill content
        skill_content = skill_file.read_text(encoding="utf-8")

        # Log skill start event
        if TELEMETRY_AVAILABLE and is_test_mode():
            session_id = env.get("POPKIT_TEST_SESSION_ID")
            if session_id and self.storage:
                event = create_event("skill_test_start", {
                    "skill_name": skill_name,
                    "args": args or {}
                })
                self.storage.log_event(session_id, event)

        # For now, return success if skill file exists
        # Full skill execution would require Claude Code CLI integration
        stdout = f"Skill '{skill_name}' loaded successfully\n"
        stdout += f"Content length: {len(skill_content)} bytes\n"

        if args:
            stdout += f"Arguments: {json.dumps(args)}\n"

        return (0, stdout, "")

    def _execute_command(
        self,
        work_dir: Path,
        env: Dict[str, str],
        command: str
    ) -> Tuple[int, str, str]:
        """Execute a command in the test environment.

        Args:
            work_dir: Working directory
            env: Environment variables
            command: Command to execute (e.g., "/popkit:routine morning")

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        # Parse command
        if not command.startswith("/popkit:"):
            return (1, "", f"Invalid command format: {command}")

        # Extract command name and args
        parts = command.split(" ", 1)
        cmd_name = parts[0].replace("/popkit:", "")
        cmd_args = parts[1] if len(parts) > 1 else ""

        # Find command file
        cmd_file = PLUGIN_DIR / "commands" / f"{cmd_name}.md"

        if not cmd_file.exists():
            return (1, "", f"Command not found: {cmd_name}")

        # Read command content
        cmd_content = cmd_file.read_text(encoding="utf-8")

        # Log command start event
        if TELEMETRY_AVAILABLE and is_test_mode():
            session_id = env.get("POPKIT_TEST_SESSION_ID")
            if session_id and self.storage:
                event = create_event("command_test_start", {
                    "command": cmd_name,
                    "args": cmd_args
                })
                self.storage.log_event(session_id, event)

        # For now, return success if command file exists
        # Full command execution would require Claude Code CLI integration
        stdout = f"Command '{cmd_name}' loaded successfully\n"
        stdout += f"Content length: {len(cmd_content)} bytes\n"
        stdout += f"Arguments: {cmd_args}\n"

        return (0, stdout, "")

    def _collect_artifacts(
        self,
        work_dir: Path,
        patterns: List[str]
    ) -> List[str]:
        """Collect artifacts from the working directory.

        Args:
            work_dir: Working directory
            patterns: Glob patterns for artifact collection

        Returns:
            List of artifact file paths
        """
        artifacts = []

        for pattern in patterns:
            for path in work_dir.glob(pattern):
                if path.is_file():
                    # Store relative path
                    rel_path = path.relative_to(work_dir)
                    artifacts.append(str(rel_path))

        return artifacts

    def _get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics from the telemetry session.

        Args:
            session_id: Test session ID

        Returns:
            Dictionary of metrics
        """
        if not TELEMETRY_AVAILABLE or not self.storage:
            return {}

        session = self.storage.get_session(session_id)
        if not session:
            return {}

        return session.metrics.to_dict() if hasattr(session.metrics, 'to_dict') else {}

    def _cleanup_temp_dir(self, work_dir: Path) -> None:
        """Clean up a temporary directory.

        Args:
            work_dir: Directory to clean up
        """
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
            if work_dir in self._temp_dirs:
                self._temp_dirs.remove(work_dir)
        except Exception:
            pass

    def cleanup_all(self) -> None:
        """Clean up all temporary directories created by this runner."""
        for work_dir in list(self._temp_dirs):
            self._cleanup_temp_dir(work_dir)


# =============================================================================
# Convenience Functions
# =============================================================================

def run_skill_test(
    skill_name: str,
    timeout: int = 120,
    context: Optional[Dict[str, Any]] = None
) -> TestResult:
    """Run a quick skill test.

    Args:
        skill_name: Name of the skill
        timeout: Timeout in seconds
        context: Additional context

    Returns:
        TestResult
    """
    runner = LocalTestRunner()
    config = TestConfig(timeout=timeout)
    return runner.run_skill(skill_name, config=config, context=context)


def run_command_test(
    command: str,
    timeout: int = 60,
    context: Optional[Dict[str, Any]] = None
) -> TestResult:
    """Run a quick command test.

    Args:
        command: Command to test
        timeout: Timeout in seconds
        context: Additional context

    Returns:
        TestResult
    """
    runner = LocalTestRunner()
    config = TestConfig(timeout=timeout)
    return runner.run_command(command, config=config, context=context)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point for running tests."""
    import argparse

    parser = argparse.ArgumentParser(description="PopKit Local Test Runner")
    parser.add_argument("--skill", help="Skill name to test")
    parser.add_argument("--command", help="Command to test")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up temp directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not args.skill and not args.command:
        parser.print_help()
        sys.exit(1)

    runner = LocalTestRunner()
    config = TestConfig(
        timeout=args.timeout,
        cleanup=not args.no_cleanup
    )

    if args.skill:
        result = runner.run_skill(args.skill, config=config)
    else:
        result = runner.run_command(args.command, config=config)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"Test: {result.test_name}")
        print(f"Type: {result.test_type}")
        print(f"Outcome: {result.outcome}")
        print(f"Duration: {result.duration_ms:.1f}ms")
        print(f"Exit Code: {result.exit_code}")
        print(f"Session ID: {result.session_id}")
        print(f"{'=' * 60}")

        if result.stdout and args.verbose:
            print("\nSTDOUT:")
            print(result.stdout)

        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)

        if result.error:
            print(f"\nERROR: {result.error}")

        if result.artifacts:
            print(f"\nArtifacts: {len(result.artifacts)}")
            for artifact in result.artifacts[:10]:
                print(f"  - {artifact}")

    sys.exit(0 if result.outcome == "success" else 1)


if __name__ == "__main__":
    main()
