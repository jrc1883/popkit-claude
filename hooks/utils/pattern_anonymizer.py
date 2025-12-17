#!/usr/bin/env python3
"""
Pattern Anonymizer Utility

Removes project-specific, personal, and sensitive information from patterns
before they are shared with the PopKit Cloud community database.

Part of the popkit plugin system.
"""

import os
import re
import hashlib
from typing import Dict, Any, List, Optional, Set
from pathlib import Path


# Patterns to redact
SENSITIVE_PATTERNS = [
    # API keys and tokens
    (r'(?i)(api[_-]?key|apikey|token|secret|password|auth|bearer)\s*[=:]\s*["\']?[\w\-\.]+["\']?', '[REDACTED_CREDENTIAL]'),
    (r'(?i)sk[-_][a-zA-Z0-9]{32,}', '[REDACTED_API_KEY]'),
    (r'(?i)pk[-_][a-zA-Z0-9]{32,}', '[REDACTED_API_KEY]'),

    # Database connection strings
    (r'(?i)(postgres|mysql|mongodb|redis)://[^\s"\']+', '[REDACTED_DB_URL]'),

    # Email addresses
    (r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]'),

    # IP addresses
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]'),

    # AWS/GCP/Azure credentials
    (r'(?i)AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]'),
    (r'(?i)(?:aws|gcp|azure)[_-]?(?:access|secret|key)[_-]?\w*\s*[=:]\s*["\']?[\w\-\.\/]+["\']?', '[REDACTED_CLOUD_CRED]'),

    # Private keys
    (r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |DSA |EC )?PRIVATE KEY-----', '[REDACTED_PRIVATE_KEY]'),

    # JWT tokens
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED_JWT]'),
]

# Path patterns to generalize
PATH_PATTERNS = [
    # Windows user paths
    (r'C:\\Users\\[^\\]+', 'C:\\Users\\[USER]'),
    (r'/Users/[^/]+', '/Users/[USER]'),
    (r'/home/[^/]+', '/home/[USER]'),

    # Common project path patterns
    (r'(?i)/(?:projects?|dev|code|workspace|repos?)/[^/\s"\']+', '/[PROJECT_DIR]'),
]

# Project-specific names to replace
PROJECT_IDENTIFIERS = [
    'project_name',
    'app_name',
    'package_name',
    'repo_name',
    'company_name',
    'org_name',
]


def generate_hash(text: str, length: int = 8) -> str:
    """Generate a consistent short hash for anonymization.

    Args:
        text: Text to hash
        length: Length of hash to return

    Returns:
        Short hash string
    """
    return hashlib.sha256(text.encode()).hexdigest()[:length]


def redact_sensitive_data(text: str) -> str:
    """Remove sensitive data patterns from text.

    Args:
        text: Text to redact

    Returns:
        Redacted text
    """
    result = text

    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)

    return result


def generalize_paths(text: str, project_root: Optional[str] = None) -> str:
    """Replace specific file paths with generalized patterns.

    Args:
        text: Text containing paths
        project_root: Optional project root to replace

    Returns:
        Text with generalized paths
    """
    result = text

    # Replace project root if provided
    if project_root:
        # Normalize path separators
        normalized = project_root.replace('\\', '/')
        result = result.replace(project_root, '[PROJECT_ROOT]')
        result = result.replace(normalized, '[PROJECT_ROOT]')
        result = result.replace(project_root.replace('/', '\\'), '[PROJECT_ROOT]')

    # Apply general path patterns
    for pattern, replacement in PATH_PATTERNS:
        result = re.sub(pattern, replacement, result)

    return result


def anonymize_project_names(text: str, project_names: Set[str]) -> str:
    """Replace specific project names with generic placeholders.

    Args:
        text: Text to anonymize
        project_names: Set of project names to replace

    Returns:
        Anonymized text
    """
    result = text

    for name in project_names:
        if len(name) > 2:  # Only replace meaningful names
            # Create a consistent hash for this project name
            hash_id = generate_hash(name)
            placeholder = f'[PROJECT_{hash_id}]'

            # Replace case-insensitively
            result = re.sub(
                rf'\b{re.escape(name)}\b',
                placeholder,
                result,
                flags=re.IGNORECASE
            )

    return result


def extract_project_context(project_root: str) -> Dict[str, Any]:
    """Extract project context for anonymization.

    Args:
        project_root: Path to project root

    Returns:
        Dict with project context
    """
    import json

    context = {
        'project_names': set(),
        'custom_paths': set(),
    }

    # Get project name from package.json
    package_json = os.path.join(project_root, 'package.json')
    if os.path.isfile(package_json):
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                if 'name' in pkg:
                    context['project_names'].add(pkg['name'])
                if 'author' in pkg:
                    if isinstance(pkg['author'], str):
                        context['project_names'].add(pkg['author'].split('<')[0].strip())
        except (json.JSONDecodeError, IOError):
            pass

    # Get project name from pyproject.toml
    pyproject = os.path.join(project_root, 'pyproject.toml')
    if os.path.isfile(pyproject):
        try:
            with open(pyproject, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    context['project_names'].add(match.group(1))
        except IOError:
            pass

    # Add directory name
    context['project_names'].add(os.path.basename(project_root))

    return context


def anonymize_pattern(
    pattern: Dict[str, Any],
    project_root: Optional[str] = None,
    extra_names: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """Fully anonymize a pattern for sharing.

    Args:
        pattern: Pattern dict with 'content', 'type', etc.
        project_root: Optional project root for path replacement
        extra_names: Additional project names to anonymize

    Returns:
        Anonymized pattern dict
    """
    result = pattern.copy()

    # Get project context
    project_names = extra_names or set()
    if project_root:
        context = extract_project_context(project_root)
        project_names.update(context['project_names'])

    # Process each string field
    string_fields = ['content', 'description', 'solution', 'error_message', 'command']

    for field in string_fields:
        if field in result and isinstance(result[field], str):
            value = result[field]

            # Step 1: Redact sensitive data
            value = redact_sensitive_data(value)

            # Step 2: Generalize paths
            value = generalize_paths(value, project_root)

            # Step 3: Anonymize project names
            value = anonymize_project_names(value, project_names)

            result[field] = value

    # Remove potentially identifying metadata
    fields_to_remove = [
        'user_id', 'email', 'author', 'project_path',
        'machine_id', 'hostname', 'username'
    ]

    for field in fields_to_remove:
        if field in result:
            del result[field]

    # Add anonymization metadata
    result['_anonymized'] = True
    result['_anonymized_at'] = __import__('datetime').datetime.now(
        __import__('datetime').timezone.utc
    ).isoformat().replace('+00:00', 'Z')

    return result


def validate_anonymization(pattern: Dict[str, Any]) -> Dict[str, List[str]]:
    """Validate that a pattern has been properly anonymized.

    Args:
        pattern: Anonymized pattern to validate

    Returns:
        Dict with 'warnings' and 'errors' lists
    """
    issues = {
        'warnings': [],
        'errors': []
    }

    # Check for remaining sensitive patterns
    string_content = ' '.join(
        str(v) for v in pattern.values()
        if isinstance(v, str)
    )

    # Check for emails
    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', string_content):
        issues['errors'].append('Email address found in pattern')

    # Check for API keys
    if re.search(r'(?i)(sk[-_]|pk[-_])[a-zA-Z0-9]{20,}', string_content):
        issues['errors'].append('API key pattern found')

    # Check for absolute paths
    if re.search(r'(?:C:\\Users\\[^\\]+|/Users/[^/]+|/home/[^/]+)', string_content):
        if '[USER]' not in string_content:
            issues['warnings'].append('User-specific path may remain')

    # Check for IP addresses
    if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', string_content):
        issues['warnings'].append('IP address found - may be intentional')

    return issues


def create_shareable_pattern(
    pattern_type: str,
    content: str,
    solution: str,
    project_root: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a new shareable pattern with proper anonymization.

    Args:
        pattern_type: Type of pattern (command, error, workflow)
        content: Original pattern content
        solution: Solution or correction
        project_root: Optional project root
        metadata: Optional additional metadata

    Returns:
        Anonymized, shareable pattern dict
    """
    import datetime
    import uuid

    pattern = {
        'id': str(uuid.uuid4()),
        'type': pattern_type,
        'content': content,
        'solution': solution,
        'created_at': datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat().replace('+00:00', 'Z'),
        'share_level': 'community',  # Default to community
        'quality_score': None,  # To be set by cloud
        'votes': 0,
    }

    # Add metadata if provided
    if metadata:
        for key, value in metadata.items():
            if key not in pattern:
                pattern[key] = value

    # Anonymize before returning
    return anonymize_pattern(pattern, project_root)


def prepare_batch_for_sharing(
    patterns: List[Dict[str, Any]],
    project_root: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Prepare a batch of patterns for sharing.

    Args:
        patterns: List of patterns to prepare
        project_root: Optional project root

    Returns:
        List of anonymized patterns
    """
    result = []

    for pattern in patterns:
        anonymized = anonymize_pattern(pattern, project_root)

        # Validate anonymization
        issues = validate_anonymization(anonymized)

        if not issues['errors']:
            result.append(anonymized)
        # Skip patterns with errors

    return result


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: pattern_anonymizer.py <command> [args]")
        print("Commands: test, anonymize <json>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "test":
        # Test with sample data
        test_pattern = {
            'type': 'command',
            'content': 'User tried: npm install in C:\\Users\\John\\projects\\my-secret-app',
            'solution': 'Use: npm ci for clean installs',
            'email': 'john@example.com',
            'api_key': 'sk-12345678901234567890123456789012'
        }

        print("Original:")
        print(json.dumps(test_pattern, indent=2))
        print()

        anonymized = anonymize_pattern(test_pattern)
        print("Anonymized:")
        print(json.dumps(anonymized, indent=2))
        print()

        issues = validate_anonymization(anonymized)
        print("Validation:", issues)

    elif command == "anonymize":
        if len(sys.argv) < 3:
            print("Usage: pattern_anonymizer.py anonymize <json>")
            sys.exit(1)

        try:
            pattern = json.loads(sys.argv[2])
            anonymized = anonymize_pattern(pattern)
            print(json.dumps(anonymized, indent=2))
        except json.JSONDecodeError:
            print("Error: Invalid JSON")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
