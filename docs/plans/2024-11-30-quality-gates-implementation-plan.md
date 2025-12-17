# Quality Gates Implementation Plan

**Date:** 2024-11-30
**Design:** `docs/plans/2024-11-30-quality-gates-design.md`
**Branch:** `feature/quality-gates`
**Worktree:** `../popkit-quality-gates`

## Step 1: Create Hook Skeleton

**File:** `hooks/quality-gate.py`

Create the basic PostToolUse hook structure following existing patterns:

```python
#!/usr/bin/env python3
"""
Quality Gate Hook - PostToolUse validation for code integrity
Runs validation (tsc, build, lint) based on triggers and presents
interactive options on failure.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class QualityGateHook:
    def __init__(self):
        self.claude_dir = Path(".claude")
        self.state_file = self.claude_dir / "quality-gate-state.json"
        self.config_file = self.claude_dir / "quality-gates.json"
        self.checkpoints_dir = self.claude_dir / "checkpoints"

        # Ensure directories exist
        self.claude_dir.mkdir(exist_ok=True)
        self.checkpoints_dir.mkdir(exist_ok=True)

        # Load state and config
        self.state = self.load_state()
        self.config = self.load_config()

    # ... implementation methods
```

**Verification:** Hook loads without errors when invoked.

---

## Step 2: Implement Auto-Detection Logic

**Add to `hooks/quality-gate.py`:**

```python
def detect_gates(self) -> List[Dict[str, Any]]:
    """Auto-detect available quality gates based on project files."""
    gates = []
    cwd = Path.cwd()

    # TypeScript
    if (cwd / "tsconfig.json").exists():
        gates.append({
            "name": "typescript",
            "command": "npx tsc --noEmit",
            "timeout": 60,
            "enabled": True
        })

    # Package.json scripts
    pkg_path = cwd / "package.json"
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
            if "test" in scripts:
                gates.append({
                    "name": "test",
                    "command": "npm test",
                    "timeout": 300,
                    "enabled": False,  # Optional by default
                    "optional": True
                })
        except json.JSONDecodeError:
            pass

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
```

**Verification:** Run on a TypeScript project, verify tsc gate detected.

---

## Step 3: Implement Trigger Logic

**Add to `hooks/quality-gate.py`:**

```python
# High-risk patterns
HIGH_RISK_PATTERNS = [
    "tsconfig.json",
    "package.json",
    "*.config.js",
    "*.config.ts",
    ".env*"
]

def is_high_risk_action(self, tool_name: str, tool_args: Dict) -> bool:
    """Determine if action warrants immediate validation."""

    # Deletions are always high-risk
    if tool_name == "Delete":
        return True

    # Check file path against patterns
    file_path = tool_args.get("file_path", "")
    if file_path:
        filename = Path(file_path).name
        for pattern in HIGH_RISK_PATTERNS:
            if pattern.startswith("*"):
                if filename.endswith(pattern[1:]):
                    return True
            elif filename == pattern:
                return True

    # Check for import/export changes
    if tool_name in ["Edit", "MultiEdit"]:
        content = tool_args.get("new_string", "")
        old_content = tool_args.get("old_string", "")
        if any(kw in content or kw in old_content
               for kw in ["import ", "export ", "require("]):
            return True

    # Multi-file rapid changes
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
```

**Verification:** Editing `tsconfig.json` triggers immediate validation.

---

## Step 4: Implement Gate Execution

**Add to `hooks/quality-gate.py`:**

```python
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
            cwd=Path.cwd()
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
    results = {
        "passed": True,
        "gates": [],
        "total_errors": 0,
        "duration": 0
    }

    for gate in gates:
        if gate.get("optional") and not self.config.get("options", {}).get("run_tests"):
            continue

        gate_result = self.run_gate(gate)
        results["gates"].append(gate_result)
        results["duration"] += gate_result["duration"]

        if not gate_result["success"]:
            results["passed"] = False
            results["total_errors"] += len(gate_result["errors"])

            # Fail fast if configured
            if self.config.get("options", {}).get("fail_fast", True):
                break

    return results

def parse_errors(self, gate_name: str, output: str) -> List[Dict]:
    """Parse error output into structured format."""
    errors = []

    if gate_name == "typescript":
        # Parse TypeScript errors: file(line,col): error TS####: message
        import re
        for match in re.finditer(r'(.+)\((\d+),(\d+)\): error (TS\d+): (.+)', output):
            errors.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "code": match.group(4),
                "message": match.group(5)
            })
    else:
        # Generic: split by newlines, filter empty
        for line in output.split('\n'):
            line = line.strip()
            if line and ('error' in line.lower() or 'failed' in line.lower()):
                errors.append({"message": line})

    return errors[:10]  # Limit to first 10 errors
```

**Verification:** `tsc --noEmit` runs and errors are parsed correctly.

---

## Step 5: Implement Interactive Menu

**Add to `hooks/quality-gate.py`:**

```python
def present_failure_menu(self, results: Dict) -> str:
    """Present interactive menu on gate failure. Returns chosen action."""

    # Format error display
    output_lines = [
        "",
        "=" * 60,
        f"Quality Gate Failed: {results['gates'][0]['name']} ({results['total_errors']} errors)",
        "=" * 60,
        ""
    ]

    # Show errors (max 5)
    for gate in results["gates"]:
        if not gate["success"]:
            for error in gate["errors"][:5]:
                if "file" in error:
                    output_lines.append(f"  {error['file']}:{error['line']}")
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

    # Return action for hook response
    # Default to "fix" - errors injected into context
    return "fix"

def format_errors_for_context(self, results: Dict) -> str:
    """Format errors for injection into conversation context."""
    lines = ["Quality gate validation found the following issues:\n"]

    for gate in results["gates"]:
        if not gate["success"]:
            lines.append(f"## {gate['name'].title()} Errors\n")
            for error in gate["errors"]:
                if "file" in error:
                    lines.append(f"- `{error['file']}:{error['line']}` - {error['message']}")
                else:
                    lines.append(f"- {error['message']}")
            lines.append("")

    lines.append("\nPlease address these errors before continuing.")
    return '\n'.join(lines)
```

**Verification:** Failure menu displays correctly on TypeScript errors.

---

## Step 6: Implement Rollback Mechanism

**Add to `hooks/quality-gate.py`:**

```python
def create_checkpoint(self) -> str:
    """Create a checkpoint of current changes."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    patch_path = self.checkpoints_dir / f"{timestamp}.patch"

    try:
        # Capture all uncommitted changes
        result = subprocess.run(
            "git diff HEAD",
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        if result.stdout:
            patch_path.write_text(result.stdout)
            self.update_manifest(timestamp, patch_path)
            return str(patch_path)
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
        subprocess.run("git checkout .", shell=True, cwd=Path.cwd())
        subprocess.run("git clean -fd", shell=True, cwd=Path.cwd())

        # Reset state
        self.state["file_edit_count"] = 0
        self.state["recent_files"] = []
        self.state["recent_file_count"] = 0
        self.save_state()

        if patch_path:
            print(f"Rolled back. Changes saved to: {patch_path}", file=sys.stderr)
            print(f"To recover: git apply {patch_path}", file=sys.stderr)

        return True
    except Exception as e:
        print(f"Rollback failed: {e}", file=sys.stderr)
        return False

def update_manifest(self, timestamp: str, patch_path: Path):
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
        "path": str(patch_path),
        "trigger": "quality_gate_rollback"
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
        except:
            remaining.append(cp)

    manifest["checkpoints"] = remaining
```

**Verification:** Rollback saves patch and restores clean state.

---

## Step 7: Main Hook Entry Point

**Add to `hooks/quality-gate.py`:**

```python
def process(self, input_data: Dict) -> Dict:
    """Main processing function."""
    tool_name = input_data.get("tool_name", "")
    tool_args = input_data.get("tool_input", {})

    # Update counters
    self.update_state_counters(tool_name, tool_args)

    # Check if we should run gates
    if not self.should_run_gates(tool_name, tool_args):
        return {"continue": True}

    # Run quality gates
    results = self.run_all_gates()

    # Reset counter after running gates
    self.state["file_edit_count"] = 0
    self.save_state()

    if results["passed"]:
        self.state["last_checkpoint"] = datetime.now().isoformat()
        self.save_state()
        return {"continue": True, "message": "Quality gates passed"}

    # Gates failed - present options
    action = self.present_failure_menu(results)

    if action == "rollback":
        self.rollback()
        return {"continue": True, "message": "Rolled back to last checkpoint"}
    elif action == "pause":
        return {"continue": False, "stop_reason": "Quality gate failure - manual review requested"}
    elif action == "continue":
        return {"continue": True, "message": "Continuing despite errors (not recommended)"}
    else:  # fix (default)
        error_context = self.format_errors_for_context(results)
        return {
            "continue": True,
            "message": error_context,
            "inject_context": error_context
        }

def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_data = json.loads(sys.stdin.read())
        hook = QualityGateHook()
        result = hook.process(input_data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e), "continue": True}))
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()
```

---

## Step 8: Register Hook in hooks.json

**Edit:** `hooks/hooks.json`

Add after the `post-tool-use` hook:

```json
{
  "name": "quality-gate",
  "event": "PostToolUse",
  "command": "python",
  "args": ["hooks/quality-gate.py"],
  "description": "Validate code integrity after file modifications (tsc, build, lint)",
  "timeout": 180000,
  "enabled": true,
  "tools": ["Write", "Edit", "MultiEdit", "Delete"]
}
```

**Note:** Higher timeout (3 min) since gates can take time.

---

## Step 9: Test End-to-End

### Test Cases

1. **Basic trigger test**
   - Edit 5 files → gates should run
   - Verify tsc runs on TypeScript project

2. **High-risk trigger test**
   - Edit `tsconfig.json` → immediate gate run
   - Delete a file → immediate gate run

3. **Failure handling test**
   - Introduce TypeScript error → menu displays
   - Verify error parsing works

4. **Rollback test**
   - Make changes, trigger failure
   - Select rollback → verify patch saved
   - Verify clean state restored

5. **Config override test**
   - Create `.claude/quality-gates.json`
   - Disable lint gate
   - Verify lint skipped

---

## Estimated Timeline

| Step | Task | Estimated LOC |
|------|------|---------------|
| 1 | Hook skeleton | 50 |
| 2 | Auto-detection | 60 |
| 3 | Trigger logic | 80 |
| 4 | Gate execution | 100 |
| 5 | Interactive menu | 70 |
| 6 | Rollback | 80 |
| 7 | Main entry | 40 |
| 8 | Register hook | 10 |
| 9 | Testing | - |
| **Total** | | **~490 lines** |
