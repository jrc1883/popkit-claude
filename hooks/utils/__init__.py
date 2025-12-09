#!/usr/bin/env python3
"""
Popkit Hooks Utilities Package

Provides shared utilities for popkit hooks including:
- version: Plugin version checking and update notifications
- github_issues: GitHub issue creation from errors and lessons
"""

from .github_issues import (
    create_issue_from_lesson,
    create_issue_from_validation_failure,
    save_lesson_locally,
    save_error_locally
)

# Version utilities will be imported when available
try:
    from .version import (
        check_for_updates,
        format_update_notification,
        get_current_version,
        SemanticVersion
    )
except ImportError:
    # version.py not yet created
    pass

__all__ = [
    # GitHub Issues
    'create_issue_from_lesson',
    'create_issue_from_validation_failure',
    'save_lesson_locally',
    'save_error_locally',
    # Version (when available)
    'check_for_updates',
    'format_update_notification',
    'get_current_version',
    'SemanticVersion'
]
