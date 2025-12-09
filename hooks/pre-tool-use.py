#!/usr/bin/env python3
"""
Global Pre-Tool-Use Hook
Safety checks, agent coordination, and orchestration before tool execution
Prevents dangerous operations and coordinates multi-agent workflows
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

class PreToolUseHook:
    def __init__(self):
        self.claude_dir = Path.home() / '.claude'
        self.config_dir = self.claude_dir / 'config'
        self.session_id = self.get_session_id()
        self.observability_endpoint = "http://localhost:8001/events"
        self.orchestrator_endpoint = "http://localhost:8005/coordinate"
        
        # Load configuration
        self.safety_rules = self.load_safety_rules()
        self.coordination_rules = self.load_coordination_rules()
        self.tool_permissions = self.load_tool_permissions()
        
        # Initialize context database
        self.context_db = self.init_context_db()
        
    def get_session_id(self) -> str:
        """Get current session ID from environment or generate new one"""
        session_id = os.environ.get('CLAUDE_SESSION_ID')
        if not session_id:
            # Try to get from recent context
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
    
    def load_safety_rules(self) -> Dict[str, List[str]]:
        """Load safety rules for dangerous operations"""
        return {
            "blocked_commands": [
                r"rm\s+-rf\s+/",
                r"sudo\s+rm\s+-rf",
                r"format\s+c:",
                r"del\s+/s\s+/q\s+c:",
                r"DROP\s+DATABASE",
                r"TRUNCATE\s+TABLE",
                r"chmod\s+777",
                r"chown\s+root",
                r"dd\s+if=/dev/zero",
                r":(){ :|:& };:",  # Fork bomb
            ],
            "sensitive_paths": [
                r"\/etc\/passwd",
                r"\/etc\/shadow",
                r"\/root\/",
                r"\/boot\/",
                r"C:\\Windows\\System32",
                r"C:\\Program Files",
                r"\.ssh\/id_rsa",
                r"\.aws\/credentials",
                r"\.env",
            ],
            "dangerous_tools": [
                "Bash:rm -rf",
                "Bash:sudo",
                "Bash:chmod 777",
                "Write:/etc/",
                "Write:/root/",
                "Edit:/etc/",
            ]
        }
    
    def load_coordination_rules(self) -> Dict[str, Any]:
        """Load agent coordination and conflict resolution rules"""
        return {
            "tool_conflicts": {
                "Edit": ["Write", "MultiEdit"],
                "Write": ["Edit", "MultiEdit"],
                "MultiEdit": ["Edit", "Write"]
            },
            "agent_priorities": {
                "security": ["security-auditor", "security-tester"],
                "performance": ["performance-optimizer", "load-tester", "performance-profiler"],
                "quality": ["code-reviewer", "quality-assurance-coordinator"],
                "testing": ["automated-tester", "manual-tester", "compatibility-tester"]
            },
            "sequential_operations": [
                ["security-auditor", "code-reviewer"],
                ["test-writer-fixer", "automated-tester"],
                ["ui-designer", "accessibility-guardian"]
            ],
            "parallel_operations": [
                ["performance-optimizer", "seo-optimizer"],
                ["growth-hacker", "tiktok-strategist"],
                ["feedback-synthesizer", "trend-researcher"]
            ]
        }
    
    def load_tool_permissions(self) -> Dict[str, Dict[str, Any]]:
        """Load tool permission matrix by context"""
        return {
            "production": {
                "allowed_tools": ["Read", "Grep", "Glob", "LS", "WebFetch"],
                "restricted_tools": ["Write", "Edit", "MultiEdit", "Bash"],
                "requires_confirmation": ["Write", "Edit", "MultiEdit"]
            },
            "development": {
                "allowed_tools": ["Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "LS", "Bash", "WebFetch"],
                "restricted_tools": [],
                "requires_confirmation": ["Bash:rm", "Bash:sudo", "Write:/"]
            },
            "testing": {
                "allowed_tools": ["Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "LS", "Bash", "WebFetch"],
                "restricted_tools": ["Bash:rm -rf", "Write:/etc/"],
                "requires_confirmation": ["Bash", "Write"]
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
    
    def detect_environment_context(self) -> str:
        """Detect current environment context (production, development, testing)"""
        cwd = os.getcwd()
        
        # Check for production indicators
        if any(indicator in cwd.lower() for indicator in ['prod', 'production', 'live', 'deploy']):
            return "production"
        
        # Check for testing indicators
        if any(indicator in cwd.lower() for indicator in ['test', 'testing', 'spec', 'qa']):
            return "testing"
        
        # Check for development indicators or default
        return "development"
    
    def check_safety_violations(self, tool_name: str, tool_args: Dict[str, Any]) -> List[str]:
        """Check for safety violations in tool usage"""
        violations = []
        
        # Check blocked commands for Bash tool
        if tool_name == "Bash" and "command" in tool_args:
            command = tool_args["command"]
            for blocked_pattern in self.safety_rules["blocked_commands"]:
                if re.search(blocked_pattern, command, re.IGNORECASE):
                    violations.append(f"Blocked dangerous command: {blocked_pattern}")
        
        # Check sensitive paths for file operations
        if tool_name in ["Write", "Edit", "MultiEdit"] and "file_path" in tool_args:
            file_path = tool_args["file_path"]
            for sensitive_pattern in self.safety_rules["sensitive_paths"]:
                if re.search(sensitive_pattern, file_path, re.IGNORECASE):
                    violations.append(f"Access to sensitive path blocked: {sensitive_pattern}")
        
        # Check dangerous tool combinations
        tool_signature = f"{tool_name}:{tool_args.get('command', tool_args.get('file_path', ''))}"
        for dangerous_tool in self.safety_rules["dangerous_tools"]:
            if dangerous_tool in tool_signature:
                violations.append(f"Dangerous tool usage blocked: {dangerous_tool}")
        
        return violations
    
    def check_permission_requirements(self, tool_name: str, tool_args: Dict[str, Any], context: str) -> Tuple[bool, List[str]]:
        """Check if tool usage requires special permissions or confirmation"""
        permissions = self.tool_permissions.get(context, self.tool_permissions["development"])
        warnings = []
        
        # Check if tool is allowed
        if tool_name not in permissions["allowed_tools"] and tool_name in permissions["restricted_tools"]:
            return False, [f"Tool {tool_name} is restricted in {context} environment"]
        
        # Check if confirmation is required
        tool_signature = f"{tool_name}:{tool_args.get('command', tool_args.get('file_path', ''))}"
        for confirmation_pattern in permissions["requires_confirmation"]:
            if confirmation_pattern in tool_signature:
                warnings.append(f"Tool {tool_name} requires confirmation in {context} environment")
        
        return True, warnings
    
    def coordinate_with_agents(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate tool usage with active agents"""
        coordination_result = {
            "conflicts": [],
            "recommendations": [],
            "agent_handoffs": [],
            "sequential_requirements": []
        }
        
        # Check for tool conflicts
        if tool_name in self.coordination_rules["tool_conflicts"]:
            conflicting_tools = self.coordination_rules["tool_conflicts"][tool_name]
            coordination_result["conflicts"] = [
                f"Tool {tool_name} conflicts with: {', '.join(conflicting_tools)}"
            ]
        
        # Get agent recommendations based on tool usage
        if tool_name == "Write" and "file_path" in tool_args:
            file_path = tool_args["file_path"]
            if file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                coordination_result["recommendations"].append("Consider running code-reviewer after file modifications")
            if file_path.endswith(('.test.ts', '.spec.ts')):
                coordination_result["recommendations"].append("Consider running automated-tester after test file changes")
        
        # Check for required sequential operations
        for sequence in self.coordination_rules["sequential_operations"]:
            if len(sequence) > 1:
                coordination_result["sequential_requirements"].append(
                    f"After completion, consider: {' → '.join(sequence[1:])}"
                )
        
        return coordination_result
    
    def log_pre_tool_event(self, tool_name: str, tool_args: Dict[str, Any], safety_check: Dict[str, Any]):
        """Log pre-tool-use event to observability system"""
        try:
            event_data = {
                "timestamp": datetime.now().isoformat(),
                "sessionId": self.session_id,
                "eventType": "pre_tool_use",
                "hookType": "pre_tool_use",
                "toolName": tool_name,
                "toolArgs": tool_args,
                "metadata": {
                    "safety_check": safety_check,
                    "environment_context": self.detect_environment_context(),
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
                
        except Exception as e:
            print(f"Warning: Could not log to observability system: {e}", file=sys.stderr)
    
    def request_orchestration(self, tool_name: str, tool_args: Dict[str, Any], coordination: Dict[str, Any]) -> Optional[Dict]:
        """Request orchestration guidance from orchestrator service"""
        try:
            orchestration_data = {
                "session_id": self.session_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "coordination_analysis": coordination,
                "environment_context": self.detect_environment_context(),
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
                print(f"Warning: Orchestration request failed: {response.status_code}", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Could not connect to orchestrator: {e}", file=sys.stderr)
        
        return None
    
    def get_recent_context(self) -> Dict[str, Any]:
        """Get recent context from previous interactions"""
        context = {"recent_tools": [], "recent_agents": [], "project_context": {}}
        
        if not self.context_db:
            return context
        
        try:
            # Get recent tool usage
            cursor = self.context_db.execute("""
                SELECT tool_name, COUNT(*) as usage_count 
                FROM pre_tool_events 
                WHERE session_id = ? AND timestamp > datetime('now', '-1 hour')
                GROUP BY tool_name 
                ORDER BY usage_count DESC 
                LIMIT 5
            """, (self.session_id,))
            
            context["recent_tools"] = [{"tool": row[0], "count": row[1]} for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"Warning: Could not retrieve recent context: {e}", file=sys.stderr)
        
        return context
    
    def store_pre_tool_context(self, tool_name: str, tool_args: Dict[str, Any], safety_result: Dict[str, Any]):
        """Store pre-tool context for future reference"""
        if not self.context_db:
            return
        
        try:
            # Create table if it doesn't exist
            self.context_db.execute('''
                CREATE TABLE IF NOT EXISTS pre_tool_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_args TEXT,
                    safety_result TEXT,
                    environment_context TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert current event
            self.context_db.execute('''
                INSERT INTO pre_tool_events 
                (session_id, timestamp, tool_name, tool_args, safety_result, environment_context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                datetime.now().isoformat(),
                tool_name,
                json.dumps(tool_args),
                json.dumps(safety_result),
                self.detect_environment_context()
            ))
            
            self.context_db.commit()
            
        except Exception as e:
            print(f"Warning: Could not store pre-tool context: {e}", file=sys.stderr)
    
    def process_tool_request(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing function for tool requests"""
        result = {
            "action": "continue",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "session_id": self.session_id,
            "safety_check": {"passed": True, "violations": []},
            "coordination": {},
            "warnings": [],
            "recommendations": []
        }
        
        # Environment context detection
        environment_context = self.detect_environment_context()
        
        # Safety checks
        safety_violations = self.check_safety_violations(tool_name, tool_args)
        if safety_violations:
            result["action"] = "block"
            result["safety_check"] = {"passed": False, "violations": safety_violations}
            return result
        
        # Permission checks
        permission_allowed, permission_warnings = self.check_permission_requirements(
            tool_name, tool_args, environment_context
        )
        if not permission_allowed:
            result["action"] = "block"
            result["safety_check"] = {"passed": False, "violations": permission_warnings}
            return result
        
        result["warnings"].extend(permission_warnings)
        
        # Agent coordination
        coordination = self.coordinate_with_agents(tool_name, tool_args)
        result["coordination"] = coordination
        result["recommendations"].extend(coordination.get("recommendations", []))
        
        # Orchestration request
        orchestration_result = self.request_orchestration(tool_name, tool_args, coordination)
        if orchestration_result:
            result["orchestration"] = orchestration_result
            if orchestration_result.get("action") == "modify":
                result["tool_args"] = orchestration_result.get("modified_args", tool_args)
        
        # Get recent context
        result["recent_context"] = self.get_recent_context()
        
        # Log event
        self.log_pre_tool_event(tool_name, tool_args, result["safety_check"])
        
        # Store context
        self.store_pre_tool_context(tool_name, tool_args, result)
        
        return result

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        tool_name = input_data.get("tool_name", "")
        tool_args = input_data.get("tool_input", {})

        if not tool_name:
            response = {"error": "No tool_name provided in input"}
            print(json.dumps(response))
            sys.exit(1)

        hook = PreToolUseHook()
        result = hook.process_tool_request(tool_name, tool_args)

        # Build JSON response
        response = {
            "decision": "allow" if result["action"] != "block" else "block",
            "reason": None,
            "tool_name": tool_name,
            "session_id": result.get("session_id"),
            "warnings": result.get("warnings", []),
            "recommendations": result.get("recommendations", [])
        }

        if result["action"] == "block":
            response["reason"] = "; ".join(result["safety_check"]["violations"])
            print(f"🚫 Tool execution blocked: {tool_name}", file=sys.stderr)
            for violation in result["safety_check"]["violations"]:
                print(f"   - {violation}", file=sys.stderr)
        else:
            # Output warnings and recommendations to stderr for visibility
            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"⚠️  {warning}", file=sys.stderr)

            if result["recommendations"]:
                for recommendation in result["recommendations"]:
                    print(f"💡 {recommendation}", file=sys.stderr)

            if result["coordination"].get("conflicts"):
                for conflict in result["coordination"]["conflicts"]:
                    print(f"🔄 {conflict}", file=sys.stderr)

            print(f"✅ Tool {tool_name} approved for execution", file=sys.stderr)

        # Output JSON response to stdout
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"error": f"Invalid JSON input: {e}", "decision": "block"}
        print(json.dumps(response))
        sys.exit(1)
    except Exception as e:
        response = {"error": str(e), "decision": "allow"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()