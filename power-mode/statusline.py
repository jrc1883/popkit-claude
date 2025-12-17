#!/usr/bin/env python3
"""
PopKit Status Line Widget System (Issue #79)

Displays configurable widgets in Claude Code status line.

Available Widgets:
- efficiency: Token savings, patterns matched, duplicates skipped
- power_mode: Power Mode status with issue, phase, agents
- workflow: Current workflow progress
- health: Build, test, lint status from morning routine

Configuration in .claude/popkit/config.json:
{
  "statusline": {
    "widgets": ["efficiency", "power_mode"],
    "compact_mode": true
  }
}

Usage:
  Configured in .claude/settings.json as statusLine command
  python statusline.py                 # Full status line
  python statusline.py --widgets       # List available widgets
  python statusline.py efficiency      # Single widget output
  python statusline.py status          # Detailed status

Part of the popkit plugin system.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


# ANSI color codes
class Colors:
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RED = "\033[31m"
    WHITE = "\033[37m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class WidgetConfig:
    """Configuration for status line widgets."""
    widgets: List[str]
    compact_mode: bool = True
    show_hints: bool = True
    separator: str = " | "

    @classmethod
    def default(cls) -> 'WidgetConfig':
        """Get default configuration."""
        return cls(
            widgets=["popkit", "efficiency", "power_mode"],
            compact_mode=True,
            show_hints=True
        )

    @classmethod
    def load(cls) -> 'WidgetConfig':
        """Load configuration from file."""
        # Try project-local config
        local_config = Path.cwd() / ".claude" / "popkit" / "config.json"
        home_config = Path.home() / ".claude" / "popkit" / "config.json"

        config_file = local_config if local_config.exists() else home_config

        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    sl_config = data.get("statusline", {})
                    return cls(
                        widgets=sl_config.get("widgets", cls.default().widgets),
                        compact_mode=sl_config.get("compact_mode", True),
                        show_hints=sl_config.get("show_hints", True),
                        separator=sl_config.get("separator", " | ")
                    )
            except (json.JSONDecodeError, IOError):
                pass

        return cls.default()


# =============================================================================
# DATA LOADERS
# =============================================================================

def get_git_root() -> Optional[Path]:
    """Get the git repository root directory (Issue #66).

    Returns:
        Path to git root, or None if not in a git repo.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_project_root() -> Path:
    """Get project root directory (Issue #66 - bug fix).

    Priority:
    1. Git repository root (most reliable)
    2. Directory containing .claude/
    3. Current working directory (fallback)

    Returns:
        Path to project root.
    """
    # Try git root first
    git_root = get_git_root()
    if git_root:
        return git_root

    # Look for .claude directory walking up from cwd
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".claude").exists():
            return parent

    # Fallback to cwd
    return cwd


def get_state_file_path() -> Path:
    """Get path to power mode state file (Issue #66 - bug fix).

    Uses get_project_root() instead of Path.cwd() for consistency.
    """
    project_root = get_project_root()

    # Try project-local first (.claude/popkit/)
    local_state = project_root / ".claude" / "popkit" / "power-mode-state.json"
    if local_state.exists():
        return local_state

    # Fall back to user home (.claude/popkit/)
    home_state = Path.home() / ".claude" / "popkit" / "power-mode-state.json"
    return home_state


def load_power_mode_state() -> Dict[str, Any]:
    """Load Power Mode state from file.

    Returns:
        State dict or {"active": False} if not found
    """
    state_file = get_state_file_path()

    if not state_file.exists():
        return {"active": False}

    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, IOError):
        return {"active": False}


def load_efficiency_metrics() -> Optional[Dict[str, Any]]:
    """Load efficiency metrics from file (Issue #66 - bug fix).

    Returns:
        Metrics dict or None if not found
    """
    project_root = get_project_root()

    # Try project-local first
    local_metrics = project_root / ".claude" / "popkit" / "efficiency-metrics.json"
    if local_metrics.exists():
        try:
            return json.loads(local_metrics.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    # Fall back to home
    home_metrics = Path.home() / ".claude" / "popkit" / "efficiency-metrics.json"
    if home_metrics.exists():
        try:
            return json.loads(home_metrics.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    return None


def load_workflow_state() -> Optional[Dict[str, Any]]:
    """Load current workflow state (Issue #66 - bug fix).

    Returns:
        Workflow state dict or None if not found
    """
    project_root = get_project_root()

    # Try project-local STATUS.json
    local_status = project_root / ".claude" / "STATUS.json"
    if local_status.exists():
        try:
            with open(local_status) as f:
                data = json.load(f)
                return data.get("workflow", {})
        except (json.JSONDecodeError, IOError):
            pass

    return None


def load_health_state() -> Optional[Dict[str, Any]]:
    """Load health check state from morning routine (Issue #66 - bug fix).

    Returns:
        Health state dict or None if not found
    """
    project_root = get_project_root()

    # Try project-local health state
    local_health = project_root / ".claude" / "popkit" / "health-state.json"
    if local_health.exists():
        try:
            return json.loads(local_health.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    # Fall back to home
    home_health = Path.home() / ".claude" / "popkit" / "health-state.json"
    if home_health.exists():
        try:
            return json.loads(home_health.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    return None


def format_tokens_saved(tokens: int) -> str:
    """Format token count for display.

    Args:
        tokens: Number of tokens

    Returns:
        Formatted string (e.g., "2.4k", "500")
    """
    if tokens >= 1000:
        return f"{tokens/1000:.1f}k"
    return str(tokens)


def format_progress_bar(progress: float, width: int = 10) -> str:
    """Format a progress bar.

    Args:
        progress: Progress value (0.0 to 1.0)
        width: Bar width in characters

    Returns:
        Formatted progress bar string
    """
    progress = max(0.0, min(1.0, progress))  # Clamp to [0, 1]
    filled = int(progress * width)
    empty = width - filled

    return f"[{'#' * filled}{'-' * empty}]"


def format_runtime(activated_at: str) -> str:
    """Format runtime duration.

    Args:
        activated_at: ISO format timestamp

    Returns:
        Human-readable duration (e.g., "5m", "1h 23m")
    """
    try:
        start = datetime.fromisoformat(activated_at.replace('Z', '+00:00'))
        now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
        delta = now - start

        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return "?"


def format_efficiency_indicator(metrics: Optional[Dict[str, Any]]) -> str:
    """Format efficiency indicator for status line.

    Args:
        metrics: Efficiency metrics dict

    Returns:
        Efficiency indicator string or empty if no metrics
    """
    if not metrics:
        return ""

    # Calculate tokens saved using the same formula as efficiency_tracker.py
    duplicates = metrics.get("duplicates_skipped", 0)
    patterns = metrics.get("patterns_matched", 0)
    context_reuse = metrics.get("context_reuse_count", 0)
    bugs = metrics.get("bugs_detected", 0)
    stuck = metrics.get("stuck_patterns_detected", 0)
    insight_lengths = metrics.get("insight_lengths", [])

    # Token estimation constants
    tokens_saved = (
        duplicates * 100 +
        patterns * 500 +
        context_reuse * 200 +
        bugs * 300 +
        stuck * 800 +
        int(sum(insight_lengths) * 0.25)
    )

    if tokens_saved == 0:
        return ""

    return f"~{format_tokens_saved(tokens_saved)} saved"


def format_active_skills_indicator() -> str:
    """Format active skills indicator for status line (Issue #188).

    Queries the activity ledger to show what skills are currently running.

    Returns:
        Active skills indicator string or empty if none active
    """
    try:
        # Import lazily to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "utils"))
        from context_storage import get_context_storage

        storage = get_context_storage()
        active = storage.get_active_skills()

        if not active:
            return ""

        # Format: skill (or skill+N if multiple)
        if len(active) == 1:
            skill_display = active[0].replace("pop-", "")[:12]
        else:
            skill_display = f"{active[0].replace('pop-', '')[:8]}+{len(active)-1}"

        return f"{Colors.MAGENTA}[{skill_display}]{Colors.RESET}"

    except Exception:
        # Don't break status line if activity check fails
        return ""


def format_streaming_indicator(state: Dict[str, Any]) -> str:
    """Format streaming indicator for status line.

    Args:
        state: Power Mode state dict

    Returns:
        Streaming indicator string or empty if no active streams
    """
    streaming = state.get("streaming", {})
    active_streams = streaming.get("active_streams", 0)

    if active_streams == 0:
        return ""

    # Animation frames for streaming
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Use seconds to cycle through frames
    frame_index = int(datetime.now().timestamp() * 4) % len(frames)
    spinner = frames[frame_index]

    agents = streaming.get("agents_streaming", [])
    tool = streaming.get("latest_tool", "")

    if agents:
        agent_display = agents[0][:8]  # First 8 chars of first agent
        if len(agents) > 1:
            agent_display += f"+{len(agents)-1}"
    else:
        agent_display = ""

    if tool:
        return f"{Colors.CYAN}{spinner}{Colors.RESET} {agent_display}:{tool}"
    else:
        return f"{Colors.CYAN}{spinner}{Colors.RESET} {active_streams} stream{'s' if active_streams > 1 else ''}"


# =============================================================================
# WIDGET FUNCTIONS (Issue #79)
# =============================================================================

def widget_popkit(compact: bool = True) -> str:
    """
    PopKit branding widget.

    Format: [PopKit] or [PK] in compact mode
    """
    if compact:
        return f"{Colors.YELLOW}{Colors.BOLD}[PK]{Colors.RESET}"
    return f"{Colors.YELLOW}{Colors.BOLD}[PopKit]{Colors.RESET}"


def widget_efficiency(compact: bool = True) -> str:
    """
    Efficiency metrics widget.

    Format: ~2.4k saved | P:3 D:12
    Compact: ~2.4k
    """
    metrics = load_efficiency_metrics()
    if not metrics:
        return ""

    # Calculate tokens saved
    duplicates = metrics.get("duplicates_skipped", 0)
    patterns = metrics.get("patterns_matched", 0)
    context_reuse = metrics.get("context_reuse_count", 0)
    bugs = metrics.get("bugs_detected", 0)
    stuck = metrics.get("stuck_patterns_detected", 0)
    insight_lengths = metrics.get("insight_lengths", [])

    tokens_saved = (
        duplicates * 100 +
        patterns * 500 +
        context_reuse * 200 +
        bugs * 300 +
        stuck * 800 +
        int(sum(insight_lengths) * 0.25)
    )

    if tokens_saved == 0 and patterns == 0 and duplicates == 0:
        return ""

    tokens_str = format_tokens_saved(tokens_saved)

    if compact:
        return f"{Colors.CYAN}~{tokens_str}{Colors.RESET}"

    # Full format with breakdown
    parts = [f"~{tokens_str} saved"]
    if patterns > 0:
        parts.append(f"P:{patterns}")
    if duplicates > 0:
        parts.append(f"D:{duplicates}")

    return f"{Colors.CYAN}{' '.join(parts)}{Colors.RESET}"


def widget_power_mode(compact: bool = True) -> str:
    """
    Power Mode status widget.

    Format: #45 Phase 3/7 [####----] 40%
    Compact: #45 3/7 40%
    """
    state = load_power_mode_state()
    if not state.get("active"):
        return ""

    issue_num = state.get("active_issue")
    current_phase = state.get("current_phase", "")
    phase_index = state.get("phase_index", 0)
    total_phases = state.get("total_phases", 0)
    progress = state.get("progress", 0.0)
    percent = int(progress * 100)

    # Agent count
    agents = state.get("config", {}).get("agents", [])
    agent_count = len(agents) if agents else 0

    # Insights
    insights_shared = state.get("insights_shared", 0)
    insights_received = state.get("insights_received", 0)

    parts = []

    # Issue number
    if issue_num:
        parts.append(f"{Colors.MAGENTA}#{issue_num}{Colors.RESET}")

    if compact:
        # Compact: #45 3/7 40%
        if total_phases > 0:
            parts.append(f"{phase_index}/{total_phases}")
        parts.append(f"{percent}%")
    else:
        # Full: Phase 3/7 | Agents: 4 | [####----] 40%
        if total_phases > 0:
            parts.append(f"{Colors.BLUE}Phase {phase_index}/{total_phases}{Colors.RESET}")
        if agent_count > 0:
            parts.append(f"Agents:{agent_count}")
        if insights_shared > 0 or insights_received > 0:
            parts.append(f"{insights_shared}↑{insights_received}↓")
        bar = format_progress_bar(progress, 8)
        parts.append(f"{Colors.GREEN}{bar} {percent}%{Colors.RESET}")

    return " ".join(parts)


def widget_batch_status(compact: bool = True) -> str:
    """
    Batch spawning status widget (Issue #253).

    Display batch number and agent information during Power Mode parallel execution.

    Format (compact): Batch:2 Agents:4
    Format (full): Batch 2 | Code Explorer, Security Auditor (4 agents)

    Returns:
        Formatted batch status string, or empty if no active batch
    """
    state = load_power_mode_state()
    streaming = state.get("streaming", {})
    batch_num = state.get("batch_number", 0)
    agent_names = streaming.get("agents_streaming", [])

    if not batch_num or not agent_names:
        return ""

    if compact:
        return f"{Colors.CYAN}Batch:{batch_num} Agents:{len(agent_names)}{Colors.RESET}"

    # Full format with agent names
    agents_display = ", ".join(agent_names[:3])  # Show first 3
    if len(agent_names) > 3:
        agents_display += f" +{len(agent_names) - 3}"

    return f"{Colors.CYAN}Batch {batch_num} | {agents_display} ({len(agent_names)} agents){Colors.RESET}"


def widget_workflow(compact: bool = True) -> str:
    """
    Workflow progress widget.

    Format: feature-dev: Implementation (70%)
    Compact: impl 70%
    """
    workflow = load_workflow_state()
    if not workflow:
        return ""

    workflow_type = workflow.get("type", "")
    current_step = workflow.get("current_step", "")
    progress = workflow.get("progress", 0.0)
    percent = int(progress * 100)

    if not workflow_type and not current_step:
        return ""

    if compact:
        # Compact: step name abbreviation + percent
        step_abbrev = current_step[:4].lower() if current_step else ""
        return f"{Colors.BLUE}{step_abbrev} {percent}%{Colors.RESET}"

    # Full format
    parts = []
    if workflow_type:
        parts.append(workflow_type)
    if current_step:
        parts.append(f"{current_step}")
    parts.append(f"({percent}%)")

    return f"{Colors.BLUE}{': '.join(parts[:2])} {parts[-1]}{Colors.RESET}"


def widget_health(compact: bool = True) -> str:
    """
    Health status widget from morning routine.

    Format: Build:+ Tests:12/12 Lint:0
    Compact: +++ or +-+
    """
    health = load_health_state()
    if not health:
        return ""

    build_ok = health.get("build", {}).get("success", None)
    tests_pass = health.get("tests", {}).get("passed", 0)
    tests_total = health.get("tests", {}).get("total", 0)
    lint_errors = health.get("lint", {}).get("errors", 0)
    ts_errors = health.get("typescript", {}).get("errors", 0)

    # Check if we have any data
    if build_ok is None and tests_total == 0 and lint_errors == 0 and ts_errors == 0:
        return ""

    # Use ASCII-safe characters: + for pass, - for fail, ? for unknown
    if compact:
        # Compact: +++ or +-+ (build, tests, lint)
        build_icon = "+" if build_ok else ("-" if build_ok is False else "?")
        test_icon = "+" if tests_pass == tests_total and tests_total > 0 else ("-" if tests_pass < tests_total else "?")
        lint_icon = "+" if lint_errors == 0 else "-"

        build_color = Colors.GREEN if build_ok else Colors.RED
        test_color = Colors.GREEN if test_icon == "+" else Colors.RED
        lint_color = Colors.GREEN if lint_icon == "+" else Colors.RED

        return f"{build_color}{build_icon}{Colors.RESET}{test_color}{test_icon}{Colors.RESET}{lint_color}{lint_icon}{Colors.RESET}"

    # Full format
    parts = []
    if build_ok is not None:
        icon = "+" if build_ok else "-"
        color = Colors.GREEN if build_ok else Colors.RED
        parts.append(f"Build:{color}{icon}{Colors.RESET}")
    if tests_total > 0:
        color = Colors.GREEN if tests_pass == tests_total else Colors.RED
        parts.append(f"Tests:{color}{tests_pass}/{tests_total}{Colors.RESET}")
    if lint_errors >= 0:
        color = Colors.GREEN if lint_errors == 0 else Colors.RED
        parts.append(f"Lint:{color}{lint_errors}{Colors.RESET}")

    return " ".join(parts)


# Widget registry
WIDGETS: Dict[str, Callable[[bool], str]] = {
    "popkit": widget_popkit,
    "efficiency": widget_efficiency,
    "power_mode": widget_power_mode,
    "batch_status": widget_batch_status,
    "workflow": widget_workflow,
    "health": widget_health,
}


def get_widget_output(widget_name: str, compact: bool = True) -> str:
    """Get output for a single widget."""
    if widget_name in WIDGETS:
        return WIDGETS[widget_name](compact)
    return ""


def format_widget_status_line(config: Optional[WidgetConfig] = None) -> str:
    """
    Format status line using configured widgets.

    Args:
        config: Widget configuration (loads from file if None)

    Returns:
        Formatted status line string
    """
    if config is None:
        config = WidgetConfig.load()

    outputs = []
    for widget_name in config.widgets:
        output = get_widget_output(widget_name, config.compact_mode)
        if output:
            outputs.append(output)

    if not outputs:
        return ""

    # Add hints if configured
    if config.show_hints:
        state = load_power_mode_state()
        if state.get("active"):
            outputs.append(f"{Colors.DIM}(/stats | /power stop){Colors.RESET}")

    return config.separator.join(outputs)


# =============================================================================
# WIDGET CONFIGURATION MANAGEMENT (Issue #79)
# =============================================================================

def save_widget_config(config: WidgetConfig) -> bool:
    """
    Save widget configuration to file.

    Args:
        config: Widget configuration to save

    Returns:
        True if saved successfully
    """
    # Try project-local first, fall back to home
    local_config = Path.cwd() / ".claude" / "popkit" / "config.json"
    home_config = Path.home() / ".claude" / "popkit" / "config.json"

    config_file = local_config if local_config.parent.exists() else home_config

    try:
        # Load existing config or create new
        existing = {}
        if config_file.exists():
            with open(config_file) as f:
                existing = json.load(f)

        # Update statusline section
        existing["statusline"] = {
            "widgets": config.widgets,
            "compact_mode": config.compact_mode,
            "show_hints": config.show_hints,
            "separator": config.separator
        }

        # Save
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(existing, f, indent=2)

        return True

    except (IOError, json.JSONDecodeError):
        return False


def enable_widget(widget_name: str) -> bool:
    """
    Enable a widget.

    Args:
        widget_name: Name of widget to enable

    Returns:
        True if enabled successfully
    """
    if widget_name not in WIDGETS:
        print(f"Unknown widget: {widget_name}")
        print(f"Available widgets: {', '.join(WIDGETS.keys())}")
        return False

    config = WidgetConfig.load()
    if widget_name not in config.widgets:
        config.widgets.append(widget_name)
        if save_widget_config(config):
            print(f"Enabled widget: {widget_name}")
            return True
        else:
            print("Failed to save configuration")
            return False
    else:
        print(f"Widget already enabled: {widget_name}")
        return True


def disable_widget(widget_name: str) -> bool:
    """
    Disable a widget.

    Args:
        widget_name: Name of widget to disable

    Returns:
        True if disabled successfully
    """
    config = WidgetConfig.load()
    if widget_name in config.widgets:
        config.widgets.remove(widget_name)
        if save_widget_config(config):
            print(f"Disabled widget: {widget_name}")
            return True
        else:
            print("Failed to save configuration")
            return False
    else:
        print(f"Widget not enabled: {widget_name}")
        return True


def set_compact_mode(enabled: bool) -> bool:
    """
    Set compact mode.

    Args:
        enabled: True for compact mode

    Returns:
        True if set successfully
    """
    config = WidgetConfig.load()
    config.compact_mode = enabled
    if save_widget_config(config):
        mode_str = "compact" if enabled else "full"
        print(f"Set display mode: {mode_str}")
        return True
    else:
        print("Failed to save configuration")
        return False


def reset_widget_config() -> bool:
    """
    Reset widget configuration to defaults.

    Returns:
        True if reset successfully
    """
    default = WidgetConfig.default()
    if save_widget_config(default):
        print("Reset widget configuration to defaults")
        print(f"Widgets: {', '.join(default.widgets)}")
        print(f"Compact mode: {default.compact_mode}")
        return True
    else:
        print("Failed to save configuration")
        return False


def format_status_line(state: Dict[str, Any]) -> str:
    """Format the status line output.

    Args:
        state: Power Mode state dict

    Returns:
        Formatted status line string (empty if Power Mode inactive)
    """
    if not state.get("active"):
        return ""  # No status line when inactive

    # Build components
    components = []

    # [POP] indicator
    pop_indicator = f"{Colors.YELLOW}{Colors.BOLD}[POP]{Colors.RESET}"
    components.append(pop_indicator)

    # Streaming indicator (if active)
    streaming_indicator = format_streaming_indicator(state)
    if streaming_indicator:
        components.append(streaming_indicator)

    # Active skills indicator (Issue #188)
    skills_indicator = format_active_skills_indicator()
    if skills_indicator:
        components.append(skills_indicator)

    # Issue number (if present)
    issue_num = state.get("active_issue")
    if issue_num:
        issue_display = f"{Colors.MAGENTA}#{issue_num}{Colors.RESET}"
        components.append(issue_display)

    # Phase info
    current_phase = state.get("current_phase", "unknown")
    phase_index = state.get("phase_index", 0)
    total_phases = state.get("total_phases", 0)

    if total_phases > 0:
        phase_display = f"{Colors.BLUE}Phase: {current_phase} ({phase_index}/{total_phases}){Colors.RESET}"
    else:
        phase_display = f"{Colors.BLUE}Phase: {current_phase}{Colors.RESET}"
    components.append(phase_display)

    # Progress bar
    progress = state.get("progress", 0.0)
    bar = format_progress_bar(progress)
    percent = int(progress * 100)
    progress_display = f"{Colors.GREEN}{bar} {percent}%{Colors.RESET}"
    components.append(progress_display)

    # Efficiency indicator (Issue #78)
    metrics = load_efficiency_metrics()
    efficiency_indicator = format_efficiency_indicator(metrics)
    if efficiency_indicator:
        efficiency_display = f"{Colors.CYAN}{efficiency_indicator}{Colors.RESET}"
        components.append(efficiency_display)

    # Commands hint (dimmed)
    hint = f"{Colors.DIM}(/power status | stop){Colors.RESET}"
    components.append(hint)

    return " ".join(components)


def get_redis_commander_url() -> Optional[str]:
    """Get the Redis Commander URL if configured.

    Returns:
        URL string or None if not configured
    """
    # Default Redis Commander URL from docker-compose.yml
    return "http://localhost:18081"


def format_detailed_status(state: Dict[str, Any]) -> str:
    """Format detailed status for /popkit:power status command (Issue #66).

    Enhanced with dashboard URL, logs path, and more metrics.

    Args:
        state: Power Mode state dict

    Returns:
        Multi-line detailed status
    """
    if not state.get("active"):
        lines = [
            "",
            f"{Colors.BLUE}[i] POWER MODE INACTIVE{Colors.RESET}",
            "",
            "No active Power Mode session.",
            "",
            "To start Power Mode:",
            "  /popkit:dev work #N -p   Work on issue with Power Mode",
            "  /popkit:power start \"task\"   Start with custom objective",
            "",
            "Debug Tools:",
            f"  Redis Commander: {get_redis_commander_url()}",
            "  /popkit:power init debug   Start Redis Commander",
            ""
        ]
        return '\n'.join(lines)

    # Active session details
    issue_num = state.get("active_issue")
    session_id = state.get("session_id", "unknown")
    activated_at = state.get("activated_at", "")
    runtime = format_runtime(activated_at) if activated_at else "?"

    current_phase = state.get("current_phase", "unknown")
    phase_index = state.get("phase_index", 0)
    total_phases = state.get("total_phases", 0)
    progress = state.get("progress", 0.0)
    percent = int(progress * 100)

    phases_completed = state.get("phases_completed", [])
    source = state.get("source", "unknown")

    lines = [
        "",
        f"{Colors.GREEN}[+] POWER MODE ACTIVE{Colors.RESET}",
        "",
        f"Session: {session_id}",
    ]

    if issue_num:
        lines.append(f"Issue: #{issue_num}")

    lines.extend([
        f"Source: {source}",
        f"Started: {runtime} ago" if runtime else "",
        "",
        "Current State:",
        f"  Phase: {current_phase} ({phase_index}/{total_phases})",
        f"  Progress: {format_progress_bar(progress)} {percent}%",
        "",
        "Phases Completed:" if phases_completed else "",
    ])

    for phase in phases_completed:
        lines.append(f"  - {phase}")

    # Streaming info (Issue #23)
    streaming = state.get("streaming", {})
    active_streams = streaming.get("active_streams", 0)
    total_chunks = streaming.get("total_chunks", 0)

    if active_streams > 0 or total_chunks > 0:
        lines.extend([
            "",
            "Streaming:",
            f"  Active: {active_streams} stream{'s' if active_streams != 1 else ''}",
            f"  Total chunks: {total_chunks}",
        ])

        agents_streaming = streaming.get("agents_streaming", [])
        if agents_streaming:
            lines.append(f"  Agents: {', '.join(agents_streaming[:3])}")

        latest_tool = streaming.get("latest_tool")
        if latest_tool:
            lines.append(f"  Latest tool: {latest_tool}")

    # Efficiency metrics (Issue #78)
    metrics = load_efficiency_metrics()
    if metrics:
        # Calculate tokens saved
        duplicates = metrics.get("duplicates_skipped", 0)
        patterns = metrics.get("patterns_matched", 0)
        context_reuse = metrics.get("context_reuse_count", 0)
        bugs = metrics.get("bugs_detected", 0)
        stuck = metrics.get("stuck_patterns_detected", 0)
        insights_shared = metrics.get("insights_shared", 0)
        insights_received = metrics.get("insights_received", 0)
        insight_lengths = metrics.get("insight_lengths", [])
        tool_calls = metrics.get("tool_calls", 0)

        tokens_saved = (
            duplicates * 100 +
            patterns * 500 +
            context_reuse * 200 +
            bugs * 300 +
            stuck * 800 +
            int(sum(insight_lengths) * 0.25)
        )

        if tokens_saved > 0 or duplicates > 0 or patterns > 0:
            lines.extend([
                "",
                f"{Colors.CYAN}Efficiency (Issue #78):{Colors.RESET}",
                f"  Tokens saved: ~{format_tokens_saved(tokens_saved)}",
                f"  Duplicates skipped: {duplicates}",
                f"  Patterns matched: {patterns}",
                f"  Context reuse: {context_reuse}",
            ])

            if bugs > 0 or stuck > 0:
                lines.append(f"  Bugs detected: {bugs} | Stuck prevented: {stuck}")

            if insights_shared > 0 or insights_received > 0:
                lines.append(f"  Insights: {insights_shared} shared, {insights_received} received")

            lines.append(f"  Tool calls: {tool_calls}")

    # Debug Tools (Issue #66 - visibility)
    lines.extend([
        "",
        f"{Colors.YELLOW}Debug Tools:{Colors.RESET}",
        f"  Redis Commander: {get_redis_commander_url()}",
        f"  Session logs: ~/.claude/power-mode/logs/{session_id}.log",
    ])

    lines.extend([
        "",
        "Commands:",
        f"  {Colors.CYAN}/popkit:power stop{Colors.RESET}    Stop Power Mode",
        f"  {Colors.CYAN}/popkit:power init debug{Colors.RESET}  Open Redis Commander",
    ])

    if issue_num:
        lines.append(f"  {Colors.CYAN}/popkit:dev work #{issue_num}{Colors.RESET}   Continue current issue")

    lines.append("")

    return '\n'.join(lines)


def print_help():
    """Print help message."""
    print("""
PopKit Status Line Widget System

Usage:
  python statusline.py                    Widget-based status line (default)
  python statusline.py --legacy           Legacy Power Mode status line
  python statusline.py --widgets          List available widgets
  python statusline.py <widget>           Output single widget
  python statusline.py status             Detailed Power Mode status
  python statusline.py raw                Raw JSON state
  python statusline.py --help             This help message

Available Widgets:
  popkit       PopKit branding indicator
  efficiency   Token savings and pattern matches
  power_mode   Power Mode issue, phase, progress
  workflow     Current workflow progress
  health       Build/test/lint status

Configuration (.claude/popkit/config.json):
  {
    "statusline": {
      "widgets": ["popkit", "efficiency", "power_mode"],
      "compact_mode": true,
      "show_hints": true,
      "separator": " | "
    }
  }

Examples:
  python statusline.py efficiency         Show only efficiency widget
  python statusline.py --widgets          List available widgets
  python statusline.py --legacy           Use legacy Power Mode format
""")


def list_widgets():
    """List available widgets with descriptions."""
    print("\nAvailable Widgets:")
    print("-" * 40)

    descriptions = {
        "popkit": "PopKit branding indicator",
        "efficiency": "Token savings, patterns matched, duplicates skipped",
        "power_mode": "Power Mode status with issue, phase, agents",
        "batch_status": "Batch spawning status with agent count (Issue #253)",
        "workflow": "Current workflow progress from STATUS.json",
        "health": "Build, test, lint status from morning routine",
    }

    config = WidgetConfig.load()

    for name in WIDGETS.keys():
        # Use ASCII-safe characters for cross-platform compatibility
        enabled = "x" if name in config.widgets else " "
        desc = descriptions.get(name, "")

        # Get sample, but strip ANSI codes for text output
        sample = get_widget_output(name, compact=True)
        # Remove ANSI escape sequences for clean display
        sample_clean = re.sub(r'\033\[[0-9;]*m', '', sample) if sample else ""

        print(f"  [{enabled}] {name:12} - {desc}")
        if sample_clean:
            print(f"       Sample: {sample_clean}")

    print()
    print(f"Current config: {', '.join(config.widgets)}")
    print(f"Compact mode: {config.compact_mode}")
    print()


def main():
    """Main entry point.

    Reads session info from stdin (JSON from Claude Code) if available,
    then outputs formatted status line using the widget system.
    """
    # Try to read session info from stdin
    try:
        if not sys.stdin.isatty():
            session_info = json.loads(sys.stdin.read())
        else:
            session_info = {}
    except Exception:
        session_info = {}

    # Load state
    state = load_power_mode_state()

    # Check for command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--help" or arg == "-h":
            print_help()

        elif arg == "--widgets" or arg == "-w":
            # List available widgets
            list_widgets()

        elif arg == "status" or arg == "--detailed":
            # Output detailed status
            print(format_detailed_status(state))

        elif arg == "raw":
            # Output raw JSON state
            print(json.dumps(state, indent=2))

        elif arg == "stats" or arg == "--stats":
            # Output efficiency stats JSON (Issue #78)
            metrics = load_efficiency_metrics()
            if metrics:
                print(json.dumps(metrics, indent=2))
            else:
                print(json.dumps({"error": "No efficiency metrics found"}, indent=2))

        elif arg == "compact":
            # Output compact efficiency summary
            metrics = load_efficiency_metrics()
            indicator = format_efficiency_indicator(metrics)
            if indicator:
                print(indicator)
            else:
                print("No metrics yet")

        elif arg == "--legacy":
            # Legacy Power Mode status line (for backwards compatibility)
            status_line = format_status_line(state)
            if status_line:
                print(status_line)

        elif arg == "--full":
            # Full (non-compact) widget status line
            config = WidgetConfig.load()
            config.compact_mode = False
            status_line = format_widget_status_line(config)
            if status_line:
                print(status_line)

        elif arg in WIDGETS:
            # Single widget output
            compact = "--full" not in sys.argv
            output = get_widget_output(arg, compact=compact)
            if output:
                print(output)

        elif arg == "enable" and len(sys.argv) > 2:
            # Enable widget
            enable_widget(sys.argv[2])

        elif arg == "disable" and len(sys.argv) > 2:
            # Disable widget
            disable_widget(sys.argv[2])

        elif arg == "compact":
            # Toggle or set compact mode
            if len(sys.argv) > 2:
                value = sys.argv[2].lower()
                if value in ("on", "true", "1", "yes"):
                    set_compact_mode(True)
                elif value in ("off", "false", "0", "no"):
                    set_compact_mode(False)
                else:
                    # Show compact efficiency summary (legacy)
                    metrics = load_efficiency_metrics()
                    indicator = format_efficiency_indicator(metrics)
                    if indicator:
                        print(indicator)
                    else:
                        print("No metrics yet")
            else:
                # Toggle compact mode
                config = WidgetConfig.load()
                set_compact_mode(not config.compact_mode)

        elif arg == "reset":
            # Reset widget config
            reset_widget_config()

        else:
            # Unknown argument - show help
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information")

    else:
        # Default: widget-based status line
        status_line = format_widget_status_line()
        if status_line:
            print(status_line)


if __name__ == "__main__":
    main()
