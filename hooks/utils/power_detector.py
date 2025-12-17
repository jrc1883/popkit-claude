#!/usr/bin/env python3
"""
Power Mode Auto-Activation Detector (Issue #66)

Detects when Power Mode should be suggested or automatically activated
based on task complexity, issue labels, and context analysis.

Features:
- Epic issue detection
- Complex task detection (>3 files)
- Phase-aware activation suggestions
- Label-based recommendations

Usage:
    from power_detector import PowerDetector

    detector = PowerDetector()
    result = detector.analyze_issue(issue_data)
    if result.should_suggest:
        print(f"Suggest Power Mode: {result.reason}")

Part of Issue #66 - Power Mode v2
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# =============================================================================
# CONFIGURATION
# =============================================================================

# Labels that indicate Power Mode should be used
POWER_MODE_LABELS = [
    "epic",
    "complex",
    "multi-phase",
    "architecture",
    "refactor",
    "migration",
    "power-mode",
]

# Keywords in issue titles/bodies that suggest complexity
COMPLEXITY_KEYWORDS = [
    "comprehensive",
    "multi-agent",
    "orchestration",
    "parallel",
    "phase",
    "epic",
    "large-scale",
    "refactor",
    "migration",
    "redesign",
    "architecture",
    "system-wide",
]

# Minimum thresholds for auto-suggestion
MIN_FILES_FOR_SUGGESTION = 5
MIN_PHASES_FOR_SUGGESTION = 3
MIN_AGENTS_FOR_SUGGESTION = 2


# =============================================================================
# DETECTION RESULT
# =============================================================================

@dataclass
class PowerModeRecommendation:
    """Result of Power Mode detection analysis."""
    should_suggest: bool = False
    should_auto_enable: bool = False
    confidence: float = 0.0
    reason: str = ""
    detected_signals: List[str] = field(default_factory=list)
    suggested_agents: List[str] = field(default_factory=list)
    suggested_phases: List[str] = field(default_factory=list)
    estimated_files: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "should_suggest": self.should_suggest,
            "should_auto_enable": self.should_auto_enable,
            "confidence": self.confidence,
            "reason": self.reason,
            "detected_signals": self.detected_signals,
            "suggested_agents": self.suggested_agents,
            "suggested_phases": self.suggested_phases,
            "estimated_files": self.estimated_files,
        }


# =============================================================================
# POWER DETECTOR
# =============================================================================

class PowerDetector:
    """
    Detects when Power Mode should be suggested or auto-enabled.

    Analyzes:
    - Issue labels (epic, complex, etc.)
    - Issue title and body keywords
    - PopKit Guidance section content
    - Referenced file counts
    - Phase complexity
    """

    def __init__(self):
        self.power_labels = set(POWER_MODE_LABELS)
        self.complexity_keywords = COMPLEXITY_KEYWORDS

    def analyze_issue(self, issue_data: Dict) -> PowerModeRecommendation:
        """
        Analyze a GitHub issue to determine if Power Mode should be suggested.

        Args:
            issue_data: Issue data from `gh issue view --json`

        Returns:
            PowerModeRecommendation with detection results
        """
        result = PowerModeRecommendation()
        signals = []

        # Extract issue details
        title = issue_data.get("title", "").lower()
        body = issue_data.get("body", "") or ""
        labels = [l.get("name", "").lower() for l in issue_data.get("labels", [])]

        # Check for power-mode labels
        matching_labels = self.power_labels & set(labels)
        if matching_labels:
            signals.append(f"Labels: {', '.join(matching_labels)}")
            result.confidence += 0.3 * len(matching_labels)

            if "epic" in matching_labels or "power-mode" in matching_labels:
                result.should_auto_enable = True
                result.confidence = max(result.confidence, 0.8)

        # Check for complexity keywords in title
        title_keywords = [kw for kw in self.complexity_keywords if kw in title]
        if title_keywords:
            signals.append(f"Title keywords: {', '.join(title_keywords)}")
            result.confidence += 0.15 * len(title_keywords)

        # Check body for complexity keywords
        body_lower = body.lower()
        body_keywords = [kw for kw in self.complexity_keywords if kw in body_lower]
        if body_keywords:
            signals.append(f"Body keywords: {', '.join(set(body_keywords)[:5])}")
            result.confidence += 0.1 * min(len(set(body_keywords)), 3)

        # Parse PopKit Guidance if present
        guidance = self._parse_popkit_guidance(body)
        if guidance:
            if guidance.get("power_mode"):
                signals.append("PopKit Guidance: Power Mode requested")
                result.should_auto_enable = True
                result.confidence = max(result.confidence, 0.9)

            if guidance.get("phases"):
                result.suggested_phases = guidance["phases"]
                if len(guidance["phases"]) >= MIN_PHASES_FOR_SUGGESTION:
                    signals.append(f"PopKit Guidance: {len(guidance['phases'])} phases")
                    result.confidence += 0.2

            if guidance.get("agents"):
                result.suggested_agents = guidance["agents"]
                if len(guidance["agents"]) >= MIN_AGENTS_FOR_SUGGESTION:
                    signals.append(f"PopKit Guidance: {len(guidance['agents'])} agents")
                    result.confidence += 0.15

            if guidance.get("complexity", "").lower() in ("high", "very high"):
                signals.append("PopKit Guidance: High complexity")
                result.confidence += 0.2

        # Estimate file count from body
        file_count = self._estimate_file_count(body)
        result.estimated_files = file_count
        if file_count >= MIN_FILES_FOR_SUGGESTION:
            signals.append(f"Estimated files: {file_count}")
            result.confidence += 0.1 * min((file_count - 4) / 6, 0.3)

        # Determine final recommendation
        result.detected_signals = signals
        result.confidence = min(result.confidence, 1.0)  # Cap at 1.0

        if result.confidence >= 0.6:
            result.should_suggest = True
            reasons = []
            if matching_labels:
                reasons.append(f"issue labeled {', '.join(matching_labels)}")
            if len(result.suggested_phases) >= MIN_PHASES_FOR_SUGGESTION:
                reasons.append(f"{len(result.suggested_phases)} phases")
            if len(result.suggested_agents) >= MIN_AGENTS_FOR_SUGGESTION:
                reasons.append(f"{len(result.suggested_agents)} agents")
            if file_count >= MIN_FILES_FOR_SUGGESTION:
                reasons.append(f"~{file_count} files")
            if title_keywords:
                reasons.append(f"complexity keywords in title")

            result.reason = "Consider Power Mode: " + ", ".join(reasons[:3])

        if result.should_auto_enable:
            result.should_suggest = True
            result.reason = "Power Mode recommended: " + (
                "epic issue" if "epic" in labels else
                "power-mode label" if "power-mode" in labels else
                "PopKit Guidance requires parallel agents"
            )

        return result

    def analyze_task(self, task_description: str, context: Dict = None) -> PowerModeRecommendation:
        """
        Analyze a free-form task description for Power Mode suitability.

        Args:
            task_description: User's task description
            context: Optional context (recent files, git status, etc.)

        Returns:
            PowerModeRecommendation with detection results
        """
        result = PowerModeRecommendation()
        signals = []

        task_lower = task_description.lower()

        # Check for complexity keywords
        keywords = [kw for kw in self.complexity_keywords if kw in task_lower]
        if keywords:
            signals.append(f"Task keywords: {', '.join(keywords[:3])}")
            result.confidence += 0.15 * len(keywords)

        # Check for explicit multi-phase indicators
        phase_indicators = [
            r"\d+\s*(phases?|steps?|stages?)",
            r"(first|then|next|finally|after that)",
            r"(explore|design|implement|test|review)",
        ]
        for pattern in phase_indicators:
            if re.search(pattern, task_lower):
                signals.append(f"Multi-phase indicator: {pattern}")
                result.confidence += 0.1

        # Check for file-touching indicators
        file_patterns = [
            r"(multiple|several|many)\s*(files?|components?|modules?)",
            r"(across|throughout)\s*(the\s+)?(codebase|project)",
            r"refactor(ing)?\s+\w+",
        ]
        for pattern in file_patterns:
            if re.search(pattern, task_lower):
                signals.append(f"Multi-file indicator")
                result.confidence += 0.15
                break

        # Check context if provided
        if context:
            recent_files = context.get("recent_files", [])
            if len(recent_files) >= MIN_FILES_FOR_SUGGESTION:
                signals.append(f"Context: {len(recent_files)} recent files")
                result.confidence += 0.2

            uncommitted_changes = context.get("uncommitted_changes", 0)
            if uncommitted_changes >= 10:
                signals.append(f"Context: {uncommitted_changes} uncommitted changes")
                result.confidence += 0.1

        result.detected_signals = signals
        result.confidence = min(result.confidence, 1.0)

        if result.confidence >= 0.5:
            result.should_suggest = True
            result.reason = "Task appears complex: " + ", ".join(signals[:2])

        # Suggest default phases if none detected
        if result.should_suggest and not result.suggested_phases:
            result.suggested_phases = ["explore", "implement", "test", "review"]

        return result

    def _parse_popkit_guidance(self, body: str) -> Optional[Dict]:
        """
        Parse PopKit Guidance section from issue body.

        Returns:
            Dict with parsed guidance or None
        """
        if not body:
            return None

        # Find PopKit Guidance section
        guidance_pattern = r"##\s*PopKit\s+Guidance(.*?)(?=##|\Z)"
        match = re.search(guidance_pattern, body, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        guidance_text = match.group(1)
        result = {}

        # Check for Power Mode flag
        if re.search(r"\[x\]\s*\*\*Power\s+Mode\*\*", guidance_text, re.IGNORECASE):
            result["power_mode"] = True

        # Extract phases
        phases_match = re.search(
            r"(?:phases?|development\s+phases?)[\s:]+\[?([\w\s,→-]+)\]?",
            guidance_text,
            re.IGNORECASE
        )
        if phases_match:
            phases_text = phases_match.group(1)
            # Parse various formats
            if "→" in phases_text:
                phases = [p.strip().lower() for p in phases_text.split("→")]
            elif "->" in phases_text:
                phases = [p.strip().lower() for p in phases_text.split("->")]
            else:
                phases = [p.strip().lower() for p in re.split(r"[,\n]", phases_text)]
            result["phases"] = [p for p in phases if p]

        # Extract agents
        agents_match = re.search(
            r"(?:agents?|suggested\s+agents?)[\s:]+([^\n]+)",
            guidance_text,
            re.IGNORECASE
        )
        if agents_match:
            agents_text = agents_match.group(1)
            agents = [a.strip().strip("`") for a in re.split(r"[,|]", agents_text)]
            result["agents"] = [a for a in agents if a and not a.startswith("[")]

        # Extract complexity
        complexity_match = re.search(
            r"complexity[\s:]+\[?x?\]?\s*(\w+)",
            guidance_text,
            re.IGNORECASE
        )
        if complexity_match:
            result["complexity"] = complexity_match.group(1)

        return result if result else None

    def _estimate_file_count(self, body: str) -> int:
        """
        Estimate number of files that will be touched based on issue body.

        Returns:
            Estimated file count
        """
        if not body:
            return 0

        count = 0

        # Count file paths mentioned
        file_pattern = r"`([^`]+\.(ts|tsx|js|jsx|py|md|json|yaml|yml))`"
        files = re.findall(file_pattern, body)
        count += len(files)

        # Count "Files to Modify" table entries
        table_pattern = r"\|\s*`?[\w./]+\.(ts|tsx|js|jsx|py|md)`?\s*\|"
        table_files = re.findall(table_pattern, body)
        count += len(table_files)

        # Look for explicit count indicators
        explicit_pattern = r"(\d+)\s*(files?|components?|modules?)"
        explicit_matches = re.findall(explicit_pattern, body.lower())
        for match in explicit_matches:
            count = max(count, int(match[0]))

        return count

    def should_use_power_mode(
        self,
        issue_data: Optional[Dict] = None,
        task_description: Optional[str] = None,
        context: Optional[Dict] = None,
        flags: Optional[Dict] = None
    ) -> PowerModeRecommendation:
        """
        Determine if Power Mode should be used based on all available signals.

        Priority:
        1. Explicit flags (-p/--power or --solo) override everything
        2. Issue-based detection if issue provided
        3. Task-based detection if task description provided
        4. Default to sequential mode

        Args:
            issue_data: GitHub issue data (optional)
            task_description: User's task description (optional)
            context: Additional context (optional)
            flags: Command flags like {"power": True} (optional)

        Returns:
            PowerModeRecommendation with final decision
        """
        flags = flags or {}

        # 1. Check explicit flags first
        if flags.get("power"):
            return PowerModeRecommendation(
                should_suggest=True,
                should_auto_enable=True,
                confidence=1.0,
                reason="Power Mode enabled via -p/--power flag",
                detected_signals=["Explicit flag: --power"]
            )

        if flags.get("solo"):
            return PowerModeRecommendation(
                should_suggest=False,
                should_auto_enable=False,
                confidence=1.0,
                reason="Sequential mode via --solo flag",
                detected_signals=["Explicit flag: --solo"]
            )

        # 2. Analyze issue if provided
        if issue_data:
            return self.analyze_issue(issue_data)

        # 3. Analyze task description if provided
        if task_description:
            return self.analyze_task(task_description, context)

        # 4. Default: no recommendation
        return PowerModeRecommendation(
            should_suggest=False,
            confidence=0.0,
            reason="No signals detected, defaulting to sequential mode"
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def should_suggest_power_mode(issue_data: Dict) -> bool:
    """Quick check if Power Mode should be suggested for an issue."""
    detector = PowerDetector()
    result = detector.analyze_issue(issue_data)
    return result.should_suggest


def get_power_mode_recommendation(
    issue_data: Optional[Dict] = None,
    task: Optional[str] = None,
    flags: Optional[Dict] = None
) -> PowerModeRecommendation:
    """Get Power Mode recommendation for any context."""
    detector = PowerDetector()
    return detector.should_use_power_mode(
        issue_data=issue_data,
        task_description=task,
        flags=flags
    )


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    import subprocess
    import sys

    parser = argparse.ArgumentParser(description="Power Mode Detection")
    parser.add_argument("--issue", "-i", type=int, help="GitHub issue number")
    parser.add_argument("--task", "-t", help="Task description")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")

    args = parser.parse_args()

    detector = PowerDetector()

    if args.issue:
        # Fetch issue data
        try:
            result = subprocess.run(
                ["gh", "issue", "view", str(args.issue), "--json",
                 "number,title,body,labels,state"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print(f"Error fetching issue: {result.stderr}", file=sys.stderr)
                sys.exit(1)

            issue_data = json.loads(result.stdout)
            recommendation = detector.analyze_issue(issue_data)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.task:
        recommendation = detector.analyze_task(args.task)

    else:
        print("Provide --issue or --task")
        sys.exit(1)

    if args.json:
        print(json.dumps(recommendation.to_dict(), indent=2))
    else:
        print(f"\nPower Mode Recommendation:")
        print(f"  Should suggest: {recommendation.should_suggest}")
        print(f"  Should auto-enable: {recommendation.should_auto_enable}")
        print(f"  Confidence: {recommendation.confidence:.1%}")
        print(f"  Reason: {recommendation.reason}")

        if recommendation.detected_signals:
            print(f"\nDetected signals:")
            for signal in recommendation.detected_signals:
                print(f"  - {signal}")

        if recommendation.suggested_phases:
            print(f"\nSuggested phases: {' → '.join(recommendation.suggested_phases)}")

        if recommendation.suggested_agents:
            print(f"Suggested agents: {', '.join(recommendation.suggested_agents)}")
