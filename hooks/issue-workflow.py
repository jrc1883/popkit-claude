#!/usr/bin/env python3
"""
Issue Workflow Hook - Activation Logic for Issue-Driven Development

Integrates with /popkit:issue work <number> to:
1. Fetch and parse issue with PopKit Guidance section
2. Determine if brainstorming should be triggered
3. Determine if Power Mode should activate
4. Create todos from phases
5. Suggest agents based on issue type and guidance
6. Run quality gates at phase transitions (Issue #11)

This hook ties together:
- Issue Parser (github_issues.py)
- Quality Gates (quality-gate.py)
- Power Mode (power-mode/)

Part of Issue #11 - Unified Orchestration System
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))
from github_issues import (
    get_workflow_config,
    infer_issue_type,
    get_agents_for_issue_type
)
from flag_parser import parse_work_args

# Import quality gate hook for phase transitions
sys.path.insert(0, str(Path(__file__).parent))
try:
    from importlib import import_module
    quality_gate_module = import_module("quality-gate")
    QualityGateHook = quality_gate_module.QualityGateHook
    QUALITY_GATES_AVAILABLE = True
except ImportError:
    QUALITY_GATES_AVAILABLE = False


class IssueWorkflowHook:
    """Manages issue-driven workflow activation."""

    def __init__(self):
        self.cwd = Path.cwd()
        self.claude_dir = self.cwd / ".claude"
        self.popkit_dir = self.claude_dir / "popkit"
        self.state_file = self.popkit_dir / "issue-workflow-state.json"
        # Use the REAL Power Mode state file path that statusline.py and checkin-hook.py use
        self.power_mode_state = self.popkit_dir / "power-mode-state.json"
        self.phase_checkpoints_dir = self.popkit_dir / "phase-checkpoints"

        # Ensure directories exist
        self.claude_dir.mkdir(exist_ok=True)
        self.popkit_dir.mkdir(exist_ok=True)
        self.phase_checkpoints_dir.mkdir(exist_ok=True)

        # Load state
        self.state = self.load_state()

        # Initialize quality gate hook if available
        self.quality_gate = QualityGateHook() if QUALITY_GATES_AVAILABLE else None

    def load_state(self) -> Dict[str, Any]:
        """Load workflow state from file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "active_issue": None,
            "current_phase": None,
            "phases_completed": [],
            "activated_at": None
        }

    def save_state(self):
        """Persist workflow state to file."""
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2))
        except Exception as e:
            print(f"Warning: Could not save state: {e}", file=sys.stderr)

    def activate_power_mode(self, config: Dict[str, Any]) -> bool:
        """Activate Power Mode with configuration from issue.

        Merges with existing state to preserve agent tracking data from checkin-hook.py.
        Writes to .claude/popkit/power-mode-state.json (the real Power Mode state file).
        """
        try:
            # Load existing state to preserve agent tracking fields
            existing_state = {}
            if self.power_mode_state.exists():
                try:
                    existing_state = json.loads(self.power_mode_state.read_text())
                except (json.JSONDecodeError, IOError):
                    pass

            phases = config.get("suggested_phases", [])
            power_state = {
                "active": True,
                "activated_at": datetime.now().isoformat(),
                "source": f"issue #{config.get('issue_number', 'unknown')}",
                "active_issue": config.get("issue_number"),
                "session_id": existing_state.get("session_id") or f"pop-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                # Status line fields (these are what statusline.py reads)
                "current_phase": phases[0] if phases else "implementation",
                "phase_index": 1,
                "total_phases": len(phases) if phases else 1,
                "progress": 0.0,
                "phases_completed": [],
                # Config for reference
                "config": {
                    "phases": phases,
                    "agents": config.get("config", {}).get("agents", {}),
                    "quality_gates": config.get("config", {}).get("quality_gates", [])
                }
            }

            # Merge: keep agent tracking fields from existing state
            agent_tracking_fields = [
                "tool_call_count", "tools_used", "files_touched",
                "decisions", "discoveries", "last_checkin"
            ]
            for field in agent_tracking_fields:
                if field in existing_state:
                    power_state[field] = existing_state[field]

            self.power_mode_state.write_text(json.dumps(power_state, indent=2))
            print(f"Power Mode activated: {self.power_mode_state}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Warning: Could not activate Power Mode: {e}", file=sys.stderr)
            return False

    def deactivate_power_mode(self):
        """Deactivate Power Mode."""
        try:
            if self.power_mode_state.exists():
                power_state = json.loads(self.power_mode_state.read_text())
                power_state["active"] = False
                power_state["deactivated_at"] = datetime.now().isoformat()
                self.power_mode_state.write_text(json.dumps(power_state, indent=2))
        except Exception:
            pass

    def generate_todo_list(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate todo list from issue phases and configuration."""
        todos = []
        phases = config.get("suggested_phases", [])

        phase_descriptions = {
            "discovery": "Research and gather context for the issue",
            "architecture": "Design the solution architecture",
            "implementation": "Implement the solution",
            "testing": "Write and run tests",
            "documentation": "Update documentation",
            "review": "Review and finalize changes"
        }

        for i, phase in enumerate(phases):
            todos.append({
                "content": f"Phase {i+1}: {phase.title()} - {phase_descriptions.get(phase, phase)}",
                "status": "pending" if i > 0 else "in_progress",
                "activeForm": f"Working on {phase}"
            })

        return todos

    def format_workflow_summary(self, workflow: Dict[str, Any]) -> str:
        """Format workflow configuration as readable summary."""
        issue = workflow.get("issue", {})
        config = workflow.get("config", {})

        lines = [
            "",
            "=" * 60,
            f"Issue #{issue.get('number')}: {issue.get('title', 'Unknown')}",
            "=" * 60,
            "",
            f"State: {issue.get('state', 'Unknown')}",
            f"Labels: {', '.join(issue.get('labels', []))}",
            "",
            "Workflow Configuration:",
            f"  Type: {config.get('workflow_type', 'direct')}",
            f"  Complexity: {config.get('complexity', 'medium')}",
            f"  Power Mode: {config.get('power_mode', 'not_needed')}",
            "",
            "Phases:",
        ]

        for phase in workflow.get("suggested_phases", []):
            lines.append(f"  - {phase}")

        lines.extend([
            "",
            "Agents:",
            f"  Primary: {', '.join(config.get('agents', {}).get('primary', ['none']))}",
            f"  Supporting: {', '.join(config.get('agents', {}).get('supporting', ['none']))}",
            "",
            "Quality Gates:",
        ])

        for gate in config.get("quality_gates", []):
            lines.append(f"  - {gate}")

        lines.extend([
            "",
            "-" * 60,
            "Activation:",
            f"  Should Brainstorm: {'Yes' if workflow.get('should_brainstorm') else 'No'}",
            f"  Should Activate Power Mode: {'Yes' if workflow.get('should_activate_power_mode') else 'No'}",
            "-" * 60,
            ""
        ])

        return '\n'.join(lines)

    def start_issue_workflow(self, issue_number: int) -> Dict[str, Any]:
        """Start working on an issue - main entry point.

        Args:
            issue_number: The issue number to work on

        Returns:
            Dict with workflow configuration and actions to take
        """
        result = {
            "success": False,
            "issue_number": issue_number,
            "workflow": None,
            "actions": [],
            "todos": [],
            "messages": []
        }

        # Fetch and parse issue
        workflow = get_workflow_config(issue_number)

        if workflow.get("error"):
            result["messages"].append(f"Error: {workflow['error']}")
            return result

        result["workflow"] = workflow
        result["success"] = True

        # Determine actions
        if workflow.get("should_brainstorm"):
            result["actions"].append({
                "type": "trigger_skill",
                "skill": "pop-brainstorming",
                "reason": "Issue specifies 'Brainstorm First' workflow"
            })
            result["messages"].append("Brainstorming recommended before implementation")

        if workflow.get("should_activate_power_mode"):
            result["actions"].append({
                "type": "activate_power_mode",
                "reason": f"Power Mode: {workflow['config']['power_mode']}, Complexity: {workflow['config']['complexity']}"
            })
            self.activate_power_mode({
                "issue_number": issue_number,
                **workflow
            })
            result["messages"].append("Power Mode activated for parallel agent coordination")

        # Generate todos from phases
        result["todos"] = self.generate_todo_list(workflow)

        # Update state
        self.state["active_issue"] = issue_number
        self.state["current_phase"] = workflow.get("suggested_phases", ["implementation"])[0]
        self.state["phases_completed"] = []
        self.state["activated_at"] = datetime.now().isoformat()
        self.save_state()

        # Add summary message
        result["messages"].append(self.format_workflow_summary(workflow))

        return result

    def start_work_on_issue(self, issue_number: int, flags: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start working on an issue with flag support - for /popkit:work command.

        This is the enhanced version of start_issue_workflow that respects
        command-line flags for Power Mode control.

        Args:
            issue_number: The issue number to work on
            flags: Dict from parse_work_args with:
                - force_power: bool - Force Power Mode ON
                - force_solo: bool - Force Power Mode OFF
                - phases: List[str] - Override phases
                - agents: List[str] - Override agents

        Returns:
            Dict with workflow configuration and actions to take
        """
        flags = flags or {}

        result = {
            "success": False,
            "issue_number": issue_number,
            "workflow": None,
            "power_mode": False,
            "power_mode_source": None,
            "actions": [],
            "todos": [],
            "messages": []
        }

        # Fetch and parse issue
        workflow = get_workflow_config(issue_number)

        if workflow.get("error"):
            result["messages"].append(f"Error: {workflow['error']}")
            return result

        result["workflow"] = workflow
        result["success"] = True

        # Override phases if specified
        if flags.get("phases"):
            workflow["suggested_phases"] = flags["phases"]
            result["messages"].append(f"Using custom phases: {', '.join(flags['phases'])}")

        # Override agents if specified
        if flags.get("agents"):
            workflow["config"]["agents"] = {
                "primary": flags["agents"][:1] if flags["agents"] else [],
                "supporting": flags["agents"][1:] if len(flags["agents"]) > 1 else []
            }
            result["messages"].append(f"Using custom agents: {', '.join(flags['agents'])}")

        # Determine Power Mode activation (flag priority)
        should_activate_power = False
        power_source = "none"

        if flags.get("force_power"):
            # Flag -p or --power takes highest priority
            should_activate_power = True
            power_source = "flag (-p/--power)"
        elif flags.get("force_solo"):
            # Flag --solo forces sequential mode
            should_activate_power = False
            power_source = "flag (--solo)"
        elif workflow.get("should_activate_power_mode"):
            # Use PopKit Guidance recommendation
            should_activate_power = True
            config = workflow.get("config", {})
            power_source = f"PopKit Guidance (power_mode: {config.get('power_mode')}, complexity: {config.get('complexity')})"
        else:
            # Default to sequential
            should_activate_power = False
            power_source = "default (sequential)"

        result["power_mode"] = should_activate_power
        result["power_mode_source"] = power_source

        # Determine actions
        if workflow.get("should_brainstorm"):
            result["actions"].append({
                "type": "trigger_skill",
                "skill": "pop-brainstorming",
                "reason": "Issue specifies 'Brainstorm First' workflow"
            })
            result["messages"].append("Brainstorming recommended before implementation")

        if should_activate_power:
            result["actions"].append({
                "type": "activate_power_mode",
                "reason": power_source
            })
            self.activate_power_mode({
                "issue_number": issue_number,
                **workflow
            })
            result["messages"].append(f"Power Mode activated ({power_source})")
        else:
            result["messages"].append(f"Sequential mode ({power_source})")

        # Generate todos from phases
        result["todos"] = self.generate_todo_list(workflow)

        # Update state
        self.state["active_issue"] = issue_number
        self.state["current_phase"] = workflow.get("suggested_phases", ["implementation"])[0]
        self.state["phases_completed"] = []
        self.state["activated_at"] = datetime.now().isoformat()
        self.state["power_mode"] = should_activate_power
        self.save_state()

        # Add summary message
        result["messages"].append(self.format_workflow_summary(workflow))

        return result

    def complete_phase(self, phase_name: str, force: bool = False) -> Dict[str, Any]:
        """Mark a phase as complete and determine next steps.

        Runs quality gates before allowing phase transition. If gates fail,
        the transition is blocked unless force=True.

        Args:
            phase_name: Name of the phase to complete
            force: If True, proceed despite gate failures (not recommended)

        Returns:
            Dict with next phase and any actions to take
        """
        result = {
            "completed": phase_name,
            "next_phase": None,
            "actions": [],
            "messages": [],
            "gate_results": None,
            "blocked": False
        }

        # Load current workflow state
        if not self.state.get("active_issue"):
            result["messages"].append("No active issue workflow")
            return result

        # Determine next phase first (before gates)
        workflow = get_workflow_config(self.state["active_issue"])
        if workflow.get("error"):
            result["messages"].append(f"Warning: Could not fetch issue: {workflow['error']}")
            return result

        phases = workflow.get("suggested_phases", [])
        completed = set(self.state.get("phases_completed", []))

        # Find next phase
        next_phase = None
        next_phase_index = 0
        for i, phase in enumerate(phases):
            if phase not in completed and phase != phase_name:
                next_phase = phase
                next_phase_index = i
                break

        # Run quality gates before transition (Issue #11)
        if next_phase:
            gate_results = self.run_phase_transition_gates(phase_name, next_phase)
            result["gate_results"] = gate_results

            if not gate_results["passed"] and not force:
                result["blocked"] = True
                result["messages"].append(
                    f"Phase transition blocked: quality gates failed. "
                    f"Fix errors or use force=True to proceed anyway."
                )
                return result

            if not gate_results["passed"] and force:
                result["messages"].append(
                    "WARNING: Proceeding despite gate failures (force=True)"
                )

        # Mark phase complete
        if phase_name not in self.state.get("phases_completed", []):
            self.state["phases_completed"].append(phase_name)

        # Proceed with transition
        completed = set(self.state.get("phases_completed", []))

        if next_phase:
            result["next_phase"] = next_phase
            self.state["current_phase"] = next_phase

            # Create checkpoint at phase boundary
            checkpoint = self.create_phase_checkpoint(next_phase)
            if checkpoint:
                result["actions"].append({
                    "type": "checkpoint_created",
                    "path": checkpoint,
                    "phase": next_phase
                })

            # Update power mode state for status line
            self._update_power_mode_progress(
                current_phase=next_phase,
                phase_index=next_phase_index + 1,
                total_phases=len(phases),
                phases_completed=list(completed)
            )

            result["messages"].append(f"Transitioned to phase: {next_phase}")
        else:
            result["messages"].append("All phases complete!")
            result["actions"].append({
                "type": "deactivate_power_mode",
                "reason": "All phases complete"
            })
            self.deactivate_power_mode()

        self.save_state()
        return result

    def _update_power_mode_progress(
        self,
        current_phase: str,
        phase_index: int,
        total_phases: int,
        phases_completed: List[str]
    ):
        """Update power mode state file for status line integration."""
        try:
            if self.power_mode_state.exists():
                power_state = json.loads(self.power_mode_state.read_text())
                if power_state.get("active"):
                    power_state["current_phase"] = current_phase
                    power_state["phase_index"] = phase_index
                    power_state["total_phases"] = total_phases
                    power_state["phases_completed"] = phases_completed
                    # Calculate progress as percentage of phases complete
                    power_state["progress"] = len(phases_completed) / total_phases if total_phases > 0 else 0.0
                    self.power_mode_state.write_text(json.dumps(power_state, indent=2))
        except Exception:
            pass  # Don't fail if status update fails

    # =========================================================================
    # Phase-Transition Quality Gates (Issue #11)
    # =========================================================================

    def create_phase_checkpoint(self, phase_name: str) -> Optional[str]:
        """Create a checkpoint at phase boundary.

        Creates a git patch file containing all changes since the last checkpoint.
        This allows rollback to the start of a phase if gates fail.

        Args:
            phase_name: Name of the phase being started

        Returns:
            Path to checkpoint file or None if creation failed
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        issue_num = self.state.get("active_issue", "unknown")
        checkpoint_name = f"issue-{issue_num}-{phase_name}-{timestamp}.patch"
        checkpoint_path = self.phase_checkpoints_dir / checkpoint_name

        try:
            # Capture all uncommitted changes
            result = subprocess.run(
                "git diff HEAD",
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.cwd)
            )

            if result.stdout:
                checkpoint_path.write_text(result.stdout)
                print(f"Phase checkpoint created: {checkpoint_name}", file=sys.stderr)
                return str(checkpoint_path)
            else:
                # No changes to checkpoint - that's OK
                print(f"Phase checkpoint: no uncommitted changes", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Warning: Could not create phase checkpoint: {e}", file=sys.stderr)
            return None

    def run_phase_transition_gates(self, from_phase: str, to_phase: str) -> Dict[str, Any]:
        """Run quality gates before allowing phase transition.

        Executes configured quality gates (tsc, build, lint, etc.) and
        blocks the transition if gates fail.

        Args:
            from_phase: The phase being completed
            to_phase: The phase being started

        Returns:
            Dict with:
            - passed: bool - whether all gates passed
            - gates: list of gate results
            - can_proceed: bool - whether to proceed with transition
            - action: str - "proceed", "fix", "rollback", or "blocked"
        """
        result = {
            "passed": True,
            "gates": [],
            "can_proceed": True,
            "action": "proceed",
            "from_phase": from_phase,
            "to_phase": to_phase
        }

        # Skip if quality gates not available
        if not self.quality_gate:
            print("Quality gates not available - proceeding without validation", file=sys.stderr)
            return result

        # Run all enabled quality gates
        print(f"Running quality gates before {from_phase} → {to_phase} transition...", file=sys.stderr)
        gate_results = self.quality_gate.run_all_gates()

        result["gates"] = gate_results.get("gates", [])
        result["passed"] = gate_results.get("passed", True)

        if result["passed"]:
            print(f"All quality gates passed ({gate_results.get('duration', 0):.1f}s)", file=sys.stderr)
            return result

        # Gates failed - determine action
        result["can_proceed"] = False
        result["action"] = "blocked"

        # Format error message
        failed_gates = [g for g in result["gates"] if not g.get("success")]
        error_count = sum(len(g.get("errors", [])) for g in failed_gates)

        print(f"\nPhase transition blocked: {len(failed_gates)} gate(s) failed with {error_count} error(s)", file=sys.stderr)
        print(f"Cannot proceed from '{from_phase}' to '{to_phase}' until issues are resolved.", file=sys.stderr)

        for gate in failed_gates:
            print(f"\n  {gate['name']}:", file=sys.stderr)
            for error in gate.get("errors", [])[:3]:
                if "file" in error:
                    print(f"    {error['file']}:{error.get('line', '?')} - {error['message']}", file=sys.stderr)
                else:
                    print(f"    {error['message']}", file=sys.stderr)

        print("\nOptions:", file=sys.stderr)
        print("  1. Fix the errors and retry phase completion", file=sys.stderr)
        print("  2. Use '/popkit:issue phase rollback' to restore checkpoint", file=sys.stderr)
        print("  3. Use '/popkit:issue phase force' to proceed anyway (not recommended)", file=sys.stderr)

        return result

    def rollback_to_phase_start(self, phase_name: str) -> Dict[str, Any]:
        """Rollback to the checkpoint at the start of a phase.

        Finds the most recent checkpoint for the given phase and restores it.

        Args:
            phase_name: Name of the phase to rollback to

        Returns:
            Dict with rollback status and details
        """
        result = {
            "success": False,
            "phase": phase_name,
            "checkpoint": None,
            "message": ""
        }

        # Find most recent checkpoint for this phase
        issue_num = self.state.get("active_issue", "unknown")
        pattern = f"issue-{issue_num}-{phase_name}-*.patch"

        checkpoints = list(self.phase_checkpoints_dir.glob(pattern))
        if not checkpoints:
            result["message"] = f"No checkpoint found for phase '{phase_name}'"
            return result

        # Get most recent (sorted by filename which includes timestamp)
        latest = sorted(checkpoints)[-1]
        result["checkpoint"] = str(latest)

        try:
            # First, save current changes as a recovery file
            recovery_path = self.phase_checkpoints_dir / f"recovery-{datetime.now().strftime('%Y%m%d-%H%M%S')}.patch"
            current_diff = subprocess.run(
                "git diff HEAD",
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.cwd)
            )
            if current_diff.stdout:
                recovery_path.write_text(current_diff.stdout)
                print(f"Current changes saved to: {recovery_path}", file=sys.stderr)

            # Reset to clean state
            subprocess.run("git checkout .", shell=True, cwd=str(self.cwd), check=True)
            subprocess.run("git clean -fd", shell=True, cwd=str(self.cwd), check=True)

            # Apply the checkpoint patch
            subprocess.run(
                f"git apply {latest}",
                shell=True,
                cwd=str(self.cwd),
                check=True
            )

            result["success"] = True
            result["message"] = f"Rolled back to start of phase '{phase_name}'"
            print(f"Rollback successful. Restored to checkpoint: {latest.name}", file=sys.stderr)

        except subprocess.CalledProcessError as e:
            result["message"] = f"Rollback failed: {e}"
            print(f"Rollback failed: {e}", file=sys.stderr)
        except Exception as e:
            result["message"] = f"Rollback failed: {e}"
            print(f"Rollback failed: {e}", file=sys.stderr)

        return result

    def get_current_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        if not self.state.get("active_issue"):
            return {"active": False, "message": "No active issue workflow"}

        workflow = get_workflow_config(self.state["active_issue"])

        return {
            "active": True,
            "issue_number": self.state["active_issue"],
            "current_phase": self.state.get("current_phase"),
            "phases_completed": self.state.get("phases_completed", []),
            "phases_remaining": [
                p for p in workflow.get("suggested_phases", [])
                if p not in self.state.get("phases_completed", [])
            ],
            "activated_at": self.state.get("activated_at")
        }


def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_data = json.loads(sys.stdin.read())
        hook = IssueWorkflowHook()

        action = input_data.get("action", "status")

        if action == "start":
            issue_number = input_data.get("issue_number")
            if not issue_number:
                print(json.dumps({"error": "issue_number required"}))
                sys.exit(1)
            result = hook.start_issue_workflow(issue_number)

        elif action == "work":
            # Enhanced version with flag support (for /popkit:work command)
            args = input_data.get("args", "")
            flags = parse_work_args(args)

            if flags.get("error"):
                print(json.dumps({"error": flags["error"]}))
                sys.exit(1)

            issue_number = flags.get("issue_number")
            if not issue_number:
                print(json.dumps({"error": "issue_number required"}))
                sys.exit(1)

            result = hook.start_work_on_issue(issue_number, flags)

        elif action == "complete_phase":
            phase_name = input_data.get("phase_name")
            if not phase_name:
                print(json.dumps({"error": "phase_name required"}))
                sys.exit(1)
            force = input_data.get("force", False)
            result = hook.complete_phase(phase_name, force=force)

        elif action == "rollback_phase":
            phase_name = input_data.get("phase_name")
            if not phase_name:
                print(json.dumps({"error": "phase_name required"}))
                sys.exit(1)
            result = hook.rollback_to_phase_start(phase_name)

        elif action == "status":
            result = hook.get_current_status()

        else:
            result = {"error": f"Unknown action: {action}"}

        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    # CLI mode for testing
    if len(sys.argv) > 1:
        if sys.argv[1] == "start" and len(sys.argv) > 2:
            issue_num = int(sys.argv[2])
            hook = IssueWorkflowHook()
            result = hook.start_issue_workflow(issue_num)
            print(json.dumps(result, indent=2))

        elif sys.argv[1] == "work" and len(sys.argv) > 2:
            # Enhanced version with flag support
            # Usage: python issue-workflow.py work "#4 -p"
            args = " ".join(sys.argv[2:])
            flags = parse_work_args(args)

            if flags.get("error"):
                print(json.dumps({"error": flags["error"]}, indent=2))
                sys.exit(1)

            hook = IssueWorkflowHook()
            result = hook.start_work_on_issue(flags["issue_number"], flags)
            print(json.dumps(result, indent=2))

        elif sys.argv[1] == "status":
            hook = IssueWorkflowHook()
            result = hook.get_current_status()
            print(json.dumps(result, indent=2))

        elif sys.argv[1] == "complete" and len(sys.argv) > 2:
            phase = sys.argv[2]
            force = "--force" in sys.argv or "-f" in sys.argv
            hook = IssueWorkflowHook()
            result = hook.complete_phase(phase, force=force)
            print(json.dumps(result, indent=2))

        elif sys.argv[1] == "rollback" and len(sys.argv) > 2:
            phase = sys.argv[2]
            hook = IssueWorkflowHook()
            result = hook.rollback_to_phase_start(phase)
            print(json.dumps(result, indent=2))

        else:
            print("Usage:")
            print("  python issue-workflow.py start <issue_number>  # Start working on issue")
            print("  python issue-workflow.py work #4 -p            # Start with flags (Power Mode)")
            print("  python issue-workflow.py work #4 --solo        # Start without Power Mode")
            print("  python issue-workflow.py status                # Get current status")
            print("  python issue-workflow.py complete <phase>      # Complete a phase (runs quality gates)")
            print("  python issue-workflow.py complete <phase> -f   # Complete phase, ignore gate failures")
            print("  python issue-workflow.py rollback <phase>      # Rollback to phase checkpoint")
    else:
        main()
