# packages/plugin/tests/hooks/test_tool_filter.py
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))

from tool_filter import ToolFilter, filter_tools_for_workflow

def test_filter_tools_for_git_commit_workflow():
    """Tool filtering for git commit should only include Bash"""
    available_tools = ['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob']
    config = {
        'tool_choice': {
            'workflow_steps': {
                'git-commit': {
                    'required_tools': ['Bash']
                }
            }
        }
    }

    filtered = filter_tools_for_workflow('git-commit', available_tools, config)

    assert filtered == ['Bash']
    assert 'Read' not in filtered
    assert 'Write' not in filtered


def test_filter_tools_fallback_to_all_when_no_workflow():
    """When workflow unknown, return all tools"""
    available_tools = ['Read', 'Write', 'Bash']
    config = {'tool_choice': {'workflow_steps': {}}}

    filtered = filter_tools_for_workflow('unknown-workflow', available_tools, config)

    assert filtered == available_tools


def test_filter_tools_handles_wildcard():
    """Wildcard * includes all tools"""
    available_tools = ['Read', 'Write', 'Bash']
    config = {
        'tool_choice': {
            'workflow_steps': {
                'full-access': {
                    'required_tools': ['*']
                }
            }
        }
    }

    filtered = filter_tools_for_workflow('full-access', available_tools, config)

    assert filtered == available_tools
