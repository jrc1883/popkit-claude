"""
PopKit Sandbox Testing Module

Local and cloud-based test execution with telemetry capture.

Part of Issues:
- #227: Local Test Runner
- #229: E2B Test Runner
"""

from .local_runner import (
    LocalTestRunner,
    TestConfig,
    TestResult,
    run_skill_test,
    run_command_test
)

# E2B runner (optional - requires e2b package)
try:
    from .e2b_runner import (
        E2BTestRunner,
        E2BConfig,
        E2BTestResult,
        is_e2b_available,
        run_skill_in_e2b,
        run_command_in_e2b
    )
    E2B_AVAILABLE = True
except ImportError:
    E2B_AVAILABLE = False
    E2BTestRunner = None
    E2BConfig = None
    E2BTestResult = None
    is_e2b_available = lambda: False
    run_skill_in_e2b = None
    run_command_in_e2b = None

__all__ = [
    # Local runner
    "LocalTestRunner",
    "TestConfig",
    "TestResult",
    "run_skill_test",
    "run_command_test",
    # E2B runner
    "E2BTestRunner",
    "E2BConfig",
    "E2BTestResult",
    "is_e2b_available",
    "run_skill_in_e2b",
    "run_command_in_e2b",
    "E2B_AVAILABLE"
]
