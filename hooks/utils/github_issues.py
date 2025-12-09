#!/usr/bin/env python3
"""
GitHub Issues Utility
Creates and parses GitHub issues with PopKit Guidance sections.

Features:
- Create issues from lessons learned and error tracking
- Fetch and parse issues for workflow configuration
- Extract PopKit Guidance section for orchestration

Part of the popkit plugin system.
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# =============================================================================
# Issue Parsing - PopKit Guidance Section
# =============================================================================

def fetch_issue(issue_number: int) -> Optional[Dict[str, Any]]:
    """Fetch issue details from GitHub.

    Args:
        issue_number: The issue number to fetch

    Returns:
        Dict with issue data or None if failed
    """
    try:
        result = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--json",
             "number,title,body,labels,state,author"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return None
    except Exception:
        return None


def parse_popkit_guidance(issue_body: str) -> Dict[str, Any]:
    """Parse PopKit Guidance section from issue body.

    Extracts workflow configuration from the structured PopKit Guidance section
    that appears in issue templates.

    Args:
        issue_body: The full issue body text

    Returns:
        Dict with parsed workflow configuration:
        - workflow_type: "brainstorm_first" | "plan_required" | "direct"
        - phases: List of checked phases
        - agents: {"primary": [...], "supporting": [...]}
        - quality_gates: List of checked gates
        - power_mode: "recommended" | "optional" | "not_needed"
        - complexity: "small" | "medium" | "large" | "epic"
    """
    config = {
        "workflow_type": "direct",
        "phases": [],
        "agents": {"primary": [], "supporting": []},
        "quality_gates": [],
        "power_mode": "not_needed",
        "complexity": "medium",
        "raw_section": None
    }

    if not issue_body:
        return config

    # Find PopKit Guidance section
    guidance_match = re.search(
        r'## PopKit Guidance\s*\n(.*?)(?=\n## |\n---|\Z)',
        issue_body,
        re.DOTALL | re.IGNORECASE
    )

    if not guidance_match:
        return config

    guidance_text = guidance_match.group(1)
    config["raw_section"] = guidance_text

    # Parse Workflow type
    if re.search(r'\[x\].*Brainstorm First', guidance_text, re.IGNORECASE):
        config["workflow_type"] = "brainstorm_first"
    elif re.search(r'\[x\].*Plan Required', guidance_text, re.IGNORECASE):
        config["workflow_type"] = "plan_required"
    elif re.search(r'\[x\].*Direct Implementation', guidance_text, re.IGNORECASE):
        config["workflow_type"] = "direct"

    # Parse Development Phases
    phase_patterns = [
        ("discovery", r'\[x\].*Discovery'),
        ("architecture", r'\[x\].*Architecture'),
        ("implementation", r'\[x\].*Implementation'),
        ("testing", r'\[x\].*Testing'),
        ("documentation", r'\[x\].*Documentation'),
        ("review", r'\[x\].*Review'),
    ]
    for phase_name, pattern in phase_patterns:
        if re.search(pattern, guidance_text, re.IGNORECASE):
            config["phases"].append(phase_name)

    # Parse Suggested Agents
    agents_match = re.search(
        r'### Suggested Agents\s*\n(.*?)(?=\n### |\n## |\Z)',
        guidance_text,
        re.DOTALL
    )
    if agents_match:
        agents_text = agents_match.group(1)

        # Primary agents - capture everything after "Primary:" until newline
        primary_match = re.search(r'Primary:\s*(.+?)$', agents_text, re.MULTILINE)
        if primary_match:
            # Remove backticks and split by comma
            agent_str = primary_match.group(1).replace('`', '')
            agents = [a.strip() for a in agent_str.split(',')]
            config["agents"]["primary"] = [a for a in agents if a and a != '[agent-name]']

        # Supporting agents - capture everything after "Supporting:" until newline
        supporting_match = re.search(r'Supporting:\s*(.+?)$', agents_text, re.MULTILINE)
        if supporting_match:
            agent_str = supporting_match.group(1).replace('`', '')
            agents = [a.strip() for a in agent_str.split(',')]
            config["agents"]["supporting"] = [a for a in agents if a and a != '[agent-name]']

    # Parse Quality Gates
    gate_patterns = [
        ("typescript", r'\[x\].*TypeScript'),
        ("build", r'\[x\].*Build'),
        ("lint", r'\[x\].*Lint'),
        ("test", r'\[x\].*Test'),
        ("review", r'\[x\].*Manual review'),
    ]
    for gate_name, pattern in gate_patterns:
        if re.search(pattern, guidance_text, re.IGNORECASE):
            config["quality_gates"].append(gate_name)

    # Parse Power Mode recommendation
    if re.search(r'\[x\].*Recommended.*parallel', guidance_text, re.IGNORECASE):
        config["power_mode"] = "recommended"
    elif re.search(r'\[x\].*Optional.*coordination', guidance_text, re.IGNORECASE):
        config["power_mode"] = "optional"
    elif re.search(r'\[x\].*Not Needed', guidance_text, re.IGNORECASE):
        config["power_mode"] = "not_needed"

    # Parse Complexity
    if re.search(r'\[x\].*Small', guidance_text, re.IGNORECASE):
        config["complexity"] = "small"
    elif re.search(r'\[x\].*Medium', guidance_text, re.IGNORECASE):
        config["complexity"] = "medium"
    elif re.search(r'\[x\].*Large', guidance_text, re.IGNORECASE):
        config["complexity"] = "large"
    elif re.search(r'\[x\].*Epic', guidance_text, re.IGNORECASE):
        config["complexity"] = "epic"

    return config


def get_workflow_config(issue_number: int) -> Dict[str, Any]:
    """Get complete workflow configuration for an issue.

    Fetches issue from GitHub and parses PopKit Guidance section.
    Falls back to auto-generated plan if no guidance is present.

    Args:
        issue_number: The issue number to fetch

    Returns:
        Dict with:
        - issue: Basic issue info (number, title, state, labels)
        - config: Parsed PopKit Guidance configuration (or generated fallback)
        - should_brainstorm: Boolean - should brainstorming be triggered
        - should_activate_power_mode: Boolean - should Power Mode activate
        - suggested_phases: List of phases in order
        - generated: Boolean - True if config was auto-generated
        - needs_guidance: Boolean - True if user should add PopKit Guidance
    """
    result = {
        "issue": None,
        "config": None,
        "should_brainstorm": False,
        "should_activate_power_mode": False,
        "suggested_phases": [],
        "generated": False,
        "needs_guidance": False,
        "error": None
    }

    # Fetch issue
    issue = fetch_issue(issue_number)
    if not issue:
        result["error"] = f"Could not fetch issue #{issue_number}"
        return result

    result["issue"] = {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "labels": [l.get("name") for l in issue.get("labels", [])]
    }

    # Parse guidance from issue body
    config = parse_popkit_guidance(issue.get("body", ""))

    # Check if PopKit Guidance was found
    if config.get("raw_section"):
        # Use parsed guidance
        result["config"] = config
        result["generated"] = False
    else:
        # No PopKit Guidance - generate fallback plan
        fallback = generate_orchestration_plan({
            "title": issue.get("title"),
            "body": issue.get("body"),
            "labels": result["issue"]["labels"]
        })

        # Merge fallback into config format
        config = {
            "workflow_type": "direct",  # Default for generated plans
            "phases": fallback["phases"],
            "agents": fallback["agents"],
            "quality_gates": fallback["quality_gates"],
            "power_mode": fallback["power_mode"],
            "complexity": fallback["complexity"],
            "raw_section": None,  # Indicates auto-generated
            "generated": True,
            "issue_type": fallback["issue_type"],
            "confidence": fallback["confidence"],
            "reason": fallback["reason"]
        }
        result["config"] = config
        result["generated"] = True
        result["needs_guidance"] = fallback["needs_guidance"]

    # Determine if brainstorming should be triggered
    result["should_brainstorm"] = config["workflow_type"] == "brainstorm_first"

    # Determine if Power Mode should activate
    # Activate if: explicitly recommended, OR epic complexity, OR 3+ agents
    total_agents = len(config["agents"]["primary"]) + len(config["agents"]["supporting"])
    result["should_activate_power_mode"] = (
        config["power_mode"] == "recommended" or
        config["complexity"] == "epic" or
        total_agents >= 3
    )

    # Build suggested phase order
    default_phases = ["discovery", "architecture", "implementation", "testing", "documentation", "review"]
    if config["phases"]:
        # Use checked phases (or generated phases) in default order
        result["suggested_phases"] = [p for p in default_phases if p in config["phases"]]
    else:
        # Default to implementation-focused if no phases specified
        result["suggested_phases"] = ["implementation", "testing", "review"]

    return result


def infer_issue_type(issue: Dict[str, Any]) -> str:
    """Infer issue type from title and labels.

    Args:
        issue: Issue dict with title and labels

    Returns:
        One of: "bug", "feature", "architecture", "research", "unknown"
    """
    title = (issue.get("title") or "").lower()
    labels = [l.lower() for l in issue.get("labels", [])]

    # Check labels first
    if "bug" in labels:
        return "bug"
    if "architecture" in labels or "epic" in labels:
        return "architecture"
    if "research" in labels:
        return "research"
    if "enhancement" in labels or "feature" in labels:
        return "feature"

    # Check title patterns
    if title.startswith("[bug]") or "bug" in title:
        return "bug"
    if title.startswith("[architecture]") or title.startswith("[epic]"):
        return "architecture"
    if title.startswith("[research]"):
        return "research"
    if title.startswith("[feature]"):
        return "feature"

    return "unknown"


def get_agents_for_issue_type(issue_type: str) -> Dict[str, List[str]]:
    """Get suggested agents based on issue type.

    Args:
        issue_type: One of bug, feature, architecture, research

    Returns:
        Dict with primary and supporting agent lists
    """
    agent_map = {
        "bug": {
            "primary": ["bug-whisperer"],
            "supporting": ["test-writer-fixer"]
        },
        "feature": {
            "primary": ["code-architect"],
            "supporting": ["test-writer-fixer", "documentation-maintainer"]
        },
        "architecture": {
            "primary": ["code-architect", "refactoring-expert"],
            "supporting": ["migration-specialist", "code-reviewer"]
        },
        "research": {
            "primary": ["researcher"],
            "supporting": ["code-explorer"]
        },
        "unknown": {
            "primary": [],
            "supporting": []
        }
    }
    return agent_map.get(issue_type, agent_map["unknown"])


def get_default_phases(issue_type: str) -> List[str]:
    """Get default phases based on issue type.

    Args:
        issue_type: One of bug, feature, architecture, research

    Returns:
        List of phase names in order
    """
    phase_map = {
        "bug": ["discovery", "implementation", "testing"],
        "feature": ["discovery", "architecture", "implementation", "testing", "review"],
        "architecture": ["discovery", "architecture", "implementation", "testing", "documentation", "review"],
        "research": ["discovery", "documentation", "review"],
        "unknown": ["implementation", "testing", "review"]
    }
    return phase_map.get(issue_type, phase_map["unknown"])


def infer_complexity(issue: Dict[str, Any]) -> str:
    """Infer complexity from issue labels and content.

    Args:
        issue: Issue dict with title, body, and labels

    Returns:
        One of: "small", "medium", "large", "epic"
    """
    title = (issue.get("title") or "").lower()
    body = (issue.get("body") or "").lower()
    labels = [l.lower() for l in issue.get("labels", [])]

    # Check labels for explicit complexity
    if "epic" in labels:
        return "epic"
    if "large" in labels or "complex" in labels:
        return "large"
    if "small" in labels or "quick-win" in labels or "good-first-issue" in labels:
        return "small"

    # Check for complexity indicators in title/body
    # Epic indicators
    epic_keywords = ["architecture", "refactor entire", "major rewrite", "system-wide", "epic"]
    if any(kw in title or kw in body for kw in epic_keywords):
        return "epic"

    # Large indicators
    large_keywords = ["multiple components", "several files", "database migration", "api redesign"]
    if any(kw in title or kw in body for kw in large_keywords):
        return "large"

    # Small indicators
    small_keywords = ["typo", "simple fix", "minor", "update text", "rename"]
    if any(kw in title or kw in body for kw in small_keywords):
        return "small"

    # Default to medium
    return "medium"


def generate_orchestration_plan(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-generate orchestration plan when issue lacks PopKit Guidance.

    Analyzes the issue to infer type, complexity, phases, and agents.
    Used as a fallback when no PopKit Guidance section is present.

    Args:
        issue: Issue dict with number, title, body, labels

    Returns:
        Dict with:
        - generated: True (indicates this was auto-generated)
        - needs_guidance: True if inference confidence is low
        - issue_type: Inferred issue type
        - complexity: Inferred complexity
        - phases: List of suggested phases
        - agents: Dict with primary and supporting agents
        - power_mode: "recommended" | "optional" | "not_needed"
        - quality_gates: List of suggested gates
        - confidence: Float indicating inference confidence
        - reason: Explanation of inference
    """
    result = {
        "generated": True,
        "needs_guidance": False,
        "issue_type": "unknown",
        "complexity": "medium",
        "phases": [],
        "agents": {"primary": [], "supporting": []},
        "power_mode": "not_needed",
        "quality_gates": [],
        "confidence": 0.0,
        "reason": ""
    }

    # Infer issue type
    issue_type = infer_issue_type(issue)
    result["issue_type"] = issue_type

    # Infer complexity
    complexity = infer_complexity(issue)
    result["complexity"] = complexity

    # Get phases for issue type
    result["phases"] = get_default_phases(issue_type)

    # Get agents for issue type
    result["agents"] = get_agents_for_issue_type(issue_type)

    # Determine Power Mode recommendation
    total_agents = len(result["agents"]["primary"]) + len(result["agents"]["supporting"])
    if complexity == "epic" or total_agents >= 3:
        result["power_mode"] = "recommended"
    elif complexity == "large" or total_agents >= 2:
        result["power_mode"] = "optional"
    else:
        result["power_mode"] = "not_needed"

    # Set default quality gates
    result["quality_gates"] = ["typescript", "lint", "test"]

    # Calculate confidence
    # Higher confidence if we can clearly identify issue type and complexity
    confidence = 0.5  # Base confidence for auto-generation

    if issue_type != "unknown":
        confidence += 0.2
        result["reason"] = f"Inferred issue type: {issue_type}"

    if complexity != "medium":
        confidence += 0.1
        result["reason"] += f", complexity: {complexity}"

    # Check if labels provide clear indication
    labels = issue.get("labels", [])
    if labels:
        confidence += 0.1
        result["reason"] += f" (from labels: {', '.join(labels)})"

    result["confidence"] = min(confidence, 1.0)

    # If confidence is too low, suggest user provides guidance
    if confidence < 0.5 or issue_type == "unknown":
        result["needs_guidance"] = True
        result["reason"] = "Low confidence inference. Consider adding PopKit Guidance section to the issue."

    return result


def create_issue_from_lesson(lesson: dict) -> dict:
    """Create GitHub issue from lesson learned.

    Args:
        lesson: Dict containing lesson data with keys:
            - type: Category of lesson (routing_gap, validation_failure, etc.)
            - context: Where the issue was encountered
            - symptom: What was observed
            - root_cause: Why it happened
            - fix: How it was fixed
            - prevention: How to prevent it

    Returns:
        Dict with status and issue URL if successful
    """
    title = f"[Lesson Learned] {lesson.get('type', 'unknown')}: {lesson.get('symptom', 'No description')[:50]}"

    body = f"""## Context
{lesson.get('context', 'No context provided')}

## Symptom
{lesson.get('symptom', 'No symptom description')}

## Root Cause
{lesson.get('root_cause', 'Root cause not identified')}

## Fix Applied
{lesson.get('fix', 'No fix documented')}

## Prevention
{lesson.get('prevention', 'No prevention measures documented')}

---
*Auto-generated from popkit error tracking on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--title", title,
                "--body", body,
                "--label", "lesson-learned,automated"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            return {
                "status": "created",
                "url": issue_url,
                "title": title
            }
        else:
            return {
                "status": "error",
                "error": result.stderr,
                "title": title
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Timeout creating issue"}
    except FileNotFoundError:
        return {"status": "error", "error": "gh CLI not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def create_issue_from_validation_failure(validation_result: dict) -> dict:
    """Create GitHub issue from validation failure.

    Args:
        validation_result: Dict containing validation data with keys:
            - agent: Name of the agent that failed
            - output_style: Expected output style
            - missing_fields: List of missing required fields

    Returns:
        Dict with status and issue URL if successful
    """
    agent = validation_result.get('agent', 'unknown')
    output_style = validation_result.get('output_style', 'unknown')
    missing = validation_result.get('missing_fields', [])

    title = f"[Validation Failure] {agent}: Missing {len(missing)} required fields"

    body = f"""## Agent
`{agent}`

## Expected Output Style
`{output_style}`

## Missing Required Fields
{chr(10).join(f'- `{field}`' for field in missing)}

## Context
Agent output did not conform to the declared output_style schema.

## Suggested Fix
Update the agent prompt or implementation to include the required fields.

---
*Auto-generated from popkit output validator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--title", title,
                "--body", body,
                "--label", "validation-failure,agent,automated"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return {
                "status": "created",
                "url": result.stdout.strip(),
                "title": title
            }
        else:
            return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def save_lesson_locally(lesson: dict, status_file: Path = None) -> dict:
    """Save lesson to local STATUS.json file.

    Args:
        lesson: Lesson data to save
        status_file: Path to STATUS.json (default: .claude/STATUS.json)

    Returns:
        Dict with status of operation
    """
    if status_file is None:
        status_file = Path(".claude/STATUS.json")

    try:
        # Load existing status
        status = {}
        if status_file.exists():
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)

        # Initialize lessons_learned if not present
        if 'lessons_learned' not in status:
            status['lessons_learned'] = []

        # Add ID and timestamp if not present
        if 'id' not in lesson:
            lesson['id'] = f"LL-{len(status['lessons_learned']) + 1:03d}"
        if 'date' not in lesson:
            lesson['date'] = datetime.now().strftime('%Y-%m-%d')

        # Add lesson
        status['lessons_learned'].append(lesson)

        # Save status
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)

        return {
            "status": "saved",
            "id": lesson['id'],
            "file": str(status_file)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def save_error_locally(error: dict, status_file: Path = None) -> dict:
    """Save error to local STATUS.json error_log.

    Args:
        error: Error data to save
        status_file: Path to STATUS.json (default: .claude/STATUS.json)

    Returns:
        Dict with status of operation
    """
    if status_file is None:
        status_file = Path(".claude/STATUS.json")

    try:
        # Load existing status
        status = {}
        if status_file.exists():
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)

        # Initialize error_log if not present
        if 'error_log' not in status:
            status['error_log'] = []

        # Add timestamp if not present
        if 'timestamp' not in error:
            error['timestamp'] = datetime.now().isoformat()

        # Add error
        status['error_log'].append(error)

        # Keep only last 100 errors
        if len(status['error_log']) > 100:
            status['error_log'] = status['error_log'][-100:]

        # Save status
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)

        return {"status": "saved", "file": str(status_file)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import sys

    # Test mode selection
    if len(sys.argv) > 1:
        if sys.argv[1] == "parse" and len(sys.argv) > 2:
            # Test parsing an issue: python github_issues.py parse 11
            issue_num = int(sys.argv[2])
            print(f"Fetching and parsing issue #{issue_num}...")
            result = get_workflow_config(issue_num)
            print(json.dumps(result, indent=2))
            sys.exit(0)

        elif sys.argv[1] == "test-parse":
            # Test parsing with sample body
            sample_body = """
## Summary
Test issue for parsing

## PopKit Guidance

### Workflow
- [x] **Brainstorm First** - Use `pop-brainstorming` skill
- [ ] **Plan Required** - Use `/popkit:write-plan`
- [ ] **Direct Implementation** - Proceed directly

### Development Phases
- [x] Discovery
- [x] Architecture
- [x] Implementation
- [x] Testing
- [ ] Documentation
- [x] Review

### Suggested Agents
- Primary: `code-architect`, `refactoring-expert`
- Supporting: `migration-specialist`, `code-reviewer`

### Quality Gates
- [x] TypeScript check
- [x] Build verification
- [x] Lint pass
- [ ] Test pass

### Power Mode
- [x] **Recommended** - Multiple agents should work in parallel
- [ ] **Optional** - Can benefit from coordination
- [ ] **Not Needed** - Sequential work is fine

### Estimated Complexity
- [ ] Small
- [ ] Medium
- [ ] Large
- [x] Epic
"""
            print("Testing parse_popkit_guidance with sample body...")
            result = parse_popkit_guidance(sample_body)
            print(json.dumps(result, indent=2))

            print("\nExpected results:")
            print("  workflow_type: brainstorm_first")
            print("  phases: discovery, architecture, implementation, testing, review")
            print("  primary agents: code-architect, refactoring-expert")
            print("  power_mode: recommended")
            print("  complexity: epic")
            sys.exit(0)

    # Default: test save_lesson_locally
    test_lesson = {
        "type": "routing_gap",
        "context": "ESLint cleanup in test project",
        "symptom": "Specialists not triggered for lint work",
        "root_cause": "Missing 'lint', 'eslint' keywords in routing config",
        "fix": "Added lint keywords to agents/config.json",
        "prevention": "Add routing test cases for new keywords"
    }

    print("Testing save_lesson_locally...")
    result = save_lesson_locally(test_lesson)
    print(json.dumps(result, indent=2))

    print("\nUsage:")
    print("  python github_issues.py                  # Test save_lesson_locally")
    print("  python github_issues.py test-parse       # Test parsing sample body")
    print("  python github_issues.py parse <number>   # Parse real issue from GitHub")
