#!/usr/bin/env python3
"""
Local telemetry logging for test mode (Issue #258).

This module provides a compatibility layer for skill_state.py to log
telemetry events. It wraps test_telemetry.emit_event().
"""

import sys
from typing import Dict, Any
from test_telemetry import is_test_mode, emit_event as telemetry_emit


def log_event_if_test_mode(event: Dict[str, Any]) -> None:
    """Log event if in test mode.

    This is called by skill_state.py after creating events with
    test_telemetry.create_event().

    Args:
        event: Event dictionary to emit
    """
    if is_test_mode():
        telemetry_emit(event)
