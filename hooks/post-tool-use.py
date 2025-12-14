#!/usr/bin/env python3
"""
Global Post-Tool-Use Hook
Logging, metrics collection, agent communication, and follow-up orchestration
Analyzes tool results and coordinates next steps in multi-agent workflows
"""

import os
import sys
import json
import re
import requests
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import project activity tracking
try:
    from utils.project_client import ProjectClient, ProjectActivity
    HAS_PROJECT_CLIENT = True
except ImportError:
    HAS_PROJECT_CLIENT = False

# Import skill state tracker for AskUserQuestion enforcement (Issue #159)
sys.path.insert(0, str(Path(__file__).parent / "utils"))
try:
    from skill_state import get_tracker, SkillStateTracker
    SKILL_STATE_AVAILABLE = True
except ImportError:
    SKILL_STATE_AVAILABLE = False

# Import workflow response router (Issue #206)
try:
    from response_router import (
        route_user_response,
        should_route_response,
        format_hook_output,
        get_workflow_status,
        get_pending_decision
    )
    WORKFLOW_ROUTER_AVAILABLE = True
except ImportError:
    WORKFLOW_ROUTER_AVAILABLE = False

# Import test telemetry for sandbox testing (Issue #226)
try:
    from test_telemetry import (
        is_test_mode, get_test_session_id,
        create_trace, create_decision, create_event
    )
    from local_telemetry import (
        get_local_storage,
        log_trace_if_test_mode, log_decision_if_test_mode, log_event_if_test_mode
    )
    TEST_TELEMETRY_AVAILABLE = True
except ImportError:
    TEST_TELEMETRY_AVAILABLE = False
    # Define stubs when not available
    def is_test_mode(): return False
    def get_test_session_id(): return None

class PostToolUseHook:
    def __init__(self):
        self.claude_dir = Path.home() / '.claude'
        self.config_dir = self.claude_dir / 'config'
        self.session_id = self.get_session_id()
        self.observability_endpoint = "http://localhost:8001/events"
        self.orchestrator_endpoint = "http://localhost:8005/followup"
        
        # Load configuration
        self.followup_rules = self.load_followup_rules()
        self.quality_metrics = self.load_quality_metrics()
        self.agent_communication_patterns = self.load_communication_patterns()
        
        # Initialize databases
        self.context_db = self.init_context_db()
        self.metrics_db = self.init_metrics_db()

        # Test telemetry state (Issue #226)
        self._trace_sequence = self._get_trace_sequence()
        
    def get_session_id(self) -> str:
        """Get current session ID from environment or context"""
        session_id = os.environ.get('CLAUDE_SESSION_ID')
        if not session_id:
            try:
                db_path = self.config_dir / 'context-memory.db'
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.execute(
                        "SELECT session_id FROM context_memory ORDER BY created_at DESC LIMIT 1"
                    )
                    result = cursor.fetchone()
                    if result:
                        session_id = result[0]
                    conn.close()
            except Exception:
                pass
        return session_id or "unknown"
    
    def load_followup_rules(self) -> Dict[str, List[str]]:
        """Load rules for automatic follow-up actions after tool use"""
        return {
            "file_modifications": {
                "Write": ["suggest_code_review", "check_for_tests", "validate_syntax"],
                "Edit": ["suggest_code_review", "run_linter", "check_imports"],
                "MultiEdit": ["comprehensive_review", "run_tests", "check_consistency"]
            },
            "code_analysis": {
                "Grep": ["analyze_patterns", "suggest_refactoring"],
                "Glob": ["assess_project_structure", "identify_duplicates"]
            },
            "external_operations": {
                "Bash": ["validate_output", "check_side_effects", "log_system_changes"],
                "WebFetch": ["cache_results", "validate_data", "check_rate_limits"]
            },
            "data_operations": {
                "Read": ["analyze_content", "suggest_optimizations"],
                "LS": ["assess_organization", "identify_patterns"]
            }
        }
    
    def load_quality_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Load quality assessment metrics for different tool results"""
        return {
            "code_quality": {
                "metrics": ["syntax_valid", "linting_clean", "test_coverage", "security_scan"],
                "thresholds": {"syntax_valid": 1.0, "linting_clean": 0.9, "test_coverage": 0.8}
            },
            "performance": {
                "metrics": ["execution_time", "memory_usage", "file_size", "complexity"],
                "thresholds": {"execution_time": 5.0, "file_size": 1000000, "complexity": 10}
            },
            "security": {
                "metrics": ["secret_exposure", "vulnerability_scan", "permission_check"],
                "thresholds": {"secret_exposure": 0, "vulnerability_scan": 0}
            }
        }
    
    def load_communication_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load agent communication and handoff patterns"""
        return {
            "sequential_handoffs": {
                "code_modification": ["code-reviewer", "security-auditor", "test-writer-fixer"],
                "ui_changes": ["ui-designer", "accessibility-guardian", "user-experience-optimizer"],
                "deployment": ["devops-automator", "security-tester", "environment-manager"]
            },
            "parallel_analysis": {
                "performance_issues": ["performance-optimizer", "load-tester", "performance-profiler"],
                "quality_assessment": ["code-reviewer", "quality-assurance-coordinator"],
                "security_review": ["security-auditor", "security-tester"]
            },
            "conditional_triggers": {
                "error_detected": ["bug-whisperer", "incident-responder"],
                "new_dependencies": ["dependency-detective", "security-auditor"],
                "large_changes": ["stakeholder-communicator", "documentation-maintainer"]
            }
        }
    
    def init_context_db(self) -> Optional[sqlite3.Connection]:
        """Initialize context database connection"""
        try:
            db_path = self.config_dir / 'context-memory.db'
            if db_path.exists():
                return sqlite3.connect(str(db_path))
        except Exception:
            pass
        return None
    
    def init_metrics_db(self) -> sqlite3.Connection:
        """Initialize metrics database"""
        db_path = self.config_dir / 'metrics.db'
        conn = sqlite3.connect(str(db_path))
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tool_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                execution_time REAL,
                success_rate REAL,
                error_count INTEGER,
                output_size INTEGER,
                quality_score REAL,
                agent_involvement TEXT,
                followup_actions TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success_rate REAL,
                average_time REAL,
                quality_score REAL,
                collaboration_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return conn
    
    def analyze_tool_result(self, tool_name: str, tool_args: Dict[str, Any], tool_result: Any) -> Dict[str, Any]:
        """Analyze tool execution results for quality and next steps"""
        analysis = {
            "success": True,
            "quality_score": 0.0,
            "issues": [],
            "suggestions": [],
            "metrics": {},
            "followup_needed": []
        }
        
        # Basic success detection
        if isinstance(tool_result, dict) and tool_result.get("error"):
            analysis["success"] = False
            analysis["issues"].append(f"Tool execution failed: {tool_result['error']}")
            analysis["followup_needed"].append("error_investigation")
        
        # Tool-specific analysis
        if tool_name == "Write" and analysis["success"]:
            analysis.update(self.analyze_write_result(tool_args, tool_result))
        elif tool_name in ["Edit", "MultiEdit"] and analysis["success"]:
            analysis.update(self.analyze_edit_result(tool_args, tool_result))
        elif tool_name == "Bash" and analysis["success"]:
            analysis.update(self.analyze_bash_result(tool_args, tool_result))
        elif tool_name == "Read" and analysis["success"]:
            analysis.update(self.analyze_read_result(tool_args, tool_result))
        
        return analysis
    
    def analyze_write_result(self, tool_args: Dict[str, Any], tool_result: Any) -> Dict[str, Any]:
        """Analyze Write tool results"""
        analysis = {"quality_score": 0.7, "followup_needed": []}
        
        file_path = tool_args.get("file_path", "")
        content = tool_args.get("content", "")
        
        # File type specific analysis
        if file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
            analysis["suggestions"].append("Consider running code review and linting")
            analysis["followup_needed"].extend(["code_review", "linting"])
            analysis["quality_score"] = 0.8
        elif file_path.endswith(('.py', '.rb', '.go')):
            analysis["suggestions"].append("Consider running syntax validation and tests")
            analysis["followup_needed"].extend(["syntax_check", "test_execution"])
        elif file_path.endswith(('.md', '.txt', '.rst')):
            analysis["suggestions"].append("Consider spell check and documentation review")
            analysis["followup_needed"].append("documentation_review")
        
        # Content analysis
        if len(content) > 10000:
            analysis["suggestions"].append("Large file created - consider breaking into smaller modules")
            analysis["followup_needed"].append("refactoring_assessment")
        
        # Security patterns
        if re.search(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
            analysis["issues"].append("Potential secret exposed in code")
            analysis["followup_needed"].append("security_review")
            analysis["quality_score"] = max(0.3, analysis["quality_score"] - 0.4)
        
        return analysis
    
    def analyze_edit_result(self, tool_args: Dict[str, Any], tool_result: Any) -> Dict[str, Any]:
        """Analyze Edit/MultiEdit tool results"""
        analysis = {"quality_score": 0.8, "followup_needed": ["code_review"]}
        
        file_path = tool_args.get("file_path", "")
        
        # Multi-edit specific analysis
        if "edits" in tool_args:
            edit_count = len(tool_args["edits"])
            if edit_count > 5:
                analysis["suggestions"].append(f"Large refactoring with {edit_count} changes - comprehensive review recommended")
                analysis["followup_needed"].extend(["comprehensive_review", "test_execution"])
            
            # Check for potential conflicts
            edit_locations = [edit.get("old_string", "")[:50] for edit in tool_args["edits"]]
            if len(set(edit_locations)) != len(edit_locations):
                analysis["issues"].append("Potential overlapping edits detected")
                analysis["quality_score"] -= 0.2
        
        # File-specific recommendations
        if file_path.endswith('.test.ts') or file_path.endswith('.spec.ts'):
            analysis["followup_needed"].append("test_execution")
        elif file_path.endswith(('.ts', '.tsx')):
            analysis["followup_needed"].extend(["type_checking", "linting"])
        
        return analysis
    
    def analyze_bash_result(self, tool_args: Dict[str, Any], tool_result: Any) -> Dict[str, Any]:
        """Analyze Bash tool results"""
        analysis = {"quality_score": 0.6, "followup_needed": []}
        
        command = tool_args.get("command", "")
        
        # Command category analysis
        if any(cmd in command for cmd in ["npm install", "yarn add", "pip install"]):
            analysis["followup_needed"].extend(["dependency_audit", "security_scan"])
            analysis["suggestions"].append("New dependencies installed - security audit recommended")
        elif any(cmd in command for cmd in ["git commit", "git push"]):
            analysis["followup_needed"].append("deployment_readiness")
            analysis["quality_score"] = 0.8
        elif any(cmd in command for cmd in ["docker build", "docker run"]):
            analysis["followup_needed"].extend(["container_security", "resource_monitoring"])
        elif "test" in command:
            analysis["followup_needed"].append("test_results_analysis")
            analysis["quality_score"] = 0.9
        
        # Output analysis
        if isinstance(tool_result, str):
            if "error" in tool_result.lower() or "failed" in tool_result.lower():
                analysis["issues"].append("Command execution reported errors")
                analysis["followup_needed"].append("error_investigation")
                analysis["quality_score"] = 0.3
            elif "warning" in tool_result.lower():
                analysis["suggestions"].append("Command completed with warnings")
                analysis["quality_score"] = 0.7
        
        return analysis
    
    def analyze_read_result(self, tool_args: Dict[str, Any], tool_result: Any) -> Dict[str, Any]:
        """Analyze Read tool results"""
        analysis = {"quality_score": 0.9, "followup_needed": []}
        
        file_path = tool_args.get("file_path", "")
        
        # Large file analysis
        if isinstance(tool_result, str) and len(tool_result) > 50000:
            analysis["suggestions"].append("Large file read - consider chunked processing")
            analysis["followup_needed"].append("optimization_review")
        
        # File type specific analysis
        if file_path.endswith('.log'):
            analysis["followup_needed"].append("log_analysis")
        elif file_path.endswith(('.json', '.yaml', '.yml')):
            analysis["followup_needed"].append("config_validation")
        elif file_path.endswith('.sql'):
            analysis["followup_needed"].extend(["query_optimization", "security_review"])
        
        return analysis
    
    def determine_followup_agents(self, tool_name: str, analysis: Dict[str, Any], project_context: Dict[str, Any]) -> List[str]:
        """Determine which agents should be activated for follow-up"""
        followup_agents = []
        
        # Rule-based agent selection
        for followup_type in analysis.get("followup_needed", []):
            if followup_type == "code_review":
                followup_agents.append("code-reviewer")
            elif followup_type == "security_review":
                followup_agents.extend(["security-auditor", "security-tester"])
            elif followup_type == "test_execution":
                followup_agents.append("automated-tester")
            elif followup_type == "performance_review":
                followup_agents.extend(["performance-optimizer", "load-tester"])
            elif followup_type == "documentation_review":
                followup_agents.append("documentation-maintainer")
            elif followup_type == "error_investigation":
                followup_agents.append("bug-whisperer")
        
        # Context-based agent selection
        if analysis.get("quality_score", 1.0) < 0.5:
            followup_agents.append("quality-assurance-coordinator")
        
        if len(analysis.get("issues", [])) > 2:
            followup_agents.append("incident-responder")
        
        # Project-specific agent selection
        if project_context.get("has_package_json"):
            if "dependency" in str(analysis.get("followup_needed", [])):
                followup_agents.append("dependency-detective")
        
        return list(set(followup_agents))  # Remove duplicates
    
    def calculate_quality_metrics(self, tool_name: str, analysis: Dict[str, Any], execution_time: float) -> Dict[str, float]:
        """Calculate quality metrics for tool execution"""
        metrics = {
            "success_rate": 1.0 if analysis["success"] else 0.0,
            "quality_score": analysis.get("quality_score", 0.5),
            "error_count": len(analysis.get("issues", [])),
            "execution_time": execution_time,
            "followup_complexity": len(analysis.get("followup_needed", [])) / 10.0
        }
        
        # Tool-specific metrics
        if tool_name == "Bash":
            metrics["safety_score"] = 1.0 - (metrics["error_count"] * 0.2)
        elif tool_name in ["Write", "Edit", "MultiEdit"]:
            metrics["code_impact_score"] = min(1.0, len(analysis.get("suggestions", [])) / 5.0)
        
        return metrics
    
    def store_metrics(self, tool_name: str, metrics: Dict[str, float], agent_involvement: List[str], followup_actions: List[str]):
        """Store tool execution metrics in database"""
        try:
            self.metrics_db.execute('''
                INSERT INTO tool_metrics 
                (session_id, timestamp, tool_name, execution_time, success_rate, 
                 error_count, quality_score, agent_involvement, followup_actions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                datetime.now().isoformat(),
                tool_name,
                metrics.get("execution_time", 0.0),
                metrics.get("success_rate", 0.0),
                int(metrics.get("error_count", 0)),
                metrics.get("quality_score", 0.0),
                json.dumps(agent_involvement),
                json.dumps(followup_actions)
            ))
            self.metrics_db.commit()
        except Exception as e:
            print(f"Warning: Could not store metrics: {e}", file=sys.stderr)
    
    def log_post_tool_event(self, tool_name: str, tool_args: Dict[str, Any], tool_result: Any, analysis: Dict[str, Any]):
        """Log post-tool-use event to observability system"""
        try:
            event_data = {
                "timestamp": datetime.now().isoformat(),
                "sessionId": self.session_id,
                "eventType": "post_tool_use",
                "hookType": "post_tool_use",
                "toolName": tool_name,
                "toolArgs": tool_args,
                "toolResult": str(tool_result)[:1000],  # Limit size
                "metadata": {
                    "analysis": analysis,
                    "working_directory": os.getcwd()
                }
            }
            
            response = requests.post(
                self.observability_endpoint,
                json=event_data,
                timeout=2
            )
            
            if response.status_code != 200:
                print(f"Warning: Observability logging failed: {response.status_code}", file=sys.stderr)
            
            # Also send to OPTIMUS Command Center
            try:
                optimus_data = {
                    "agentName": os.environ.get('CLAUDE_AGENT_NAME', 'claude'),
                    "activity": f"tool_use:{tool_name}",
                    "metadata": {
                        "toolName": tool_name,
                        "success": analysis.get("success", True),
                        "executionTime": analysis.get("metrics", {}).get("execution_time", 0),
                        "qualityScore": analysis.get("quality_score", 0),
                        "sessionId": self.session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                requests.post(
                    "http://localhost:3051/api/agent/activity",
                    json=optimus_data,
                    timeout=1
                )
            except:
                pass  # Fail silently for OPTIMUS integration
                
        except Exception as e:
            print(f"Warning: Could not log to observability system: {e}", file=sys.stderr)
    
    def request_followup_orchestration(self, tool_name: str, analysis: Dict[str, Any], followup_agents: List[str]) -> Optional[Dict]:
        """Request follow-up orchestration from orchestrator service"""
        try:
            orchestration_data = {
                "session_id": self.session_id,
                "completed_tool": tool_name,
                "analysis": analysis,
                "suggested_agents": followup_agents,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                self.orchestrator_endpoint,
                json=orchestration_data,
                timeout=3
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Warning: Followup orchestration failed: {response.status_code}", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Could not connect to orchestrator for followup: {e}", file=sys.stderr)
        
        return None
    
    def get_project_context(self) -> Dict[str, Any]:
        """Get current project context"""
        cwd = os.getcwd()
        context = {
            "working_directory": cwd,
            "project_name": Path(cwd).name,
            "has_package_json": os.path.exists(os.path.join(cwd, "package.json")),
            "has_tests": any(os.path.exists(os.path.join(cwd, d)) for d in ["test", "tests", "__tests__"]),
            "has_claude_md": os.path.exists(os.path.join(cwd, "CLAUDE.md")),
            "git_repository": os.path.exists(os.path.join(cwd, ".git"))
        }
        return context
    
    def process_tool_completion(self, tool_name: str, tool_args: Dict[str, Any], tool_result: Any, execution_time: float = 0.0) -> Dict[str, Any]:
        """Main processing function for completed tool execution"""
        result = {
            "tool_name": tool_name,
            "session_id": self.session_id,
            "analysis": {},
            "followup_agents": [],
            "recommendations": [],
            "metrics": {},
            "orchestration_result": None
        }
        
        # Analyze tool result
        analysis = self.analyze_tool_result(tool_name, tool_args, tool_result)
        result["analysis"] = analysis
        
        # Get project context
        project_context = self.get_project_context()
        
        # Determine follow-up agents
        followup_agents = self.determine_followup_agents(tool_name, analysis, project_context)
        result["followup_agents"] = followup_agents
        
        # Calculate metrics
        metrics = self.calculate_quality_metrics(tool_name, analysis, execution_time)
        result["metrics"] = metrics
        
        # Generate recommendations
        result["recommendations"] = analysis.get("suggestions", [])
        if followup_agents:
            result["recommendations"].append(f"Consider activating: {', '.join(followup_agents)}")
        
        # Store metrics
        self.store_metrics(tool_name, metrics, followup_agents, analysis.get("followup_needed", []))
        
        # Log event
        self.log_post_tool_event(tool_name, tool_args, tool_result, analysis)
        
        # Request follow-up orchestration
        if followup_agents:
            orchestration_result = self.request_followup_orchestration(tool_name, analysis, followup_agents)
            result["orchestration_result"] = orchestration_result

        # Track activity in PopKit Cloud (non-blocking)
        self.record_cloud_activity(tool_name, followup_agents)

        return result

    def check_pending_skill_decisions(self, tool_name: str, tool_result: str = "") -> Dict[str, Any]:
        """Check for pending completion decisions from active skill (Issue #159, #183).

        This implements the enforcement side of AskUserQuestion requirements.
        When a skill has pending decisions, we output a reminder to stderr.

        Enhanced in Issue #183 to:
        - Detect errors in tool output and record them
        - Check for required decisions that must be presented even on error
        - Provide more prominent reminders for required decisions

        Returns:
            Dict with pending decision info if any
        """
        if not SKILL_STATE_AVAILABLE:
            return {"has_pending": False}

        tracker = get_tracker()

        # Skip check for AskUserQuestion tool (it's being used, that's good)
        if tool_name == "AskUserQuestion":
            return {"has_pending": False, "recording_decision": True}

        # Check if there's an active skill with pending decisions
        if not tracker.is_skill_active():
            return {"has_pending": False}

        # Issue #183: Detect errors in tool output and record them
        error_detected = self._detect_error_in_output(tool_result)
        if error_detected:
            tracker.record_error(error_detected)

        # Check for required decisions (must be presented even on error)
        required = tracker.get_required_decisions()
        if required:
            first_required = required[0]
            return {
                "has_pending": True,
                "is_required": True,
                "has_error": tracker.has_error(),
                "error_message": tracker.state.last_error if tracker.state else None,
                "skill_name": tracker.get_active_skill(),
                "decision": first_required
            }

        # Check for error recovery decisions
        if tracker.has_error():
            recovery = tracker.get_error_recovery_decisions()
            if recovery:
                return {
                    "has_pending": True,
                    "is_required": True,
                    "is_error_recovery": True,
                    "has_error": True,
                    "error_message": tracker.state.last_error if tracker.state else None,
                    "skill_name": tracker.get_active_skill(),
                    "decision": recovery[0]
                }

        # Standard pending decisions
        pending = tracker.get_pending_completion_decisions()
        if not pending:
            return {"has_pending": False}

        first_pending = pending[0]
        return {
            "has_pending": True,
            "is_required": False,
            "skill_name": tracker.get_active_skill(),
            "decision": first_pending
        }

    def _detect_error_in_output(self, tool_result: str) -> Optional[str]:
        """Detect common error patterns in tool output (Issue #183).

        Returns error message if detected, None otherwise.
        """
        if not tool_result:
            return None

        # Common error patterns that indicate early completion
        error_patterns = [
            ("already closed", "Issue already closed"),
            ("already merged", "PR already merged"),
            ("not found", "Resource not found"),
            ("does not exist", "Resource does not exist"),
            ("permission denied", "Permission denied"),
            ("fatal:", "Git error"),
            ("error:", "Command error"),
            ("Error:", "Command error"),
            ("failed to", "Operation failed"),
            ("cannot ", "Operation blocked"),
        ]

        result_lower = tool_result.lower()
        for pattern, message in error_patterns:
            if pattern.lower() in result_lower:
                # Extract more context around the error
                idx = result_lower.find(pattern.lower())
                start = max(0, idx - 20)
                end = min(len(tool_result), idx + len(pattern) + 50)
                context = tool_result[start:end].strip()
                return f"{message}: {context}"

        return None

    def record_cloud_activity(self, tool_name: str, followup_agents: List[str]):
        """Record tool usage activity in PopKit Cloud for cross-project observability."""
        if not HAS_PROJECT_CLIENT:
            return

        try:
            client = ProjectClient()
            if not client.is_available:
                return

            # Extract agent name from follow-up agents (if any)
            agent_name = followup_agents[0] if followup_agents else None

            activity = ProjectActivity(
                tool_name=tool_name,
                agent_name=agent_name
            )

            client.record_activity(activity)
        except Exception:
            pass  # Silent failure - never block tool execution

    def route_workflow_response(self, tool_name: str, tool_output: Dict[str, Any]) -> Dict[str, Any]:
        """Route AskUserQuestion responses to active workflows (Issue #206).

        When a user responds to an AskUserQuestion and there's an active workflow
        waiting for a decision, this routes the response to the workflow engine
        to advance to the next step.

        Args:
            tool_name: Name of the tool that was executed
            tool_output: Output from the tool

        Returns:
            Dict with routing result and any guidance for next steps
        """
        if not WORKFLOW_ROUTER_AVAILABLE:
            return {"routed": False, "reason": "workflow_router_unavailable"}

        # Only route AskUserQuestion responses
        if not should_route_response(tool_name):
            return {"routed": False, "reason": "not_ask_user_question"}

        try:
            # Route the response to the workflow
            result = route_user_response(tool_output)

            if result.routed:
                return {
                    "routed": True,
                    "workflow_id": result.workflow_id,
                    "next_step": result.next_step,
                    "step_type": result.step_type,
                    "skill": result.skill,
                    "agent": result.agent,
                    "message": result.message,
                    "context": result.context
                }
            else:
                return {
                    "routed": False,
                    "reason": result.message or result.error,
                    "workflow_id": result.workflow_id
                }

        except Exception as e:
            return {"routed": False, "reason": f"routing_error: {e}"}

    # =========================================================================
    # Test Telemetry (Issue #226)
    # =========================================================================

    def _get_trace_sequence(self) -> int:
        """Get and increment the trace sequence number for test mode.

        Uses an environment variable to persist sequence across hook invocations.
        """
        if not is_test_mode():
            return 0

        seq_env = os.environ.get("POPKIT_TEST_TRACE_SEQ", "0")
        try:
            seq = int(seq_env)
        except ValueError:
            seq = 0

        # Increment for next call
        os.environ["POPKIT_TEST_TRACE_SEQ"] = str(seq + 1)
        return seq + 1

    def capture_tool_telemetry(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: str,
        execution_time_ms: int,
        success: bool,
        error: Optional[str] = None
    ) -> bool:
        """Capture tool trace telemetry when in test mode (Issue #226).

        This is called for every tool execution when POPKIT_TEST_MODE=true.
        Minimal overhead when not in test mode.

        Args:
            tool_name: Name of the tool executed
            tool_input: Tool input parameters
            tool_output: Tool output (may be truncated)
            execution_time_ms: Execution time in milliseconds
            success: Whether the tool succeeded
            error: Error message if failed

        Returns:
            True if telemetry was captured
        """
        if not TEST_TELEMETRY_AVAILABLE or not is_test_mode():
            return False

        try:
            trace = create_trace(
                sequence=self._trace_sequence,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=str(tool_output),
                duration_ms=execution_time_ms,
                success=success,
                error=error
            )

            return log_trace_if_test_mode(trace)
        except Exception:
            # Never block tool execution for telemetry failures
            return False

    def capture_decision_telemetry(
        self,
        question: str,
        header: str,
        options: List[Dict[str, str]],
        selected: str,
        context: str = ""
    ) -> bool:
        """Capture AskUserQuestion decision point when in test mode (Issue #226).

        Args:
            question: The question that was asked
            header: Short header/label
            options: Available options
            selected: Which option was selected
            context: Context that led to this decision

        Returns:
            True if telemetry was captured
        """
        if not TEST_TELEMETRY_AVAILABLE or not is_test_mode():
            return False

        try:
            decision = create_decision(
                question=question,
                header=header,
                options=options,
                selected=selected,
                context=context
            )

            return log_decision_if_test_mode(decision)
        except Exception:
            return False


def check_stop_reason(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check and handle Claude API stop reasons.

    Stop reasons:
    - end_turn: Normal completion
    - tool_use: Tool execution requested (expected in this context)
    - max_tokens: Response was truncated
    - stop_sequence: Custom stop sequence hit

    Returns dict with:
    - truncated: bool
    - warning: str or None
    - suggestion: str or None
    """
    result = {
        "truncated": False,
        "warning": None,
        "suggestion": None,
        "stop_reason": None
    }

    stop_reason = input_data.get("stop_reason")
    if not stop_reason:
        return result

    result["stop_reason"] = stop_reason

    if stop_reason == "max_tokens":
        result["truncated"] = True
        result["warning"] = "Response was truncated (max_tokens reached)"
        result["suggestion"] = "Output may be incomplete. Consider: retry with shorter context, or continue from last point."
    elif stop_reason == "stop_sequence":
        result["warning"] = "Custom stop sequence was hit"
    # end_turn and tool_use are normal, no warnings needed

    return result


def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        tool_name = input_data.get("tool_name", "")
        tool_args = input_data.get("tool_input", {})
        tool_result = input_data.get("tool_response", {})
        execution_time = input_data.get("execution_time", 0.0)

        # Check stop reason for truncation/issues
        stop_info = check_stop_reason(input_data)
        if stop_info["warning"]:
            print(f"⚠️  {stop_info['warning']}", file=sys.stderr)
        if stop_info["suggestion"]:
            print(f"💡 {stop_info['suggestion']}", file=sys.stderr)

        if not tool_name:
            response = {"error": "No tool_name provided in input"}
            print(json.dumps(response))
            sys.exit(1)

        hook = PostToolUseHook()
        result = hook.process_tool_completion(tool_name, tool_args, tool_result, execution_time)

        # Capture telemetry for sandbox testing (Issue #226)
        # This runs ONLY when POPKIT_TEST_MODE=true, minimal overhead otherwise
        if is_test_mode():
            success = result.get("analysis", {}).get("success", True)
            error = result.get("analysis", {}).get("issues", [])
            error_msg = error[0] if error else None

            hook.capture_tool_telemetry(
                tool_name=tool_name,
                tool_input=tool_args,
                tool_output=str(tool_result)[:10000],  # Truncate for storage
                execution_time_ms=int(execution_time * 1000),
                success=success,
                error=error_msg
            )

            # Capture decision points from AskUserQuestion
            if tool_name == "AskUserQuestion" and isinstance(tool_result, dict):
                # Extract decision info from tool args and result
                question = tool_args.get("questions", [{}])[0].get("question", "")
                header = tool_args.get("questions", [{}])[0].get("header", "")
                options = tool_args.get("questions", [{}])[0].get("options", [])
                # The selected answer comes from the tool result
                answers = tool_result.get("answers", {})
                selected = next(iter(answers.values()), "") if answers else ""

                hook.capture_decision_telemetry(
                    question=question,
                    header=header,
                    options=options,
                    selected=selected,
                    context=f"Tool execution at sequence {hook._trace_sequence}"
                )

        # Check for pending skill decisions (Issue #159, #183)
        # Pass tool_result to detect errors that should trigger required decisions
        pending_decision = hook.check_pending_skill_decisions(tool_name, tool_result)
        result["pending_skill_decision"] = pending_decision

        # Route AskUserQuestion responses to active workflows (Issue #206)
        workflow_result = hook.route_workflow_response(tool_name, tool_result)
        result["workflow_routing"] = workflow_result

        # Add stop reason info to result
        result["stop_info"] = stop_info

        # Build JSON response
        response = {
            "status": "success",
            "tool_name": tool_name,
            "session_id": result.get("session_id"),
            "analysis": result.get("analysis", {}),
            "followup_agents": result.get("followup_agents", []),
            "recommendations": result.get("recommendations", []),
            "metrics": result.get("metrics", {}),
            "stop_info": result.get("stop_info", {}),
            "workflow_routing": result.get("workflow_routing", {})
        }

        # Add truncation warning to recommendations if applicable
        if stop_info.get("truncated"):
            response["recommendations"].insert(0, stop_info["suggestion"])

        # Output analysis and recommendations to stderr for visibility
        if result["analysis"].get("issues"):
            for issue in result["analysis"]["issues"]:
                print(f"⚠️  {issue}", file=sys.stderr)

        if result["recommendations"]:
            for recommendation in result["recommendations"]:
                print(f"💡 {recommendation}", file=sys.stderr)

        if result["followup_agents"]:
            print(f"🔄 Suggested follow-up agents: {', '.join(result['followup_agents'])}", file=sys.stderr)

        # Quality score
        quality_score = result["metrics"].get("quality_score", 0.0)
        if quality_score < 0.5:
            print(f"⚡ Quality Score: {quality_score:.1f} - Consider review", file=sys.stderr)
        elif quality_score > 0.8:
            print(f"✨ Quality Score: {quality_score:.1f} - Excellent", file=sys.stderr)

        # Output pending skill decision reminder if applicable (Issue #159, #183)
        if pending_decision.get("has_pending"):
            decision = pending_decision.get("decision", {})
            skill_name = pending_decision.get("skill_name", "unknown")
            is_required = pending_decision.get("is_required", False)
            has_error = pending_decision.get("has_error", False)
            error_message = pending_decision.get("error_message")

            print(f"", file=sys.stderr)

            # Issue #183: Show error context if present
            if has_error and error_message:
                print(f"⚠️  Error detected during skill execution:", file=sys.stderr)
                print(f"   {error_message}", file=sys.stderr)
                print(f"", file=sys.stderr)

            # Issue #183: More prominent header for required decisions
            if is_required:
                print(f"🚨 REQUIRED User Decision ({skill_name})", file=sys.stderr)
                print(f"   This decision MUST be presented before continuing.", file=sys.stderr)
            else:
                print(f"🤔 User Decision Required ({skill_name})", file=sys.stderr)

            print(f"   {decision.get('question', 'No question specified')}", file=sys.stderr)
            if decision.get("options"):
                print(f"   Options:", file=sys.stderr)
                for opt in decision["options"]:
                    print(f"     • {opt.get('label')}: {opt.get('description', '')}", file=sys.stderr)
            print(f"   💡 Use AskUserQuestion tool to get user input", file=sys.stderr)
            print(f"", file=sys.stderr)

        # Output workflow routing guidance if applicable (Issue #206)
        if workflow_result.get("routed"):
            print(f"", file=sys.stderr)
            print(f"🔀 Workflow Advanced: {workflow_result.get('workflow_id')}", file=sys.stderr)
            print(f"   → Next step: {workflow_result.get('next_step')}", file=sys.stderr)

            if workflow_result.get("skill"):
                print(f"   💡 Invoke skill: {workflow_result.get('skill')}", file=sys.stderr)
            elif workflow_result.get("agent"):
                print(f"   💡 Use agent: {workflow_result.get('agent')}", file=sys.stderr)

            if workflow_result.get("message"):
                print(f"   {workflow_result.get('message')}", file=sys.stderr)
            print(f"", file=sys.stderr)

        print(f"✅ Tool {tool_name} analysis complete", file=sys.stderr)

        # Output JSON response to stdout
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"error": f"Invalid JSON input: {e}", "status": "error"}
        print(json.dumps(response))
        sys.exit(1)
    except Exception as e:
        response = {"error": str(e), "status": "error"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()