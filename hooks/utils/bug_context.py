#!/usr/bin/env python3
"""
Bug Context Capture Utility

Part of Issue #73 (In-Plugin Bug Reporting)

Captures context when a bug is reported, including:
- Recent tool calls
- Files touched
- Error messages
- Agent state
- Project context
- Git status
"""

import json
import os
import re
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ToolCall:
    """Represents a single tool call."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[str] = None
    timestamp: Optional[str] = None
    success: bool = True


@dataclass
class ErrorInfo:
    """Represents detected error information."""
    message: str
    error_type: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None


@dataclass
class ProjectContext:
    """Represents project context."""
    language: Optional[str] = None
    framework: Optional[str] = None
    services: List[str] = field(default_factory=list)
    detected_from: Optional[str] = None


@dataclass
class GitContext:
    """Represents git context."""
    branch: Optional[str] = None
    uncommitted_files: int = 0
    recent_commits: List[str] = field(default_factory=list)
    has_changes: bool = False


@dataclass
class BugContext:
    """Full bug context capture."""
    id: str
    description: str
    timestamp: str

    # Tool calls
    recent_tools: List[ToolCall] = field(default_factory=list)
    files_touched: List[str] = field(default_factory=list)

    # Errors
    errors: List[ErrorInfo] = field(default_factory=list)

    # State
    agent_progress: Optional[float] = None
    current_task: Optional[str] = None

    # Project
    project: Optional[ProjectContext] = None
    git: Optional[GitContext] = None

    # Analysis
    stuck_patterns: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


# =============================================================================
# ERROR PATTERNS
# =============================================================================

ERROR_PATTERNS = [
    r"error[:\s]",
    r"Error[:\s]",
    r"ERROR[:\s]",
    r"exception[:\s]",
    r"Exception[:\s]",
    r"failed",
    r"Failed",
    r"FAILED",
    r"failure",
    r"TypeError",
    r"SyntaxError",
    r"ReferenceError",
    r"RuntimeError",
    r"ValueError",
    r"KeyError",
    r"AttributeError",
    r"permission denied",
    r"access denied",
    r"unauthorized",
    r"not found",
    r"404",
    r"does not exist",
    r"timeout",
    r"timed out",
    r"ETIMEDOUT",
    r"ECONNREFUSED",
    r"ENOENT",
]

STUCK_PATTERNS = [
    ("same_file_edited", "Same file edited 3+ times"),
    ("same_command_run", "Same command run 3+ times"),
    ("build_failed", "Build command failed"),
    ("test_failed", "Tests failing"),
    ("no_progress", "No progress in 10+ tool calls"),
]


# =============================================================================
# CONTEXT CAPTURE
# =============================================================================

class BugContextCapture:
    """Captures bug context from session state."""

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
        self.bugs_dir = Path(self.working_dir) / ".claude" / "bugs"

    def capture(
        self,
        description: str,
        recent_tools: Optional[List[Dict]] = None,
        agent_state: Optional[Dict] = None,
        verbose: bool = False
    ) -> BugContext:
        """
        Capture full bug context.

        Args:
            description: User's bug description
            recent_tools: List of recent tool calls
            agent_state: Current agent state
            verbose: Include full tool outputs

        Returns:
            BugContext with all captured information
        """
        # Generate bug ID
        timestamp = datetime.now().isoformat()
        bug_id = self._generate_bug_id(description, timestamp)

        # Create context
        ctx = BugContext(
            id=bug_id,
            description=description,
            timestamp=timestamp
        )

        # Capture tool calls
        if recent_tools:
            ctx.recent_tools = self._parse_tool_calls(recent_tools, verbose)
            ctx.files_touched = self._extract_files_touched(recent_tools)
            ctx.errors = self._extract_errors(recent_tools)

        # Capture agent state
        if agent_state:
            ctx.agent_progress = agent_state.get("progress")
            ctx.current_task = agent_state.get("current_task")

        # Capture project context
        ctx.project = self._detect_project_context()

        # Capture git context
        ctx.git = self._capture_git_context()

        # Analyze stuck patterns
        ctx.stuck_patterns = self._detect_stuck_patterns(recent_tools or [])

        # Generate suggestions
        ctx.suggested_actions = self._generate_suggestions(ctx)

        return ctx

    def save(self, ctx: BugContext) -> Path:
        """Save bug context to local storage."""
        self.bugs_dir.mkdir(parents=True, exist_ok=True)

        file_path = self.bugs_dir / f"{ctx.id}.json"
        file_path.write_text(ctx.to_json())

        return file_path

    def list_bugs(self, limit: int = 10) -> List[Dict]:
        """List locally logged bugs."""
        if not self.bugs_dir.exists():
            return []

        bugs = []
        for f in sorted(self.bugs_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(f.read_text())
                bugs.append({
                    "id": data.get("id"),
                    "description": data.get("description"),
                    "timestamp": data.get("timestamp"),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return bugs

    def get_bug(self, bug_id: str) -> Optional[BugContext]:
        """Get a specific bug by ID."""
        file_path = self.bugs_dir / f"{bug_id}.json"
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return self._dict_to_context(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def clear_bugs(self, before: Optional[str] = None, bug_id: Optional[str] = None) -> int:
        """Clear bug logs."""
        if not self.bugs_dir.exists():
            return 0

        cleared = 0

        if bug_id:
            # Clear specific bug
            file_path = self.bugs_dir / f"{bug_id}.json"
            if file_path.exists():
                file_path.unlink()
                cleared = 1
        elif before:
            # Clear bugs before date
            before_dt = datetime.fromisoformat(before)
            for f in self.bugs_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    bug_dt = datetime.fromisoformat(data.get("timestamp", ""))
                    if bug_dt < before_dt:
                        f.unlink()
                        cleared += 1
                except (json.JSONDecodeError, ValueError):
                    continue
        else:
            # Clear all
            for f in self.bugs_dir.glob("*.json"):
                f.unlink()
                cleared += 1

        return cleared

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _generate_bug_id(self, description: str, timestamp: str) -> str:
        """Generate unique bug ID."""
        date_part = timestamp.split("T")[0]
        hash_input = f"{description}{timestamp}"
        hash_part = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"bug-{date_part}-{hash_part}"

    def _parse_tool_calls(self, tools: List[Dict], verbose: bool) -> List[ToolCall]:
        """Parse tool calls from raw data."""
        parsed = []
        for t in tools[-10:]:  # Last 10
            output = t.get("tool_output", "")
            if not verbose and output and len(output) > 200:
                output = output[:200] + "..."

            parsed.append(ToolCall(
                tool_name=t.get("tool_name", "unknown"),
                tool_input=t.get("tool_input", {}),
                tool_output=output,
                timestamp=t.get("timestamp"),
                success=not self._has_error(output or "")
            ))
        return parsed

    def _extract_files_touched(self, tools: List[Dict]) -> List[str]:
        """Extract unique files from tool calls."""
        files = set()
        for t in tools:
            tool_input = t.get("tool_input", {})

            # File path from Read/Edit/Write
            if "file_path" in tool_input:
                files.add(tool_input["file_path"])

            # Pattern from Glob
            if "pattern" in tool_input and "path" in tool_input:
                files.add(f"{tool_input['path']}/{tool_input['pattern']}")

        return list(files)

    def _extract_errors(self, tools: List[Dict]) -> List[ErrorInfo]:
        """Extract errors from tool outputs."""
        errors = []
        for t in tools:
            output = t.get("tool_output", "")
            if not output:
                continue

            for pattern in ERROR_PATTERNS:
                if re.search(pattern, output, re.IGNORECASE):
                    # Extract error message
                    lines = output.split("\n")
                    for line in lines:
                        if re.search(pattern, line, re.IGNORECASE):
                            errors.append(ErrorInfo(
                                message=line.strip()[:200],
                                error_type=self._classify_error(line)
                            ))
                            break
                    break

        return errors[:5]  # Max 5 errors

    def _has_error(self, output: str) -> bool:
        """Check if output contains error."""
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                return True
        return False

    def _classify_error(self, message: str) -> Optional[str]:
        """Classify error type from message."""
        error_types = [
            "TypeError", "SyntaxError", "ReferenceError", "RuntimeError",
            "ValueError", "KeyError", "AttributeError", "ImportError",
            "ConnectionError", "TimeoutError", "PermissionError"
        ]
        for et in error_types:
            if et in message:
                return et
        return None

    def _detect_project_context(self) -> ProjectContext:
        """Detect project language and framework."""
        ctx = ProjectContext()

        # Check for common project files
        project_dir = Path(self.working_dir)

        if (project_dir / "package.json").exists():
            ctx.language = "TypeScript/JavaScript"
            try:
                pkg = json.loads((project_dir / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "next" in deps:
                    ctx.framework = "Next.js"
                elif "react" in deps:
                    ctx.framework = "React"
                elif "vue" in deps:
                    ctx.framework = "Vue.js"
                elif "express" in deps:
                    ctx.framework = "Express"

                # Detect services
                if "prisma" in deps or "@prisma/client" in deps:
                    ctx.services.append("Prisma")
                if "supabase" in deps or "@supabase/supabase-js" in deps:
                    ctx.services.append("Supabase")
                if "redis" in deps or "ioredis" in deps:
                    ctx.services.append("Redis")
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        elif (project_dir / "requirements.txt").exists() or (project_dir / "pyproject.toml").exists():
            ctx.language = "Python"
            ctx.detected_from = "requirements.txt or pyproject.toml"

        elif (project_dir / "Cargo.toml").exists():
            ctx.language = "Rust"

        elif (project_dir / "go.mod").exists():
            ctx.language = "Go"

        return ctx

    def _capture_git_context(self) -> GitContext:
        """Capture git status."""
        ctx = GitContext()

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.working_dir
            )
            if result.returncode == 0:
                ctx.branch = result.stdout.strip()

            # Get uncommitted file count
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=self.working_dir
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.strip().split("\n") if l]
                ctx.uncommitted_files = len(lines)
                ctx.has_changes = len(lines) > 0

            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                capture_output=True, text=True, cwd=self.working_dir
            )
            if result.returncode == 0:
                ctx.recent_commits = [
                    l.strip() for l in result.stdout.strip().split("\n") if l
                ][:3]

        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return ctx

    def _detect_stuck_patterns(self, tools: List[Dict]) -> List[str]:
        """Detect stuck patterns from tool calls."""
        patterns = []

        if not tools:
            return patterns

        # Same file edited 3+ times
        file_edits: Dict[str, int] = {}
        for t in tools:
            if t.get("tool_name") == "Edit":
                fp = t.get("tool_input", {}).get("file_path", "")
                file_edits[fp] = file_edits.get(fp, 0) + 1

        for fp, count in file_edits.items():
            if count >= 3:
                patterns.append(f"Same file edited {count} times: {Path(fp).name}")

        # Same command run 3+ times
        command_runs: Dict[str, int] = {}
        for t in tools:
            if t.get("tool_name") == "Bash":
                cmd = t.get("tool_input", {}).get("command", "")[:50]
                command_runs[cmd] = command_runs.get(cmd, 0) + 1

        for cmd, count in command_runs.items():
            if count >= 3:
                patterns.append(f"Same command run {count} times: {cmd}")

        # Build/test failures
        for t in tools:
            output = t.get("tool_output", "")
            if t.get("tool_name") == "Bash":
                cmd = t.get("tool_input", {}).get("command", "")
                if "build" in cmd.lower() and self._has_error(output):
                    patterns.append("Build command failed")
                elif "test" in cmd.lower() and self._has_error(output):
                    patterns.append("Test command failed")

        return list(set(patterns))

    def _generate_suggestions(self, ctx: BugContext) -> List[str]:
        """Generate suggested actions based on context."""
        suggestions = []

        # Based on stuck patterns
        if "Same file edited" in str(ctx.stuck_patterns):
            suggestions.append("Consider stepping back and reviewing the approach")
            suggestions.append("Check if there's a simpler solution")

        if "Build command failed" in str(ctx.stuck_patterns):
            suggestions.append("Review build error output for specific issues")
            suggestions.append("Check for missing dependencies or type errors")

        if "Test command failed" in str(ctx.stuck_patterns):
            suggestions.append("Run tests in isolation to identify failing cases")
            suggestions.append("Check test fixtures and mock data")

        # Based on errors
        for error in ctx.errors:
            if error.error_type == "TypeError":
                suggestions.append("Check for null/undefined values")
            elif error.error_type == "SyntaxError":
                suggestions.append("Review recent code changes for syntax issues")

        # Default suggestions
        if not suggestions:
            suggestions.append("Review recent changes and error messages")
            suggestions.append("Try a different approach if current one isn't working")

        return suggestions[:5]

    def _dict_to_context(self, data: Dict) -> BugContext:
        """Convert dictionary to BugContext."""
        ctx = BugContext(
            id=data["id"],
            description=data["description"],
            timestamp=data["timestamp"]
        )

        if data.get("recent_tools"):
            ctx.recent_tools = [
                ToolCall(**t) for t in data["recent_tools"]
            ]

        ctx.files_touched = data.get("files_touched", [])

        if data.get("errors"):
            ctx.errors = [ErrorInfo(**e) for e in data["errors"]]

        ctx.agent_progress = data.get("agent_progress")
        ctx.current_task = data.get("current_task")

        if data.get("project"):
            ctx.project = ProjectContext(**data["project"])

        if data.get("git"):
            ctx.git = GitContext(**data["git"])

        ctx.stuck_patterns = data.get("stuck_patterns", [])
        ctx.suggested_actions = data.get("suggested_actions", [])

        return ctx


# =============================================================================
# FORMATTING
# =============================================================================

def format_bug_report(ctx: BugContext, verbose: bool = False) -> str:
    """Format bug context as readable report."""
    lines = [
        "Bug Report",
        "=" * 50,
        f"ID: {ctx.id}",
        f"Time: {ctx.timestamp}",
        "",
        f"Description: {ctx.description}",
        ""
    ]

    # Project context
    if ctx.project and ctx.project.language:
        lines.append("Context:")
        lines.append(f"  Language: {ctx.project.language}")
        if ctx.project.framework:
            lines.append(f"  Framework: {ctx.project.framework}")
        if ctx.project.services:
            lines.append(f"  Services: {', '.join(ctx.project.services)}")

    # Git context
    if ctx.git:
        if ctx.git.branch:
            lines.append(f"  Branch: {ctx.git.branch}")
        if ctx.git.uncommitted_files:
            lines.append(f"  Uncommitted: {ctx.git.uncommitted_files} files")
        lines.append("")

    # Agent state
    if ctx.current_task or ctx.agent_progress:
        lines.append("Agent State:")
        if ctx.current_task:
            lines.append(f"  Task: {ctx.current_task}")
        if ctx.agent_progress is not None:
            lines.append(f"  Progress: {ctx.agent_progress:.0%}")
        lines.append("")

    # Recent actions
    if ctx.recent_tools:
        lines.append("Recent Actions:")
        for i, tool in enumerate(ctx.recent_tools[-5:], 1):
            tool_input = tool.tool_input
            if tool.tool_name == "Edit":
                fp = tool_input.get("file_path", "unknown")
                lines.append(f"  {i}. Edit {Path(fp).name}")
            elif tool.tool_name == "Bash":
                cmd = tool_input.get("command", "")[:40]
                status = "" if tool.success else " (failed)"
                lines.append(f"  {i}. Bash: {cmd}{status}")
            elif tool.tool_name == "Read":
                fp = tool_input.get("file_path", "unknown")
                lines.append(f"  {i}. Read {Path(fp).name}")
            else:
                lines.append(f"  {i}. {tool.tool_name}")
        lines.append("")

    # Errors
    if ctx.errors:
        lines.append("Errors Detected:")
        for error in ctx.errors[:3]:
            error_type = f"[{error.error_type}] " if error.error_type else ""
            lines.append(f"  {error_type}{error.message[:100]}")
        lines.append("")

    # Stuck patterns
    if ctx.stuck_patterns:
        lines.append("Stuck Patterns:")
        for pattern in ctx.stuck_patterns:
            lines.append(f"  - {pattern}")
        lines.append("")

    # Suggestions
    if ctx.suggested_actions:
        lines.append("Suggested Actions:")
        for action in ctx.suggested_actions:
            lines.append(f"  - {action}")
        lines.append("")

    return "\n".join(lines)


def format_github_issue(ctx: BugContext) -> str:
    """Format bug context as GitHub issue body."""
    lines = [
        "## Bug Report (Auto-Generated)",
        "",
        f"**Description:** {ctx.description}",
        "",
        "**Context:**"
    ]

    if ctx.project and ctx.project.language:
        lines.append(f"- Language: {ctx.project.language}")
        if ctx.project.framework:
            lines.append(f"- Framework: {ctx.project.framework}")

    if ctx.git:
        if ctx.git.branch:
            lines.append(f"- Branch: {ctx.git.branch}")

    if ctx.current_task:
        lines.append(f"- Current Task: {ctx.current_task}")

    lines.append("")

    # Recent actions
    if ctx.recent_tools:
        lines.append("**Recent Actions:**")
        for i, tool in enumerate(ctx.recent_tools[-5:], 1):
            tool_input = tool.tool_input
            if tool.tool_name == "Edit":
                fp = tool_input.get("file_path", "unknown")
                lines.append(f"{i}. Edit {Path(fp).name}")
            elif tool.tool_name == "Bash":
                cmd = tool_input.get("command", "")[:40]
                status = " (failed)" if not tool.success else ""
                lines.append(f"{i}. Bash: `{cmd}`{status}")
            elif tool.tool_name == "Read":
                fp = tool_input.get("file_path", "unknown")
                lines.append(f"{i}. Read {Path(fp).name}")
            else:
                lines.append(f"{i}. {tool.tool_name}")
        lines.append("")

    # Errors
    if ctx.errors:
        lines.append("**Error Output:**")
        lines.append("```")
        for error in ctx.errors[:3]:
            lines.append(error.message[:200])
        lines.append("```")
        lines.append("")

    # Progress
    if ctx.agent_progress is not None:
        lines.append(f"**Agent Progress:** {ctx.agent_progress:.0%}")
        lines.append("")

    # Stuck patterns
    if ctx.stuck_patterns:
        lines.append("**Stuck Patterns Detected:**")
        for pattern in ctx.stuck_patterns:
            lines.append(f"- {pattern}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by PopKit Bug Reporter*")

    return "\n".join(lines)


# =============================================================================
# PATTERN SHARING
# =============================================================================

def share_bug_pattern(ctx: BugContext) -> Optional[Dict[str, Any]]:
    """
    Share bug pattern to collective learning database.

    Anonymizes the bug context and submits it as a pattern.
    Requires POPKIT_API_KEY environment variable.

    Returns:
        Result dict with status, pattern_id, or None if sharing failed
    """
    import sys
    import os

    # Try to import pattern client
    try:
        power_mode_path = Path(__file__).parent.parent.parent / "power-mode"
        sys.path.insert(0, str(power_mode_path))
        from pattern_client import PatternClient, PatternContext
    except ImportError:
        return None

    # Check for API key
    if not os.environ.get("POPKIT_API_KEY"):
        return None

    try:
        client = PatternClient()

        # Build trigger from errors and stuck patterns
        trigger_parts = []
        if ctx.errors:
            for error in ctx.errors[:2]:
                trigger_parts.append(error.message)
        if ctx.stuck_patterns:
            trigger_parts.extend(ctx.stuck_patterns[:2])
        if not trigger_parts:
            trigger_parts.append(ctx.description)

        trigger = ". ".join(trigger_parts)

        # Build solution from suggestions
        solution_parts = [ctx.description]
        if ctx.suggested_actions:
            solution_parts.extend(ctx.suggested_actions[:3])

        solution = ". ".join(solution_parts)

        # Build context
        pattern_context = PatternContext(
            languages=[ctx.project.language] if ctx.project and ctx.project.language else [],
            frameworks=[ctx.project.framework] if ctx.project and ctx.project.framework else [],
            error_types=[e.error_type for e in ctx.errors if e.error_type]
        )

        # Submit pattern (auto-anonymizes)
        result = client.submit_pattern(
            trigger=trigger,
            solution=solution,
            context=pattern_context,
            anonymize=True
        )

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}


def search_patterns_for_bug(ctx: BugContext) -> List[Dict[str, Any]]:
    """
    Search for patterns that might help with this bug.

    Returns:
        List of matching patterns with solutions
    """
    import sys
    import os

    # Try to import pattern client
    try:
        power_mode_path = Path(__file__).parent.parent.parent / "power-mode"
        sys.path.insert(0, str(power_mode_path))
        from pattern_client import PatternClient, PatternContext
    except ImportError:
        return []

    # Check for API key
    if not os.environ.get("POPKIT_API_KEY"):
        return []

    try:
        client = PatternClient()

        # Build query from errors and description
        query_parts = [ctx.description]
        if ctx.errors:
            for error in ctx.errors[:2]:
                query_parts.append(error.message)

        query = " ".join(query_parts)

        # Build context
        pattern_context = PatternContext(
            languages=[ctx.project.language] if ctx.project and ctx.project.language else [],
            frameworks=[ctx.project.framework] if ctx.project and ctx.project.framework else []
        )

        # Search patterns
        patterns = client.search_patterns(
            query=query,
            context=pattern_context,
            limit=3,
            threshold=0.6
        )

        return [
            {
                "id": p.id,
                "trigger": p.trigger,
                "solution": p.solution,
                "similarity": p.similarity,
                "quality_score": p.quality_score
            }
            for p in patterns
        ]

    except Exception:
        return []


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing bug context capture."""
    import sys

    print("Bug Context Capture Test")
    print("=" * 50)

    capture = BugContextCapture()

    # Simulate some tool calls
    mock_tools = [
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/auth/oauth.ts"},
            "tool_output": "export function handleAuth() { ... }"
        },
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/auth/oauth.ts", "old_string": "a", "new_string": "b"},
            "tool_output": "File edited"
        },
        {
            "tool_name": "Bash",
            "tool_input": {"command": "npm run build"},
            "tool_output": "TypeError: Cannot read property 'token' of undefined"
        },
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/auth/oauth.ts", "old_string": "b", "new_string": "c"},
            "tool_output": "File edited"
        },
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/auth/oauth.ts", "old_string": "c", "new_string": "d"},
            "tool_output": "File edited"
        },
    ]

    mock_state = {
        "progress": 0.3,
        "current_task": "Implement OAuth flow"
    }

    # Capture context
    ctx = capture.capture(
        description="Agent got stuck on OAuth flow",
        recent_tools=mock_tools,
        agent_state=mock_state
    )

    # Print report
    print(format_bug_report(ctx))

    # Print GitHub issue format
    print("\n" + "=" * 50)
    print("GitHub Issue Format:")
    print("=" * 50)
    print(format_github_issue(ctx))


if __name__ == "__main__":
    main()
