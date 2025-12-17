#!/usr/bin/env python3
"""
PopKit Assessment Runner

Multi-perspective self-assessment framework that runs specialized
"assessor agents" to review PopKit from different expert perspectives.

Part of Issue #107 (Multi-Perspective Self-Assessment Framework)
Parent: Epic #104 (PopKit Quality Assurance & Power Mode Value Proposition)
"""

import argparse
import json
import sys
import io
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(Enum):
    """Check status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class Finding:
    """A single assessment finding."""
    check: str
    status: Status
    severity: Severity
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "recommendation": self.recommendation
        }


@dataclass
class AssessmentResult:
    """Result from a single assessor."""
    assessor: str
    score: float
    findings: List[Finding] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    duration_ms: float = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == Status.PASS)

    def to_dict(self) -> dict:
        return {
            "assessor": self.assessor,
            "score": self.score,
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "warnings": self.warning_count,
                "passed": self.pass_count
            },
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms
        }


class BaseAssessor:
    """Base class for all assessors."""

    name: str = "base"
    description: str = "Base assessor"

    def __init__(self, plugin_path: Path):
        self.plugin_path = plugin_path
        self.findings: List[Finding] = []

    def add_finding(
        self,
        check: str,
        status: Status,
        severity: Severity,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        recommendation: Optional[str] = None
    ):
        """Add a finding to the results."""
        self.findings.append(Finding(
            check=check,
            status=status,
            severity=severity,
            message=message,
            file=file,
            line=line,
            recommendation=recommendation
        ))

    def pass_check(self, check: str, message: str = "Passed"):
        """Record a passing check."""
        self.add_finding(check, Status.PASS, Severity.INFO, message)

    def fail_check(
        self,
        check: str,
        message: str,
        severity: Severity = Severity.MEDIUM,
        file: Optional[str] = None,
        recommendation: Optional[str] = None
    ):
        """Record a failing check."""
        self.add_finding(check, Status.FAIL, severity, message, file, recommendation=recommendation)

    def warn_check(self, check: str, message: str, file: Optional[str] = None):
        """Record a warning."""
        self.add_finding(check, Status.WARN, Severity.LOW, message, file)

    def run(self) -> AssessmentResult:
        """Run the assessment. Override in subclasses."""
        raise NotImplementedError

    def calculate_score(self) -> float:
        """Calculate overall score based on findings."""
        if not self.findings:
            return 100.0

        total_checks = len(self.findings)
        deductions = 0

        for finding in self.findings:
            if finding.status == Status.FAIL:
                if finding.severity == Severity.CRITICAL:
                    deductions += 20
                elif finding.severity == Severity.HIGH:
                    deductions += 10
                elif finding.severity == Severity.MEDIUM:
                    deductions += 5
                elif finding.severity == Severity.LOW:
                    deductions += 2
            elif finding.status == Status.WARN:
                deductions += 1

        score = max(0, 100 - deductions)
        return round(score, 1)


class PluginStructureAssessor(BaseAssessor):
    """Validates plugin structure and core files."""

    name = "plugin-structure"
    description = "Validates plugin.json, hooks.json, and core structure"

    def run(self) -> AssessmentResult:
        import time
        start = time.time()

        # Check plugin.json
        self._check_plugin_json()

        # Check hooks.json
        self._check_hooks_json()

        # Check config.json
        self._check_config_json()

        # Check directory structure
        self._check_directory_structure()

        duration = (time.time() - start) * 1000
        score = self.calculate_score()

        return AssessmentResult(
            assessor=self.name,
            score=score,
            findings=self.findings,
            completed_at=datetime.now().isoformat(),
            duration_ms=duration
        )

    def _check_plugin_json(self):
        plugin_file = self.plugin_path / ".claude-plugin" / "plugin.json"
        if not plugin_file.exists():
            self.fail_check(
                "plugin.json exists",
                "plugin.json not found",
                Severity.CRITICAL,
                str(plugin_file)
            )
            return

        try:
            with open(plugin_file) as f:
                data = json.load(f)

            # Check required fields
            required = ["name", "version", "description"]
            for field in required:
                if field in data:
                    self.pass_check(f"plugin.json.{field}", f"Field '{field}' present")
                else:
                    self.fail_check(
                        f"plugin.json.{field}",
                        f"Missing required field: {field}",
                        Severity.HIGH
                    )
        except json.JSONDecodeError as e:
            self.fail_check(
                "plugin.json valid",
                f"Invalid JSON: {e}",
                Severity.CRITICAL
            )

    def _check_hooks_json(self):
        hooks_file = self.plugin_path / "hooks" / "hooks.json"
        if not hooks_file.exists():
            self.fail_check(
                "hooks.json exists",
                "hooks.json not found",
                Severity.HIGH,
                str(hooks_file)
            )
            return

        try:
            with open(hooks_file) as f:
                data = json.load(f)

            if "hooks" in data:
                self.pass_check("hooks.json.hooks", "Hooks array present")

                # Validate each hook
                valid_events = [
                    "PreToolUse", "PostToolUse", "UserPromptSubmit",
                    "SessionStart", "Stop", "SubagentStop", "Notification"
                ]

                for hook in data["hooks"]:
                    hook_name = hook.get("name", "unknown")
                    event = hook.get("event")

                    if event in valid_events:
                        self.pass_check(f"hook.{hook_name}.event", f"Valid event: {event}")
                    else:
                        self.fail_check(
                            f"hook.{hook_name}.event",
                            f"Invalid event type: {event}",
                            Severity.MEDIUM
                        )
            else:
                self.fail_check(
                    "hooks.json.hooks",
                    "Missing 'hooks' array",
                    Severity.HIGH
                )
        except json.JSONDecodeError as e:
            self.fail_check(
                "hooks.json valid",
                f"Invalid JSON: {e}",
                Severity.CRITICAL
            )

    def _check_config_json(self):
        config_file = self.plugin_path / "agents" / "config.json"
        if not config_file.exists():
            self.fail_check(
                "config.json exists",
                "agents/config.json not found",
                Severity.HIGH,
                str(config_file)
            )
            return

        try:
            with open(config_file) as f:
                data = json.load(f)

            required_sections = ["tiers", "routing", "confidence"]
            for section in required_sections:
                if section in data:
                    self.pass_check(f"config.json.{section}", f"Section '{section}' present")
                else:
                    self.fail_check(
                        f"config.json.{section}",
                        f"Missing section: {section}",
                        Severity.MEDIUM
                    )
        except json.JSONDecodeError as e:
            self.fail_check(
                "config.json valid",
                f"Invalid JSON: {e}",
                Severity.CRITICAL
            )

    def _check_directory_structure(self):
        required_dirs = ["agents", "skills", "commands", "hooks"]
        for dir_name in required_dirs:
            dir_path = self.plugin_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                self.pass_check(f"directory.{dir_name}", f"Directory '{dir_name}/' exists")
            else:
                self.fail_check(
                    f"directory.{dir_name}",
                    f"Missing directory: {dir_name}/",
                    Severity.CRITICAL
                )


class HookProtocolAssessor(BaseAssessor):
    """Validates hook JSON stdin/stdout protocol."""

    name = "hook-protocol"
    description = "Validates hook JSON stdin/stdout implementation"

    def run(self) -> AssessmentResult:
        import time
        start = time.time()

        hooks_dir = self.plugin_path / "hooks"
        if not hooks_dir.exists():
            self.fail_check(
                "hooks directory",
                "hooks/ directory not found",
                Severity.CRITICAL
            )
            return AssessmentResult(
                assessor=self.name,
                score=0,
                findings=self.findings,
                completed_at=datetime.now().isoformat(),
                duration_ms=(time.time() - start) * 1000
            )

        # Check each Python hook file
        for hook_file in hooks_dir.glob("*.py"):
            self._check_hook_file(hook_file)

        duration = (time.time() - start) * 1000
        score = self.calculate_score()

        return AssessmentResult(
            assessor=self.name,
            score=score,
            findings=self.findings,
            completed_at=datetime.now().isoformat(),
            duration_ms=duration
        )

    def _check_hook_file(self, hook_file: Path):
        hook_name = hook_file.stem

        try:
            content = hook_file.read_text(encoding='utf-8')

            # Check for stdin reading
            if "sys.stdin" in content or "stdin.read" in content:
                self.pass_check(f"{hook_name}.stdin", "Reads from stdin")
            else:
                self.warn_check(
                    f"{hook_name}.stdin",
                    "No stdin reading detected",
                    str(hook_file)
                )

            # Check for JSON parsing
            if "json.loads" in content or "json.load" in content:
                self.pass_check(f"{hook_name}.json_parse", "Uses JSON parsing")
            else:
                self.warn_check(
                    f"{hook_name}.json_parse",
                    "No JSON parsing detected",
                    str(hook_file)
                )

            # Check for JSON output
            if "json.dumps" in content or "print(json" in content:
                self.pass_check(f"{hook_name}.json_output", "Outputs JSON")
            else:
                self.warn_check(
                    f"{hook_name}.json_output",
                    "No JSON output detected",
                    str(hook_file)
                )

            # Check for error handling
            if "try:" in content and "except" in content:
                self.pass_check(f"{hook_name}.error_handling", "Has error handling")
            else:
                self.fail_check(
                    f"{hook_name}.error_handling",
                    "Missing try/except error handling",
                    Severity.MEDIUM,
                    str(hook_file),
                    recommendation="Add try/except blocks to handle errors gracefully"
                )

        except Exception as e:
            self.fail_check(
                f"{hook_name}.readable",
                f"Could not read file: {e}",
                Severity.HIGH
            )


class DocumentationAssessor(BaseAssessor):
    """Validates documentation completeness."""

    name = "documentation"
    description = "Validates SKILL.md and AGENT.md completeness"

    def run(self) -> AssessmentResult:
        import time
        start = time.time()

        # Check skills documentation
        self._check_skills_docs()

        # Check agents documentation
        self._check_agents_docs()

        # Check commands documentation
        self._check_commands_docs()

        duration = (time.time() - start) * 1000
        score = self.calculate_score()

        return AssessmentResult(
            assessor=self.name,
            score=score,
            findings=self.findings,
            completed_at=datetime.now().isoformat(),
            duration_ms=duration
        )

    def _check_skills_docs(self):
        skills_dir = self.plugin_path / "skills"
        if not skills_dir.exists():
            self.fail_check("skills directory", "skills/ not found", Severity.HIGH)
            return

        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                self._check_skill_file(skill_md, skill_dir.name)
            else:
                self.fail_check(
                    f"skill.{skill_dir.name}.exists",
                    f"Missing SKILL.md",
                    Severity.MEDIUM,
                    str(skill_dir)
                )

    def _check_skill_file(self, skill_file: Path, skill_name: str):
        content = skill_file.read_text(encoding='utf-8')

        # Check for frontmatter
        if content.startswith("---"):
            self.pass_check(f"skill.{skill_name}.frontmatter", "Has frontmatter")

            # Check for description in frontmatter
            if "description:" in content[:500]:
                self.pass_check(f"skill.{skill_name}.description", "Has description")
            else:
                self.fail_check(
                    f"skill.{skill_name}.description",
                    "Missing description in frontmatter",
                    Severity.MEDIUM
                )
        else:
            self.fail_check(
                f"skill.{skill_name}.frontmatter",
                "Missing YAML frontmatter",
                Severity.MEDIUM,
                str(skill_file)
            )

    def _check_agents_docs(self):
        agents_dir = self.plugin_path / "agents"
        if not agents_dir.exists():
            self.fail_check("agents directory", "agents/ not found", Severity.HIGH)
            return

        # Check tier directories
        for tier_dir in agents_dir.iterdir():
            if tier_dir.is_dir() and tier_dir.name.startswith("tier-"):
                for agent_dir in tier_dir.iterdir():
                    if agent_dir.is_dir():
                        agent_md = agent_dir / "AGENT.md"
                        if agent_md.exists():
                            self.pass_check(f"agent.{agent_dir.name}.exists", "Has AGENT.md")
                        else:
                            self.fail_check(
                                f"agent.{agent_dir.name}.exists",
                                "Missing AGENT.md",
                                Severity.MEDIUM,
                                str(agent_dir)
                            )

    def _check_commands_docs(self):
        commands_dir = self.plugin_path / "commands"
        if not commands_dir.exists():
            self.fail_check("commands directory", "commands/ not found", Severity.HIGH)
            return

        for cmd_file in commands_dir.glob("*.md"):
            if cmd_file.name.startswith("_"):
                continue

            content = cmd_file.read_text(encoding='utf-8')
            cmd_name = cmd_file.stem

            # Check for usage section
            if "## Usage" in content or "## usage" in content:
                self.pass_check(f"command.{cmd_name}.usage", "Has Usage section")
            else:
                self.warn_check(
                    f"command.{cmd_name}.usage",
                    "Missing Usage section",
                    str(cmd_file)
                )


class AgentRoutingAssessor(BaseAssessor):
    """Validates agent routing configuration."""

    name = "agent-routing"
    description = "Validates keyword, file pattern, and error pattern routing"

    def run(self) -> AssessmentResult:
        import time
        start = time.time()

        config_file = self.plugin_path / "agents" / "config.json"
        if not config_file.exists():
            self.fail_check("config.json", "Not found", Severity.CRITICAL)
            return AssessmentResult(
                assessor=self.name,
                score=0,
                findings=self.findings,
                completed_at=datetime.now().isoformat(),
                duration_ms=(time.time() - start) * 1000
            )

        with open(config_file) as f:
            config = json.load(f)

        # Check routing section
        routing = config.get("routing", {})

        # Validate keyword routing
        self._check_keyword_routing(routing.get("keywords", {}))

        # Validate file patterns
        self._check_file_patterns(routing.get("filePatterns", {}))

        # Validate error patterns
        self._check_error_patterns(routing.get("errorPatterns", {}))

        # Check agent coverage
        self._check_agent_coverage(config)

        duration = (time.time() - start) * 1000
        score = self.calculate_score()

        return AssessmentResult(
            assessor=self.name,
            score=score,
            findings=self.findings,
            completed_at=datetime.now().isoformat(),
            duration_ms=duration
        )

    def _check_keyword_routing(self, keywords: dict):
        if not keywords:
            self.fail_check("routing.keywords", "No keywords defined", Severity.HIGH)
            return

        self.pass_check("routing.keywords", f"{len(keywords)} keywords defined")

        # Check for empty agent lists
        for keyword, agents in keywords.items():
            if not agents:
                self.fail_check(
                    f"routing.keyword.{keyword}",
                    "Empty agent list",
                    Severity.MEDIUM
                )

    def _check_file_patterns(self, patterns: dict):
        if not patterns:
            self.warn_check("routing.filePatterns", "No file patterns defined")
            return

        self.pass_check("routing.filePatterns", f"{len(patterns)} patterns defined")

    def _check_error_patterns(self, patterns: dict):
        if not patterns:
            self.warn_check("routing.errorPatterns", "No error patterns defined")
            return

        self.pass_check("routing.errorPatterns", f"{len(patterns)} patterns defined")

    def _check_agent_coverage(self, config: dict):
        # Get all agents from tiers
        all_agents = set()
        tiers = config.get("tiers", {})
        for tier_name, tier_data in tiers.items():
            agents = tier_data.get("agents", [])
            all_agents.update(agents)

        # Get agents referenced in routing
        routed_agents = set()
        routing = config.get("routing", {})

        for agents in routing.get("keywords", {}).values():
            routed_agents.update(agents)
        for agents in routing.get("filePatterns", {}).values():
            routed_agents.update(agents)
        for agents in routing.get("errorPatterns", {}).values():
            routed_agents.update(agents)

        # Check coverage
        unrouted = all_agents - routed_agents
        if unrouted:
            self.warn_check(
                "routing.coverage",
                f"Agents without routing: {', '.join(sorted(unrouted))}"
            )
        else:
            self.pass_check("routing.coverage", "All agents have routing entries")


class AssessmentRunner:
    """Main assessment runner that coordinates all assessors."""

    ASSESSORS = {
        "structure": PluginStructureAssessor,
        "hooks": HookProtocolAssessor,
        "documentation": DocumentationAssessor,
        "routing": AgentRoutingAssessor,
    }

    # Mapping from issue persona names to our assessors
    PERSONA_MAP = {
        "anthropic": "structure",
        "security": "hooks",  # Placeholder - could expand
        "performance": "routing",  # Uses routing for now
        "ux": "documentation",
        "architect": "structure",
        "docs": "documentation",
    }

    def __init__(self, plugin_path: Path):
        self.plugin_path = plugin_path
        self.results: List[AssessmentResult] = []

    def run_assessor(self, assessor_type: str) -> AssessmentResult:
        """Run a specific assessor."""
        # Map persona names to assessor types
        if assessor_type in self.PERSONA_MAP:
            assessor_type = self.PERSONA_MAP[assessor_type]

        if assessor_type not in self.ASSESSORS:
            raise ValueError(f"Unknown assessor: {assessor_type}")

        assessor_class = self.ASSESSORS[assessor_type]
        assessor = assessor_class(self.plugin_path)
        result = assessor.run()
        self.results.append(result)
        return result

    def run_all(self) -> List[AssessmentResult]:
        """Run all assessors."""
        for assessor_type in self.ASSESSORS:
            self.run_assessor(assessor_type)
        return self.results

    def get_overall_score(self) -> float:
        """Calculate weighted overall score."""
        if not self.results:
            return 0.0

        total_score = sum(r.score for r in self.results)
        return round(total_score / len(self.results), 1)

    def generate_report(self) -> str:
        """Generate markdown assessment report."""
        lines = [
            "# PopKit Self-Assessment Report",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Overall Score:** {self.get_overall_score()}/100",
            "",
            "## Summary",
            "",
            "| Assessor | Score | Critical | High | Warnings | Passed |",
            "|----------|-------|----------|------|----------|--------|",
        ]

        for result in self.results:
            lines.append(
                f"| {result.assessor} | {result.score}/100 | "
                f"{result.critical_count} | {result.high_count} | "
                f"{result.warning_count} | {result.pass_count} |"
            )

        lines.extend([
            "",
            "## Detailed Results",
            "",
        ])

        for result in self.results:
            lines.extend([
                f"### {result.assessor}",
                "",
                f"**Score:** {result.score}/100",
                f"**Duration:** {result.duration_ms:.1f}ms",
                "",
            ])

            # Group findings by status
            failed = [f for f in result.findings if f.status == Status.FAIL]
            warnings = [f for f in result.findings if f.status == Status.WARN]
            passed = [f for f in result.findings if f.status == Status.PASS]

            if failed:
                lines.extend(["#### Issues", ""])
                for finding in failed:
                    severity_icon = {
                        Severity.CRITICAL: "🔴",
                        Severity.HIGH: "🟠",
                        Severity.MEDIUM: "🟡",
                        Severity.LOW: "🔵"
                    }.get(finding.severity, "⚪")
                    lines.append(f"- {severity_icon} **{finding.check}**: {finding.message}")
                    if finding.recommendation:
                        lines.append(f"  - Recommendation: {finding.recommendation}")
                lines.append("")

            if warnings:
                lines.extend(["#### Warnings", ""])
                for finding in warnings:
                    lines.append(f"- ⚠️ **{finding.check}**: {finding.message}")
                lines.append("")

            lines.extend([
                f"#### Passed Checks: {len(passed)}",
                "",
            ])

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export results as JSON."""
        return json.dumps({
            "generated": datetime.now().isoformat(),
            "overall_score": self.get_overall_score(),
            "results": [r.to_dict() for r in self.results]
        }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="PopKit Self-Assessment Framework"
    )
    parser.add_argument(
        "assessor",
        nargs="?",
        default="all",
        help="Assessor to run (structure, hooks, documentation, routing, all)"
    )
    parser.add_argument(
        "--plugin-path",
        type=Path,
        default=Path(__file__).parent.parent.parent,
        help="Path to plugin directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of markdown"
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Save report to file"
    )

    args = parser.parse_args()

    runner = AssessmentRunner(args.plugin_path)

    try:
        if args.assessor == "all":
            runner.run_all()
        else:
            runner.run_assessor(args.assessor)

        if args.json:
            output = runner.to_json()
        else:
            output = runner.generate_report()

        print(output)

        if args.save:
            args.save.parent.mkdir(parents=True, exist_ok=True)
            args.save.write_text(output)
            print(f"\nReport saved to: {args.save}", file=sys.stderr)

        # Exit with error code if critical issues found
        critical_count = sum(r.critical_count for r in runner.results)
        if critical_count > 0:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
