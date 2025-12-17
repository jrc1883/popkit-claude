#!/usr/bin/env python3
"""
Tool Filtering for Context Optimization

Filters available tools based on workflow requirements from agents/config.json.
Part of Phase 1: Tool Choice Enforcement.
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path


def load_agent_config() -> Dict[str, Any]:
    """Load agent configuration with tool_choice settings."""
    config_path = Path(__file__).parent.parent.parent / "agents" / "config.json"

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_tools_for_workflow(
    workflow: str,
    available_tools: List[str],
    config: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Filter tools based on workflow requirements.

    Args:
        workflow: Workflow name (e.g., 'git-commit', 'file-edit')
        available_tools: List of available tool names
        config: Agent config dict (loaded if not provided)

    Returns:
        Filtered list of tool names

    Examples:
        >>> filter_tools_for_workflow('git-commit', ['Read', 'Bash'])
        ['Bash']
    """
    if config is None:
        config = load_agent_config()

    # Get workflow steps from config
    workflow_steps = config.get('tool_choice', {}).get('workflow_steps', {})

    # Unknown workflow → return all tools (safe fallback)
    if workflow not in workflow_steps:
        return available_tools

    # Get required tools for this workflow
    required = workflow_steps[workflow].get('required_tools', [])

    # Wildcard means all tools
    if '*' in required:
        return available_tools

    # Filter to only required tools
    return [t for t in available_tools if t in required]


class ToolFilter:
    """
    Tool filtering with context override support.

    Attributes:
        config: Loaded agent configuration
        enabled: Whether filtering is active (can be disabled for debugging)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, enabled: bool = True):
        """
        Initialize tool filter.

        Args:
            config: Agent config dict (loaded if not provided)
            enabled: Whether to apply filtering (default: True)
        """
        self.config = config or load_agent_config()
        self.enabled = enabled

    def filter(self, workflow: str, available_tools: List[str]) -> List[str]:
        """
        Filter tools for a workflow.

        Args:
            workflow: Workflow name
            available_tools: Available tool names

        Returns:
            Filtered tool list (or all tools if disabled)
        """
        if not self.enabled:
            return available_tools

        return filter_tools_for_workflow(workflow, available_tools, self.config)

    def disable(self):
        """Disable filtering (debugging/override)."""
        self.enabled = False

    def enable(self):
        """Enable filtering."""
        self.enabled = True
