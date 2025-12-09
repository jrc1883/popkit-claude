#!/usr/bin/env python3
"""
Quality Gate Hook - PostToolUse validation for code integrity

Runs validation (tsc, build, lint) based on triggers:
- High-risk actions (config changes, deletions, import changes)
- Batch threshold (every N file edits)
- Agent completion (safety net)

Presents interactive options on failure:
- Fix now (default) - inject errors into context
- Rollback - restore to checkpoint, save patch
- Continue - proceed despite errors
- Pause - stop for manual review
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# High-risk file patterns that trigger immediate validation
HIGH_RISK_PATTERNS = [
    "tsconfig.json",
    "tsconfig.*.json",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".env",
    ".env.*",
    "*.config.js",
    "*.config.ts",
    "*.config.mjs",
    "vite.config.*",
    "webpack.config.*",
    "rollup.config.*",
    "jest.config.*",
    "babel.config.*",
    ".eslintrc*",
    ".prettierrc*",
]


class QualityGateHook:
    def __init__(self):
        self.cwd = Path.cwd()
        self.claude_dir = self.cwd / ".claude"
        self.state_file = self.claude_dir / "quality-gate-state.json"
        self.config_file = self.claude_dir / "quality-gates.json"
        self.checkpoints_dir = self.claude_dir / "checkpoints"

        # Ensure directories exist
        self.claude_dir.mkdir(exist_ok=True)
        self.checkpoints_dir.mkdir(exist_ok=True)

        # Load state and config
        self.state = self.load_state()
        self.config = self.load_config()

    def load_state(self) -> Dict[str, Any]:
        """Load hook state from file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "file_edit_count": 0,
            "recent_files": [],
            "recent_file_count": 0,
            "last_checkpoint": None,
            # Session-only flaky test tracking
            "test_results": []  # List of {"test_name": str, "passed": bool, "timestamp": str}
        }

    def save_state(self):
        """Persist hook state to file."""
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2))
        except Exception as e:
            print(f"Warning: Could not save state: {e}", file=sys.stderr)

    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load user configuration overrides."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError:
                pass
        return None

    # =========================================================================
    # Auto-Detection
    # =========================================================================

    def detect_gates(self) -> List[Dict[str, Any]]:
        """Auto-detect available quality gates based on project files."""
        gates = []

        # TypeScript
        if (self.cwd / "tsconfig.json").exists():
            gates.append({
                "name": "typescript",
                "command": "npx tsc --noEmit",
                "timeout": 60,
                "enabled": True
            })

        # Package.json scripts
        pkg_path = self.cwd / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text())
                scripts = pkg.get("scripts", {})

                if "build" in scripts:
                    gates.append({
                        "name": "build",
                        "command": "npm run build",
                        "timeout": 120,
                        "enabled": True
                    })
                if "lint" in scripts:
                    gates.append({
                        "name": "lint",
                        "command": "npm run lint",
                        "timeout": 60,
                        "enabled": True
                    })
                if "typecheck" in scripts:
                    # Prefer explicit typecheck over tsc
                    gates = [g for g in gates if g["name"] != "typescript"]
                    gates.append({
                        "name": "typecheck",
                        "command": "npm run typecheck",
                        "timeout": 60,
                        "enabled": True
                    })
                if "test" in scripts:
                    gates.append({
                        "name": "test",
                        "command": "npm test",
                        "timeout": 300,
                        "enabled": False,  # Optional by default (can be slow)
                        "optional": True
                    })
            except json.JSONDecodeError:
                pass

        # Python projects
        if (self.cwd / "pyproject.toml").exists() or (self.cwd / "setup.py").exists():
            if (self.cwd / "mypy.ini").exists() or (self.cwd / "pyproject.toml").exists():
                gates.append({
                    "name": "mypy",
                    "command": "mypy .",
                    "timeout": 60,
                    "enabled": True
                })

        return gates

    def get_effective_gates(self) -> List[Dict[str, Any]]:
        """Merge auto-detected gates with config overrides."""
        detected = {g["name"]: g for g in self.detect_gates()}

        if self.config and "gates" in self.config:
            for gate in self.config["gates"]:
                name = gate["name"]
                if name in detected:
                    detected[name].update(gate)
                else:
                    detected[name] = gate

        return [g for g in detected.values() if g.get("enabled", True)]

    # =========================================================================
    # Trigger Logic
    # =========================================================================

    def matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a glob-like pattern."""
        if pattern.startswith("*."):
            return filename.endswith(pattern[1:])
        elif "*" in pattern:
            # Simple glob: convert to regex
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            return bool(re.match(f"^{regex}$", filename))
        else:
            return filename == pattern

    def is_high_risk_action(self, tool_name: str, tool_args: Dict) -> bool:
        """Determine if action warrants immediate validation."""

        # Deletions are always high-risk
        if tool_name == "Delete":
            return True

        # Check file path against high-risk patterns
        file_path = tool_args.get("file_path", "")
        if file_path:
            filename = Path(file_path).name
            for pattern in HIGH_RISK_PATTERNS:
                if self.matches_pattern(filename, pattern):
                    return True

        # Check for import/export changes in edits
        if tool_name in ["Edit", "MultiEdit"]:
            new_content = tool_args.get("new_string", "")
            old_content = tool_args.get("old_string", "")
            combined = new_content + old_content

            import_export_keywords = [
                "import ", "from ", "export ", "require(", "module.exports"
            ]
            if any(kw in combined for kw in import_export_keywords):
                return True

        # Rapid multi-file changes (3+ different files recently)
        if self.state.get("recent_file_count", 0) >= 3:
            return True

        return False

    def should_run_gates(self, tool_name: str, tool_args: Dict) -> bool:
        """Determine if gates should run based on triggers."""

        # Only trigger on file modification tools
        if tool_name not in ["Write", "Edit", "MultiEdit", "Delete"]:
            return False

        # High-risk actions trigger immediately
        if self.is_high_risk_action(tool_name, tool_args):
            return True

        # Batch threshold
        threshold = 5
        if self.config:
            threshold = self.config.get("triggers", {}).get("batch_threshold", 5)

        if self.state.get("file_edit_count", 0) >= threshold:
            return True

        return False

    def update_state_counters(self, tool_name: str, tool_args: Dict):
        """Update state counters after file modifications."""
        if tool_name in ["Write", "Edit", "MultiEdit", "Delete"]:
            self.state["file_edit_count"] = self.state.get("file_edit_count", 0) + 1

            # Track recent files for rapid-change detection
            recent = self.state.get("recent_files", [])
            file_path = tool_args.get("file_path", "")
            if file_path and file_path not in recent:
                recent.append(file_path)
                if len(recent) > 10:
                    recent = recent[-10:]
            self.state["recent_files"] = recent
            self.state["recent_file_count"] = len(set(recent))

            self.save_state()

    # =========================================================================
    # Gate Execution
    # =========================================================================

    def run_gate(self, gate: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single quality gate."""
        result = {
            "name": gate["name"],
            "success": False,
            "output": "",
            "errors": [],
            "duration": 0
        }

        start = datetime.now()
        try:
            proc = subprocess.run(
                gate["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=gate.get("timeout", 60),
                cwd=str(self.cwd)
            )

            result["output"] = proc.stdout + proc.stderr
            result["success"] = proc.returncode == 0

            if not result["success"]:
                result["errors"] = self.parse_errors(gate["name"], result["output"])

        except subprocess.TimeoutExpired:
            result["output"] = f"Gate '{gate['name']}' timed out after {gate.get('timeout', 60)}s"
            result["errors"] = [{"message": result["output"]}]
        except Exception as e:
            result["output"] = str(e)
            result["errors"] = [{"message": str(e)}]

        result["duration"] = (datetime.now() - start).total_seconds()
        return result

    def run_all_gates(self) -> Dict[str, Any]:
        """Execute all enabled quality gates."""
        gates = self.get_effective_gates()

        if not gates:
            return {"passed": True, "gates": [], "total_errors": 0, "duration": 0, "skipped": "No gates detected"}

        results = {
            "passed": True,
            "gates": [],
            "total_errors": 0,
            "duration": 0
        }

        for gate in gates:
            # Skip optional gates unless explicitly enabled
            if gate.get("optional") and not (self.config or {}).get("options", {}).get("run_tests"):
                continue

            print(f"Running quality gate: {gate['name']}...", file=sys.stderr)
            gate_result = self.run_gate(gate)
            results["gates"].append(gate_result)
            results["duration"] += gate_result["duration"]

            # Track test results for flaky detection
            if gate["name"] == "test":
                self.track_test_result("test_suite", gate_result["success"])

            if not gate_result["success"]:
                results["passed"] = False
                results["total_errors"] += len(gate_result["errors"])

                # Fail fast if configured (default: true)
                fail_fast = True
                if self.config:
                    fail_fast = self.config.get("options", {}).get("fail_fast", True)
                if fail_fast:
                    break

        # Check for flaky tests and add warning
        flaky_tests = self.check_flaky_tests()
        if flaky_tests:
            results["flaky_tests"] = flaky_tests
            flaky_warning = self.format_flaky_warning(flaky_tests)
            print(flaky_warning, file=sys.stderr)

        return results

    def parse_errors(self, gate_name: str, output: str) -> List[Dict]:
        """Parse error output into structured format."""
        errors = []

        if gate_name in ["typescript", "typecheck"]:
            # TypeScript errors: file(line,col): error TS####: message
            for match in re.finditer(r'(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)', output):
                errors.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "code": match.group(4),
                    "message": match.group(5)
                })
            # Also try: file:line:col - error TS####: message
            for match in re.finditer(r'(.+?):(\d+):(\d+) - error (TS\d+): (.+)', output):
                errors.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "code": match.group(4),
                    "message": match.group(5)
                })

        elif gate_name == "lint":
            # ESLint: file:line:col: message (rule)
            for match in re.finditer(r'(.+?):(\d+):(\d+):\s*(.+)', output):
                errors.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "message": match.group(4)
                })

        elif gate_name == "build":
            # Generic build errors - look for "error" lines
            for line in output.split('\n'):
                line = line.strip()
                if line and 'error' in line.lower():
                    errors.append({"message": line})

        else:
            # Generic: split by newlines, filter relevant lines
            for line in output.split('\n'):
                line = line.strip()
                if line and ('error' in line.lower() or 'failed' in line.lower()):
                    errors.append({"message": line})

        return errors[:10]  # Limit to first 10 errors

    # =========================================================================
    # Flaky Test Tracking (Session-Only)
    # =========================================================================

    def track_test_result(self, test_name: str, passed: bool):
        """Track a test result for flaky detection (session-only)."""
        test_results = self.state.get("test_results", [])
        test_results.append({
            "test_name": test_name,
            "passed": passed,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 50 results (session memory limit)
        if len(test_results) > 50:
            test_results = test_results[-50:]

        self.state["test_results"] = test_results
        self.save_state()

    def check_flaky_tests(self) -> List[Dict[str, Any]]:
        """Check for flaky tests based on session history.

        Returns list of potentially flaky tests with their pass rates.
        A test is considered flaky if it has >20% variance (passes sometimes, fails sometimes).
        """
        flaky_tests = []
        test_results = self.state.get("test_results", [])

        if len(test_results) < 3:
            return []  # Not enough data

        # Group results by test name
        by_test = {}
        for result in test_results:
            name = result.get("test_name", "unknown")
            if name not in by_test:
                by_test[name] = {"passed": 0, "failed": 0, "total": 0}
            by_test[name]["total"] += 1
            if result.get("passed"):
                by_test[name]["passed"] += 1
            else:
                by_test[name]["failed"] += 1

        # Find flaky tests (20-80% pass rate = flaky)
        for name, stats in by_test.items():
            if stats["total"] >= 2:  # Need at least 2 runs
                pass_rate = stats["passed"] / stats["total"]
                if 0.2 <= pass_rate <= 0.8:
                    flaky_tests.append({
                        "test_name": name,
                        "pass_rate": round(pass_rate * 100, 1),
                        "passed": stats["passed"],
                        "failed": stats["failed"],
                        "total": stats["total"]
                    })

        return flaky_tests

    def format_flaky_warning(self, flaky_tests: List[Dict]) -> str:
        """Format flaky test warning for display."""
        if not flaky_tests:
            return ""

        lines = [
            "",
            "=" * 60,
            "Warning: Potentially Flaky Tests Detected",
            "=" * 60,
            ""
        ]

        for test in flaky_tests:
            lines.append(f"  {test['test_name']}")
            lines.append(f"    Pass rate: {test['pass_rate']}% ({test['passed']}/{test['total']} runs)")
            lines.append("")

        lines.extend([
            "Flaky tests pass inconsistently and may indicate:",
            "  - Race conditions or timing issues",
            "  - State pollution between tests",
            "  - Order-dependent test execution",
            "",
            "Tip: Use condition-based waiting instead of setTimeout.",
            "See: /skill:pop-test-driven-development (Condition-Based Waiting section)",
            "-" * 60,
            ""
        ])

        return '\n'.join(lines)

    # =========================================================================
    # Failure Handling
    # =========================================================================

    def present_failure_menu(self, results: Dict) -> str:
        """Present interactive menu on gate failure. Returns chosen action."""

        # Format error display
        failed_gate = next((g for g in results["gates"] if not g["success"]), None)
        gate_name = failed_gate["name"] if failed_gate else "unknown"

        output_lines = [
            "",
            "=" * 60,
            f"Quality Gate Failed: {gate_name} ({results['total_errors']} errors)",
            "=" * 60,
            ""
        ]

        # Show errors (max 5)
        for gate in results["gates"]:
            if not gate["success"]:
                for error in gate["errors"][:5]:
                    if "file" in error:
                        output_lines.append(f"  {error['file']}:{error.get('line', '?')}")
                        output_lines.append(f"    {error['message']}")
                    else:
                        output_lines.append(f"  {error['message']}")
                if len(gate["errors"]) > 5:
                    output_lines.append(f"  ... and {len(gate['errors']) - 5} more errors")

        output_lines.extend([
            "",
            "-" * 60,
            "Options:",
            "  1. Fix now      - Address these errors (default)",
            "  2. Rollback     - Revert to last checkpoint",
            "  3. Continue     - Proceed despite errors",
            "  4. Pause        - Stop for manual review",
            "-" * 60,
            ""
        ])

        # Output to stderr so it's visible
        print('\n'.join(output_lines), file=sys.stderr)

        # Default to "fix" - errors injected into context
        # In future, could read from stdin for interactive selection
        return "fix"

    def format_errors_for_context(self, results: Dict) -> str:
        """Format errors for injection into conversation context."""
        lines = ["**Quality gate validation found the following issues:**\n"]

        for gate in results["gates"]:
            if not gate["success"]:
                lines.append(f"### {gate['name'].title()} Errors\n")
                for error in gate["errors"]:
                    if "file" in error:
                        lines.append(f"- `{error['file']}:{error.get('line', '?')}` - {error['message']}")
                    else:
                        lines.append(f"- {error['message']}")
                lines.append("")

        lines.append("\n**Please address these errors before continuing.**")
        return '\n'.join(lines)

    # =========================================================================
    # Rollback Mechanism
    # =========================================================================

    def create_checkpoint(self) -> str:
        """Create a checkpoint of current changes."""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        patch_path = self.checkpoints_dir / f"{timestamp}.patch"

        try:
            # Capture all uncommitted changes (staged and unstaged)
            result = subprocess.run(
                "git diff HEAD",
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.cwd)
            )

            if result.stdout:
                patch_path.write_text(result.stdout)
                self.update_manifest(timestamp, str(patch_path))
                return str(patch_path)
            else:
                print("No changes to save", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not create checkpoint: {e}", file=sys.stderr)

        return ""

    def rollback(self) -> bool:
        """Rollback to clean state, saving current changes to patch."""
        patch_path = self.create_checkpoint()

        if not patch_path:
            print("Warning: Could not save changes before rollback", file=sys.stderr)

        try:
            # Discard all uncommitted changes
            subprocess.run("git checkout .", shell=True, cwd=str(self.cwd), check=True)
            subprocess.run("git clean -fd", shell=True, cwd=str(self.cwd), check=True)

            # Reset state
            self.state["file_edit_count"] = 0
            self.state["recent_files"] = []
            self.state["recent_file_count"] = 0
            self.save_state()

            if patch_path:
                print(f"Rolled back successfully.", file=sys.stderr)
                print(f"Changes saved to: {patch_path}", file=sys.stderr)
                print(f"To recover: git apply {patch_path}", file=sys.stderr)

            return True
        except subprocess.CalledProcessError as e:
            print(f"Rollback failed: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Rollback failed: {e}", file=sys.stderr)
            return False

    def update_manifest(self, timestamp: str, patch_path: str):
        """Update checkpoints manifest."""
        manifest_path = self.checkpoints_dir / "manifest.json"

        manifest = {"checkpoints": [], "retention_days": 7}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except:
                pass

        manifest["checkpoints"].append({
            "timestamp": timestamp,
            "path": patch_path,
            "trigger": "quality_gate_rollback",
            "created_at": datetime.now().isoformat()
        })

        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Cleanup old checkpoints
        self.cleanup_old_checkpoints(manifest)

    def cleanup_old_checkpoints(self, manifest: Dict):
        """Remove checkpoints older than retention period."""
        retention_days = manifest.get("retention_days", 7)
        cutoff = datetime.now().timestamp() - (retention_days * 86400)

        remaining = []
        for cp in manifest.get("checkpoints", []):
            try:
                cp_time = datetime.strptime(cp["timestamp"], "%Y-%m-%d-%H%M%S").timestamp()
                if cp_time > cutoff:
                    remaining.append(cp)
                else:
                    # Delete old patch file
                    patch_path = Path(cp["path"])
                    if patch_path.exists():
                        patch_path.unlink()
                        print(f"Cleaned up old checkpoint: {cp['timestamp']}", file=sys.stderr)
            except:
                remaining.append(cp)

        manifest["checkpoints"] = remaining

    # =========================================================================
    # Power Mode Integration
    # =========================================================================

    def is_power_mode_active(self) -> bool:
        """Check if Power Mode is currently active."""
        # Check for coordinator state file
        power_state = self.claude_dir / "power-mode-state.json"
        if power_state.exists():
            try:
                state = json.loads(power_state.read_text())
                return state.get("active", False)
            except:
                pass

        # Check environment variable
        return os.environ.get("POPKIT_POWER_MODE") == "1"

    def run_lightweight_check(self) -> Dict[str, Any]:
        """Run lightweight syntax check only (for Power Mode)."""
        if (self.cwd / "tsconfig.json").exists():
            result = subprocess.run(
                "npx tsc --noEmit --skipLibCheck",
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(self.cwd)
            )
            if result.returncode != 0:
                return {
                    "type": "syntax_warning",
                    "output": result.stderr,
                    "errors": self.parse_errors("typescript", result.stderr)
                }
        return {"type": "ok"}

    # =========================================================================
    # Main Processing
    # =========================================================================

    def process(self, input_data: Dict) -> Dict:
        """Main processing function."""
        tool_name = input_data.get("tool_name", "")
        tool_args = input_data.get("tool_input", {})

        # Update counters for file modifications
        self.update_state_counters(tool_name, tool_args)

        # Check if we should run gates
        if not self.should_run_gates(tool_name, tool_args):
            return {"continue": True}

        # In Power Mode, only run lightweight checks
        if self.is_power_mode_active():
            lightweight = self.run_lightweight_check()
            if lightweight.get("type") == "syntax_warning":
                print(f"Syntax warning (Power Mode): {len(lightweight.get('errors', []))} issues", file=sys.stderr)
            return {"continue": True}

        # Run full quality gates
        print("Running quality gates...", file=sys.stderr)
        results = self.run_all_gates()

        # Reset counter after running gates
        self.state["file_edit_count"] = 0
        self.state["recent_files"] = []
        self.state["recent_file_count"] = 0
        self.save_state()

        if results.get("skipped"):
            print(f"Quality gates skipped: {results['skipped']}", file=sys.stderr)
            return {"continue": True}

        if results["passed"]:
            self.state["last_checkpoint"] = datetime.now().isoformat()
            self.save_state()
            duration = results.get("duration", 0)
            print(f"All quality gates passed ({duration:.1f}s)", file=sys.stderr)
            return {"continue": True}

        # Gates failed - present options
        action = self.present_failure_menu(results)

        if action == "rollback":
            self.rollback()
            return {"continue": True, "message": "Rolled back to last checkpoint"}
        elif action == "pause":
            return {
                "continue": False,
                "stop_reason": "Quality gate failure - manual review requested"
            }
        elif action == "continue":
            print("Continuing despite errors (not recommended)", file=sys.stderr)
            return {"continue": True}
        else:  # fix (default)
            error_context = self.format_errors_for_context(results)
            # Print errors for visibility
            print(error_context, file=sys.stderr)
            return {
                "continue": True,
                "message": error_context
            }


def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_data = json.loads(sys.stdin.read())
        hook = QualityGateHook()
        result = hook.process(input_data)
        print(json.dumps(result))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}", "continue": True}))
    except Exception as e:
        print(json.dumps({"error": str(e), "continue": True}))
        # Don't block on errors - allow work to continue
        sys.exit(0)


if __name__ == "__main__":
    main()
