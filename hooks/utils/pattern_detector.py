#!/usr/bin/env python3
"""
Pattern Detector for Codebase Analysis

Detects code patterns, conventions, and architecture decisions in codebases.
Powers structured analysis and informs skill generation.

Part of PopKit Issue #50 (Phase 2: Generator Improvements).
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DetectedPattern:
    """A detected code pattern."""
    name: str           # e.g., "feature-based-organization"
    category: str       # e.g., "architecture", "state", "api", "naming", "testing"
    confidence: float   # 0.0 - 1.0
    examples: List[str] = field(default_factory=list)  # Relative file paths
    description: str = ""  # Human-readable explanation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _find_dirs(root: Path, patterns: List[str]) -> List[Path]:
    """Find directories matching any of the glob patterns."""
    found = []
    for pattern in patterns:
        found.extend(root.glob(pattern))
    return [p for p in found if p.is_dir()]


def _find_files(root: Path, patterns: List[str], exclude_dirs: Set[str] = None) -> List[Path]:
    """Find files matching any of the glob patterns, excluding certain directories."""
    exclude_dirs = exclude_dirs or {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    found = []

    for pattern in patterns:
        for path in root.glob(pattern):
            # Check if any parent is in exclude list
            if not any(part in exclude_dirs for part in path.parts):
                if path.is_file():
                    found.append(path)

    return found


def _relative_path(path: Path, root: Path) -> str:
    """Get relative path as string."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> Optional[Dict]:
    """Safely read a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _has_dependency(package_json: Dict, dep_name: str) -> bool:
    """Check if package.json has a dependency."""
    deps = package_json.get("dependencies", {})
    dev_deps = package_json.get("devDependencies", {})
    return dep_name in deps or dep_name in dev_deps


# =============================================================================
# COMPONENT PATTERN DETECTION
# =============================================================================

def detect_component_patterns(directory: Path) -> List[DetectedPattern]:
    """
    Detect UI component organization patterns.

    Looks for:
    - Atomic design (atoms/, molecules/, organisms/)
    - Feature-based (features/auth/, features/dashboard/)
    - Domain-driven (components/Button/, components/Card/)
    - Flat structure
    """
    patterns = []

    # Check for atomic design
    atomic_dirs = _find_dirs(directory, ["**/atoms", "**/molecules", "**/organisms", "**/templates"])
    if len(atomic_dirs) >= 2:
        patterns.append(DetectedPattern(
            name="atomic-design",
            category="architecture",
            confidence=min(0.3 + 0.2 * len(atomic_dirs), 0.9),
            examples=[_relative_path(d, directory) for d in atomic_dirs[:5]],
            description="Atomic Design pattern with atoms, molecules, organisms hierarchy"
        ))

    # Check for feature-based organization
    feature_dirs = _find_dirs(directory, ["**/features/*", "**/modules/*"])
    if len(feature_dirs) >= 2:
        patterns.append(DetectedPattern(
            name="feature-based-organization",
            category="architecture",
            confidence=min(0.4 + 0.15 * len(feature_dirs), 0.95),
            examples=[_relative_path(d, directory) for d in feature_dirs[:5]],
            description="Feature-based organization grouping related code by domain"
        ))

    # Check for component folders with index files
    component_dirs = _find_dirs(directory, ["**/components/*"])
    component_with_index = [d for d in component_dirs if (d / "index.ts").exists() or (d / "index.tsx").exists() or (d / "index.js").exists()]
    if len(component_with_index) >= 3:
        patterns.append(DetectedPattern(
            name="component-folder-pattern",
            category="architecture",
            confidence=min(0.3 + 0.1 * len(component_with_index), 0.85),
            examples=[_relative_path(d, directory) for d in component_with_index[:5]],
            description="Component folder pattern with index exports"
        ))

    # Check for flat components directory
    flat_components = _find_files(directory, ["**/components/*.tsx", "**/components/*.jsx", "**/components/*.vue"])
    if len(flat_components) >= 5 and len(component_dirs) < 3:
        patterns.append(DetectedPattern(
            name="flat-components",
            category="architecture",
            confidence=0.7,
            examples=[_relative_path(f, directory) for f in flat_components[:5]],
            description="Flat component structure with all components in one directory"
        ))

    return patterns


# =============================================================================
# API PATTERN DETECTION
# =============================================================================

def detect_api_patterns(directory: Path) -> List[DetectedPattern]:
    """
    Detect API organization patterns.

    Looks for:
    - Route handlers (app/api/, pages/api/, routes/)
    - Controller pattern
    - Service layer
    - Repository pattern
    """
    patterns = []

    # Check for Next.js API routes
    nextjs_api = _find_dirs(directory, ["**/app/api", "**/pages/api"])
    if nextjs_api:
        route_files = _find_files(directory, ["**/app/api/**/route.ts", "**/app/api/**/route.js", "**/pages/api/**/*.ts", "**/pages/api/**/*.js"])
        patterns.append(DetectedPattern(
            name="nextjs-api-routes",
            category="api",
            confidence=0.95 if route_files else 0.7,
            examples=[_relative_path(f, directory) for f in route_files[:5]],
            description="Next.js API routes pattern"
        ))

    # Check for Express-style routes
    routes_dir = _find_dirs(directory, ["**/routes", "**/routers"])
    if routes_dir:
        route_files = _find_files(directory, ["**/routes/*.ts", "**/routes/*.js", "**/routers/*.ts", "**/routers/*.js"])
        if route_files:
            patterns.append(DetectedPattern(
                name="express-routes",
                category="api",
                confidence=min(0.5 + 0.1 * len(route_files), 0.9),
                examples=[_relative_path(f, directory) for f in route_files[:5]],
                description="Express-style route handlers pattern"
            ))

    # Check for controller pattern
    controllers = _find_files(directory, ["**/controllers/*.ts", "**/controllers/*.js", "**/controller.ts", "**/controller.js", "**/*Controller.ts", "**/*Controller.js"])
    if controllers:
        patterns.append(DetectedPattern(
            name="controller-pattern",
            category="api",
            confidence=min(0.5 + 0.1 * len(controllers), 0.9),
            examples=[_relative_path(f, directory) for f in controllers[:5]],
            description="Controller pattern separating request handling from business logic"
        ))

    # Check for service layer
    services = _find_files(directory, ["**/services/*.ts", "**/services/*.js", "**/*Service.ts", "**/*Service.js", "**/service.ts", "**/service.js"])
    if services:
        patterns.append(DetectedPattern(
            name="service-layer",
            category="api",
            confidence=min(0.5 + 0.1 * len(services), 0.9),
            examples=[_relative_path(f, directory) for f in services[:5]],
            description="Service layer pattern for business logic encapsulation"
        ))

    # Check for repository pattern
    repos = _find_files(directory, ["**/repositories/*.ts", "**/repositories/*.js", "**/*Repository.ts", "**/*Repository.js", "**/repository.ts", "**/repository.js"])
    if repos:
        patterns.append(DetectedPattern(
            name="repository-pattern",
            category="api",
            confidence=min(0.5 + 0.1 * len(repos), 0.9),
            examples=[_relative_path(f, directory) for f in repos[:5]],
            description="Repository pattern for data access abstraction"
        ))

    return patterns


# =============================================================================
# STATE MANAGEMENT PATTERN DETECTION
# =============================================================================

def detect_state_patterns(directory: Path) -> List[DetectedPattern]:
    """
    Detect state management patterns.

    Looks for:
    - Redux (store/, slices/, actions/)
    - Context API (contexts/, providers/)
    - Zustand/Jotai
    - React Query
    - Custom hooks pattern
    """
    patterns = []

    # Check package.json for state libraries
    package_json_path = directory / "package.json"
    pkg = _read_json(package_json_path) if package_json_path.exists() else {}
    if pkg is None:
        pkg = {}

    # Redux
    if _has_dependency(pkg, "redux") or _has_dependency(pkg, "@reduxjs/toolkit"):
        redux_files = _find_files(directory, ["**/store/*.ts", "**/store/*.js", "**/slices/*.ts", "**/slices/*.js", "**/reducers/*.ts", "**/reducers/*.js"])
        patterns.append(DetectedPattern(
            name="redux",
            category="state",
            confidence=0.95 if redux_files else 0.7,
            examples=[_relative_path(f, directory) for f in redux_files[:5]],
            description="Redux state management with actions and reducers"
        ))

    # Zustand
    if _has_dependency(pkg, "zustand"):
        zustand_files = _find_files(directory, ["**/store*.ts", "**/store*.js", "**/*Store.ts", "**/*Store.js"])
        patterns.append(DetectedPattern(
            name="zustand",
            category="state",
            confidence=0.9,
            examples=[_relative_path(f, directory) for f in zustand_files[:5]],
            description="Zustand lightweight state management"
        ))

    # Jotai
    if _has_dependency(pkg, "jotai"):
        patterns.append(DetectedPattern(
            name="jotai",
            category="state",
            confidence=0.9,
            examples=[],
            description="Jotai atomic state management"
        ))

    # React Query / TanStack Query
    if _has_dependency(pkg, "@tanstack/react-query") or _has_dependency(pkg, "react-query"):
        query_files = _find_files(directory, ["**/queries/*.ts", "**/queries/*.js", "**/*Query.ts", "**/*Query.js", "**/hooks/use*.ts", "**/hooks/use*.js"])
        patterns.append(DetectedPattern(
            name="react-query",
            category="state",
            confidence=0.9,
            examples=[_relative_path(f, directory) for f in query_files[:5]],
            description="React Query for server state management"
        ))

    # Context API
    context_files = _find_files(directory, ["**/contexts/*.tsx", "**/contexts/*.jsx", "**/providers/*.tsx", "**/providers/*.jsx", "**/*Context.tsx", "**/*Context.jsx", "**/*Provider.tsx", "**/*Provider.jsx"])
    if context_files:
        patterns.append(DetectedPattern(
            name="react-context",
            category="state",
            confidence=min(0.4 + 0.15 * len(context_files), 0.85),
            examples=[_relative_path(f, directory) for f in context_files[:5]],
            description="React Context API for state sharing"
        ))

    # Custom hooks pattern
    hook_files = _find_files(directory, ["**/hooks/use*.ts", "**/hooks/use*.tsx", "**/hooks/use*.js", "**/hooks/use*.jsx"])
    if len(hook_files) >= 3:
        patterns.append(DetectedPattern(
            name="custom-hooks",
            category="state",
            confidence=min(0.4 + 0.1 * len(hook_files), 0.9),
            examples=[_relative_path(f, directory) for f in hook_files[:5]],
            description="Custom React hooks for reusable stateful logic"
        ))

    return patterns


# =============================================================================
# NAMING CONVENTION DETECTION
# =============================================================================

def detect_naming_conventions(directory: Path) -> List[DetectedPattern]:
    """
    Detect naming conventions.

    Looks for:
    - camelCase vs PascalCase vs snake_case
    - File naming (Component.tsx vs component.tsx)
    - Test file naming (*.test.ts vs *.spec.ts)
    - Index exports pattern
    """
    patterns = []

    # Check component file naming
    pascal_components = _find_files(directory, ["**/components/**/[A-Z]*.tsx", "**/components/**/[A-Z]*.jsx"])
    kebab_components = _find_files(directory, ["**/components/**/[a-z]*-[a-z]*.tsx", "**/components/**/[a-z]*-[a-z]*.jsx"])

    if len(pascal_components) > len(kebab_components) and pascal_components:
        patterns.append(DetectedPattern(
            name="pascal-case-components",
            category="naming",
            confidence=min(0.5 + 0.1 * len(pascal_components), 0.9),
            examples=[_relative_path(f, directory) for f in pascal_components[:5]],
            description="PascalCase naming for component files (Button.tsx)"
        ))
    elif len(kebab_components) > len(pascal_components) and kebab_components:
        patterns.append(DetectedPattern(
            name="kebab-case-components",
            category="naming",
            confidence=min(0.5 + 0.1 * len(kebab_components), 0.9),
            examples=[_relative_path(f, directory) for f in kebab_components[:5]],
            description="kebab-case naming for component files (button-group.tsx)"
        ))

    # Check test file naming
    test_files = _find_files(directory, ["**/*.test.ts", "**/*.test.tsx", "**/*.test.js", "**/*.test.jsx"])
    spec_files = _find_files(directory, ["**/*.spec.ts", "**/*.spec.tsx", "**/*.spec.js", "**/*.spec.jsx"])

    if len(test_files) > len(spec_files) and test_files:
        patterns.append(DetectedPattern(
            name="test-suffix",
            category="naming",
            confidence=min(0.5 + 0.1 * len(test_files), 0.9),
            examples=[_relative_path(f, directory) for f in test_files[:5]],
            description="*.test.ts naming convention for test files"
        ))
    elif len(spec_files) > len(test_files) and spec_files:
        patterns.append(DetectedPattern(
            name="spec-suffix",
            category="naming",
            confidence=min(0.5 + 0.1 * len(spec_files), 0.9),
            examples=[_relative_path(f, directory) for f in spec_files[:5]],
            description="*.spec.ts naming convention for test files"
        ))

    # Check for barrel exports (index.ts)
    index_files = _find_files(directory, ["**/index.ts", "**/index.tsx", "**/index.js", "**/index.jsx"])
    # Filter to only those that are re-exports
    if len(index_files) >= 5:
        patterns.append(DetectedPattern(
            name="barrel-exports",
            category="naming",
            confidence=min(0.4 + 0.05 * len(index_files), 0.85),
            examples=[_relative_path(f, directory) for f in index_files[:5]],
            description="Barrel exports pattern using index.ts files"
        ))

    return patterns


# =============================================================================
# TESTING PATTERN DETECTION
# =============================================================================

def detect_testing_patterns(directory: Path) -> List[DetectedPattern]:
    """
    Detect testing patterns.

    Looks for:
    - Colocated tests (__tests__/, *.test.ts next to source)
    - Separate test directory (tests/, __tests__/)
    - E2E vs unit vs integration organization
    - Fixture patterns
    """
    patterns = []

    # Check for colocated tests
    colocated_test_dirs = _find_dirs(directory, ["**/__tests__"])
    colocated_tests = _find_files(directory, ["**/src/**/*.test.ts", "**/src/**/*.test.tsx", "**/src/**/*.spec.ts", "**/src/**/*.spec.tsx"])

    if colocated_test_dirs or len(colocated_tests) >= 3:
        examples = [_relative_path(d, directory) for d in colocated_test_dirs[:3]]
        examples.extend([_relative_path(f, directory) for f in colocated_tests[:2]])
        patterns.append(DetectedPattern(
            name="colocated-tests",
            category="testing",
            confidence=min(0.5 + 0.1 * (len(colocated_test_dirs) + len(colocated_tests) // 3), 0.9),
            examples=examples[:5],
            description="Tests colocated with source files in __tests__ directories"
        ))

    # Check for separate tests directory
    tests_dir = directory / "tests"
    test_dir = directory / "test"
    if tests_dir.is_dir() or test_dir.is_dir():
        test_root = tests_dir if tests_dir.is_dir() else test_dir
        test_files = list(test_root.rglob("*.ts")) + list(test_root.rglob("*.js"))
        if test_files:
            patterns.append(DetectedPattern(
                name="separate-tests-directory",
                category="testing",
                confidence=min(0.6 + 0.05 * len(test_files), 0.9),
                examples=[_relative_path(f, directory) for f in test_files[:5]],
                description="Separate tests/ directory for all test files"
            ))

    # Check for E2E tests
    e2e_dirs = _find_dirs(directory, ["**/e2e", "**/cypress", "**/playwright"])
    if e2e_dirs:
        e2e_files = _find_files(directory, ["**/e2e/**/*.ts", "**/e2e/**/*.js", "**/cypress/**/*.ts", "**/cypress/**/*.js", "**/playwright/**/*.ts", "**/playwright/**/*.js"])
        patterns.append(DetectedPattern(
            name="e2e-tests",
            category="testing",
            confidence=0.9 if e2e_files else 0.7,
            examples=[_relative_path(f, directory) for f in e2e_files[:5]],
            description="End-to-end testing with dedicated e2e directory"
        ))

    # Check for fixtures
    fixtures = _find_dirs(directory, ["**/fixtures", "**/__fixtures__"])
    if fixtures:
        fixture_files = _find_files(directory, ["**/fixtures/*", "**/__fixtures__/*"])
        patterns.append(DetectedPattern(
            name="test-fixtures",
            category="testing",
            confidence=min(0.5 + 0.1 * len(fixture_files), 0.85),
            examples=[_relative_path(f, directory) for f in fixture_files[:5]],
            description="Test fixtures for mock data and test setup"
        ))

    # Check for mocks
    mocks = _find_dirs(directory, ["**/mocks", "**/__mocks__"])
    if mocks:
        mock_files = _find_files(directory, ["**/mocks/*", "**/__mocks__/*"])
        patterns.append(DetectedPattern(
            name="test-mocks",
            category="testing",
            confidence=min(0.5 + 0.1 * len(mock_files), 0.85),
            examples=[_relative_path(f, directory) for f in mock_files[:5]],
            description="Mock modules for testing isolation"
        ))

    return patterns


# =============================================================================
# FRAMEWORK DETECTION
# =============================================================================

def detect_frameworks(directory: Path) -> List[DetectedPattern]:
    """
    Detect frameworks and major libraries.

    Returns patterns for detected frameworks with version info.
    """
    patterns = []

    package_json_path = directory / "package.json"
    pkg = _read_json(package_json_path) if package_json_path.exists() else {}
    if pkg is None:
        pkg = {}
    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    # Next.js
    if "next" in all_deps:
        nextjs_config = list(directory.glob("next.config.*"))
        app_dir = (directory / "app").is_dir()
        pages_dir = (directory / "pages").is_dir()

        examples = []
        if nextjs_config:
            examples.append(_relative_path(nextjs_config[0], directory))
        if app_dir:
            examples.append("app/")
        if pages_dir:
            examples.append("pages/")

        patterns.append(DetectedPattern(
            name="nextjs",
            category="framework",
            confidence=0.95,
            examples=examples,
            description=f"Next.js {all_deps.get('next', 'unknown')} {'(App Router)' if app_dir else '(Pages Router)'}"
        ))

    # React (standalone)
    elif "react" in all_deps:
        patterns.append(DetectedPattern(
            name="react",
            category="framework",
            confidence=0.9,
            examples=[],
            description=f"React {all_deps.get('react', 'unknown')}"
        ))

    # Vue
    if "vue" in all_deps:
        patterns.append(DetectedPattern(
            name="vue",
            category="framework",
            confidence=0.9,
            examples=[],
            description=f"Vue.js {all_deps.get('vue', 'unknown')}"
        ))

    # Express
    if "express" in all_deps:
        patterns.append(DetectedPattern(
            name="express",
            category="framework",
            confidence=0.9,
            examples=[],
            description=f"Express.js {all_deps.get('express', 'unknown')}"
        ))

    # Fastify
    if "fastify" in all_deps:
        patterns.append(DetectedPattern(
            name="fastify",
            category="framework",
            confidence=0.9,
            examples=[],
            description=f"Fastify {all_deps.get('fastify', 'unknown')}"
        ))

    # Check for Python frameworks
    pyproject = directory / "pyproject.toml"
    requirements = directory / "requirements.txt"

    if pyproject.exists() or requirements.exists():
        # FastAPI
        if (pyproject.exists() and "fastapi" in pyproject.read_text().lower()) or \
           (requirements.exists() and "fastapi" in requirements.read_text().lower()):
            patterns.append(DetectedPattern(
                name="fastapi",
                category="framework",
                confidence=0.9,
                examples=[],
                description="FastAPI Python web framework"
            ))

        # Django
        if (pyproject.exists() and "django" in pyproject.read_text().lower()) or \
           (requirements.exists() and "django" in requirements.read_text().lower()):
            patterns.append(DetectedPattern(
                name="django",
                category="framework",
                confidence=0.9,
                examples=[],
                description="Django Python web framework"
            ))

        # Flask
        if (pyproject.exists() and "flask" in pyproject.read_text().lower()) or \
           (requirements.exists() and "flask" in requirements.read_text().lower()):
            patterns.append(DetectedPattern(
                name="flask",
                category="framework",
                confidence=0.9,
                examples=[],
                description="Flask Python web framework"
            ))

    # Check for Rust
    cargo_toml = directory / "Cargo.toml"
    if cargo_toml.exists():
        cargo_content = cargo_toml.read_text()
        if "actix" in cargo_content.lower():
            patterns.append(DetectedPattern(
                name="actix-web",
                category="framework",
                confidence=0.9,
                examples=["Cargo.toml"],
                description="Actix-web Rust web framework"
            ))
        elif "axum" in cargo_content.lower():
            patterns.append(DetectedPattern(
                name="axum",
                category="framework",
                confidence=0.9,
                examples=["Cargo.toml"],
                description="Axum Rust web framework"
            ))

    return patterns


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_project(directory: Path) -> List[DetectedPattern]:
    """
    Run all pattern detectors on a directory.

    Returns combined list of all detected patterns,
    sorted by confidence descending.
    """
    if isinstance(directory, str):
        directory = Path(directory)

    all_patterns = []

    # Run all detectors
    all_patterns.extend(detect_frameworks(directory))
    all_patterns.extend(detect_component_patterns(directory))
    all_patterns.extend(detect_api_patterns(directory))
    all_patterns.extend(detect_state_patterns(directory))
    all_patterns.extend(detect_naming_conventions(directory))
    all_patterns.extend(detect_testing_patterns(directory))

    # Sort by confidence descending
    all_patterns.sort(key=lambda p: p.confidence, reverse=True)

    return all_patterns


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detect code patterns in a project")
    parser.add_argument("directory", nargs="?", default=".", help="Project directory to analyze")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--min-confidence", "-m", type=float, default=0.0, help="Minimum confidence threshold")

    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    patterns = analyze_project(directory)

    # Filter by category if specified
    if args.category:
        patterns = [p for p in patterns if p.category == args.category]

    # Filter by confidence
    patterns = [p for p in patterns if p.confidence >= args.min_confidence]

    if args.json:
        print(json.dumps([p.to_dict() for p in patterns], indent=2))
    else:
        print(f"Detected Patterns in {directory.name}")
        print("=" * 50)

        if not patterns:
            print("No patterns detected.")
        else:
            for pattern in patterns:
                print(f"\n[{pattern.category}] {pattern.name} (confidence: {pattern.confidence:.2f})")
                print(f"  {pattern.description}")
                if pattern.examples:
                    print(f"  Examples: {', '.join(pattern.examples[:3])}")
