#!/usr/bin/env python3
"""
Bug Detector Utility

Part of Issue #72 (Automatic Bug Detection & Pattern Matching)

Detects when agents encounter errors or get stuck, automatically logs
context, and matches against known solutions from collective learning.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

# Error patterns in tool outputs
ERROR_PATTERNS = [
    # JavaScript/TypeScript errors
    (r"TypeError:", "TypeError"),
    (r"SyntaxError:", "SyntaxError"),
    (r"ReferenceError:", "ReferenceError"),
    (r"RangeError:", "RangeError"),
    # Python errors
    (r"Traceback \(most recent call last\):", "Python Exception"),
    (r"AttributeError:", "AttributeError"),
    (r"KeyError:", "KeyError"),
    (r"ValueError:", "ValueError"),
    (r"ImportError:", "ImportError"),
    (r"ModuleNotFoundError:", "ModuleNotFoundError"),
    # Generic errors
    (r"\berror\b.*:", "Error"),
    (r"\bError\b:", "Error"),
    (r"ERROR:", "Error"),
    (r"\bfailed\b", "Failed"),
    (r"\bFailed\b", "Failed"),
    (r"FAILED", "Failed"),
    (r"\bfailure\b", "Failure"),
    # HTTP/Network errors
    (r"\b401\b.*unauthorized", "Unauthorized"),
    (r"\b403\b.*forbidden", "Forbidden"),
    (r"\b404\b.*not found", "NotFound"),
    (r"\b500\b", "ServerError"),
    (r"ECONNREFUSED", "ConnectionRefused"),
    (r"ETIMEDOUT", "Timeout"),
    (r"ENOENT", "FileNotFound"),
    # Permission errors
    (r"permission denied", "PermissionDenied"),
    (r"access denied", "AccessDenied"),
]

# Behavioral patterns (stuck signals)
STUCK_BEHAVIOR = {
    "same_file_edits": 3,      # Same file edited N+ times
    "same_command_runs": 3,    # Same command run N+ times
    "no_progress_tools": 10,   # N tool calls with no progress
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DetectedBug:
    """Represents a detected bug."""
    detection_type: str           # "error" or "stuck"
    error_type: Optional[str]     # Specific error type
    error_message: Optional[str]  # Error message
    stuck_pattern: Optional[str]  # Stuck pattern description
    confidence: float             # 0.0 to 1.0
    context: Dict[str, Any]       # Additional context
    tool_name: Optional[str]      # Tool that triggered detection
    suggestions: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    """Result of bug detection."""
    detected: bool
    bugs: List[DetectedBug]
    matched_patterns: List[Dict[str, Any]]  # From collective
    action: str  # "continue", "inject_hint", "pause", "report"


# =============================================================================
# BUG DETECTOR
# =============================================================================

class BugDetector:
    """
    Detects bugs from tool outputs and behavioral patterns.

    Usage:
        detector = BugDetector()
        result = detector.detect(tool_name, tool_input, tool_output, history)
    """

    def __init__(self, pattern_client: Optional[Any] = None):
        """
        Initialize detector.

        Args:
            pattern_client: Optional PatternClient for collective search
        """
        self.pattern_client = pattern_client
        self.history: List[Dict[str, Any]] = []

    def detect(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> DetectionResult:
        """
        Detect bugs from tool call.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            tool_output: Tool output/result
            history: Previous tool calls for pattern detection

        Returns:
            DetectionResult with detected bugs and recommendations
        """
        bugs: List[DetectedBug] = []
        matched_patterns: List[Dict[str, Any]] = []

        # Update history
        if history is not None:
            self.history = history
        self.history.append({
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output[:500] if tool_output else ""
        })

        # 1. Check for error patterns in output
        error_bugs = self._detect_errors(tool_name, tool_output)
        bugs.extend(error_bugs)

        # 2. Check for stuck behavior
        stuck_bugs = self._detect_stuck_behavior(tool_name, tool_input)
        bugs.extend(stuck_bugs)

        # 3. Search collective for matching patterns
        if bugs and self.pattern_client:
            matched_patterns = self._search_patterns(bugs)

        # 4. Determine action
        action = self._determine_action(bugs, matched_patterns)

        # 5. Generate suggestions
        for bug in bugs:
            bug.suggestions = self._generate_suggestions(bug)

        return DetectionResult(
            detected=len(bugs) > 0,
            bugs=bugs,
            matched_patterns=matched_patterns,
            action=action
        )

    def _detect_errors(
        self,
        tool_name: str,
        tool_output: str
    ) -> List[DetectedBug]:
        """Detect errors in tool output."""
        bugs = []

        if not tool_output:
            return bugs

        for pattern, error_type in ERROR_PATTERNS:
            match = re.search(pattern, tool_output, re.IGNORECASE)
            if match:
                # Extract error message (line containing match)
                lines = tool_output.split("\n")
                error_line = ""
                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        error_line = line.strip()[:200]
                        break

                # Determine confidence based on error type
                confidence = self._calculate_error_confidence(error_type, tool_name)

                bugs.append(DetectedBug(
                    detection_type="error",
                    error_type=error_type,
                    error_message=error_line,
                    stuck_pattern=None,
                    confidence=confidence,
                    context={"match": match.group()},
                    tool_name=tool_name
                ))
                break  # Only detect one error per output

        return bugs

    def _detect_stuck_behavior(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> List[DetectedBug]:
        """Detect stuck behavioral patterns."""
        bugs = []

        if len(self.history) < 3:
            return bugs

        recent = self.history[-10:]

        # Same file edited multiple times
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            edit_count = sum(
                1 for h in recent
                if h.get("tool_name") == "Edit" and
                h.get("tool_input", {}).get("file_path") == file_path
            )
            if edit_count >= STUCK_BEHAVIOR["same_file_edits"]:
                bugs.append(DetectedBug(
                    detection_type="stuck",
                    error_type=None,
                    error_message=None,
                    stuck_pattern=f"Same file edited {edit_count} times: {Path(file_path).name}",
                    confidence=min(0.5 + (edit_count - 3) * 0.1, 0.9),
                    context={"file_path": file_path, "edit_count": edit_count},
                    tool_name=tool_name
                ))

        # Same command run multiple times
        if tool_name == "Bash":
            command = tool_input.get("command", "")[:50]
            command_count = sum(
                1 for h in recent
                if h.get("tool_name") == "Bash" and
                h.get("tool_input", {}).get("command", "")[:50] == command
            )
            if command_count >= STUCK_BEHAVIOR["same_command_runs"]:
                bugs.append(DetectedBug(
                    detection_type="stuck",
                    error_type=None,
                    error_message=None,
                    stuck_pattern=f"Same command run {command_count} times: {command}",
                    confidence=min(0.4 + (command_count - 3) * 0.1, 0.8),
                    context={"command": command, "count": command_count},
                    tool_name=tool_name
                ))

        return bugs

    def _calculate_error_confidence(self, error_type: str, tool_name: str) -> float:
        """Calculate confidence based on error type and context."""
        # High confidence errors
        high_confidence = ["TypeError", "SyntaxError", "ReferenceError", "Python Exception"]
        if error_type in high_confidence:
            return 0.9

        # Medium confidence
        medium_confidence = ["AttributeError", "KeyError", "ValueError", "ImportError"]
        if error_type in medium_confidence:
            return 0.8

        # Lower confidence for generic errors
        if error_type in ["Error", "Failed", "Failure"]:
            # Higher if from build/test command
            if tool_name == "Bash":
                return 0.7
            return 0.5

        return 0.6

    def _search_patterns(self, bugs: List[DetectedBug]) -> List[Dict[str, Any]]:
        """Search collective for matching patterns."""
        if not self.pattern_client:
            return []

        try:
            # Build query from detected bugs
            query_parts = []
            for bug in bugs:
                if bug.error_message:
                    query_parts.append(bug.error_message)
                if bug.stuck_pattern:
                    query_parts.append(bug.stuck_pattern)

            if not query_parts:
                return []

            query = " ".join(query_parts[:2])

            # Search patterns
            patterns = self.pattern_client.search_patterns(
                query=query,
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

    def _determine_action(
        self,
        bugs: List[DetectedBug],
        matched_patterns: List[Dict[str, Any]]
    ) -> str:
        """Determine recommended action based on detection."""
        if not bugs:
            return "continue"

        # High confidence error with pattern match
        high_conf_bugs = [b for b in bugs if b.confidence >= 0.8]
        if high_conf_bugs and matched_patterns:
            best_pattern = max(matched_patterns, key=lambda p: p.get("similarity", 0))
            if best_pattern.get("similarity", 0) >= 0.8:
                return "inject_hint"

        # Multiple stuck patterns
        stuck_bugs = [b for b in bugs if b.detection_type == "stuck"]
        if len(stuck_bugs) >= 2:
            return "pause"

        # Single error with medium+ confidence
        if high_conf_bugs:
            return "report"

        return "continue"

    def _generate_suggestions(self, bug: DetectedBug) -> List[str]:
        """Generate suggestions for a detected bug."""
        suggestions = []

        if bug.detection_type == "error":
            error_type = bug.error_type or "Error"

            if error_type == "TypeError":
                suggestions.extend([
                    "Check for null/undefined values before accessing properties",
                    "Verify the data type matches expected type",
                ])
            elif error_type == "SyntaxError":
                suggestions.extend([
                    "Review recent code changes for syntax issues",
                    "Check for missing brackets, quotes, or semicolons",
                ])
            elif error_type in ["ReferenceError", "NameError"]:
                suggestions.extend([
                    "Check if the variable/function is defined before use",
                    "Verify import statements are correct",
                ])
            elif error_type in ["ConnectionRefused", "Timeout"]:
                suggestions.extend([
                    "Check if the service is running",
                    "Verify network connectivity and firewall rules",
                ])
            elif error_type == "FileNotFound":
                suggestions.extend([
                    "Verify the file path is correct",
                    "Check if the file exists",
                ])
            else:
                suggestions.append("Review the error message for specific details")

        elif bug.detection_type == "stuck":
            if "Same file edited" in (bug.stuck_pattern or ""):
                suggestions.extend([
                    "Consider stepping back and reviewing the approach",
                    "Check if there's a simpler solution",
                    "The same file being edited multiple times may indicate confusion",
                ])
            elif "Same command run" in (bug.stuck_pattern or ""):
                suggestions.extend([
                    "Check if the command is producing the expected output",
                    "Consider a different approach if the command keeps failing",
                ])

        return suggestions


# =============================================================================
# FORMAT FUNCTIONS
# =============================================================================

def format_detection_result(result: DetectionResult) -> str:
    """Format detection result for display."""
    if not result.detected:
        return ""

    lines = [
        "Bug Detection Alert",
        "=" * 40
    ]

    for bug in result.bugs:
        if bug.detection_type == "error":
            lines.append(f"[ERROR] {bug.error_type}: {bug.error_message[:80]}...")
        else:
            lines.append(f"[STUCK] {bug.stuck_pattern}")
        lines.append(f"  Confidence: {bug.confidence:.0%}")

        if bug.suggestions:
            lines.append("  Suggestions:")
            for s in bug.suggestions[:2]:
                lines.append(f"    - {s}")

    if result.matched_patterns:
        lines.append("")
        lines.append("Matching Patterns from Collective:")
        for p in result.matched_patterns[:2]:
            lines.append(f"  [{p.get('similarity', 0):.0%}] {p.get('trigger', '')[:50]}...")
            lines.append(f"    Solution: {p.get('solution', '')[:80]}...")

    lines.append("")
    lines.append(f"Recommended Action: {result.action}")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing bug detector."""
    print("Bug Detector Test")
    print("=" * 50)

    detector = BugDetector()

    # Test error detection
    print("\n[TEST] Error detection...")
    result = detector.detect(
        tool_name="Bash",
        tool_input={"command": "npm run build"},
        tool_output="TypeError: Cannot read property 'token' of undefined\n  at handleAuth (auth.ts:45)"
    )
    print(f"  Detected: {result.detected}")
    if result.bugs:
        print(f"  Error: {result.bugs[0].error_type}")
        print(f"  Confidence: {result.bugs[0].confidence:.0%}")

    # Test stuck detection
    print("\n[TEST] Stuck behavior detection...")
    # Simulate multiple edits to same file
    for i in range(4):
        result = detector.detect(
            tool_name="Edit",
            tool_input={"file_path": "/src/auth/oauth.ts"},
            tool_output="File edited"
        )

    print(f"  Detected: {result.detected}")
    if result.bugs:
        stuck_bugs = [b for b in result.bugs if b.detection_type == "stuck"]
        if stuck_bugs:
            print(f"  Pattern: {stuck_bugs[0].stuck_pattern}")
            print(f"  Confidence: {stuck_bugs[0].confidence:.0%}")

    print("\n" + "=" * 50)
    print("[OK] Bug detector test completed!")


if __name__ == "__main__":
    main()
