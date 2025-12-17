#!/usr/bin/env python3
"""
Global User Prompt Submit Hook
Handles keyword detection, agent routing, and security filtering
Integrates with observability and orchestration systems
"""

import os
import sys
import json
import re
import hashlib
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import thinking flags parser
sys.path.insert(0, str(Path(__file__).parent / 'utils'))
try:
    from flag_parser import parse_thinking_flags
except ImportError:
    def parse_thinking_flags(args):
        """Fallback if import fails"""
        return {"force_thinking": None, "budget_tokens": 10000}

class UserPromptSubmitHook:
    def __init__(self):
        self.claude_dir = Path.home() / '.claude'
        self.config_dir = self.claude_dir / 'config'
        self.session_id = self.generate_session_id()
        self.observability_endpoint = "http://localhost:8001/events"
        self.orchestrator_endpoint = "http://localhost:8005/route"
        
        # Load configuration
        self.keyword_patterns = self.load_keyword_patterns()
        self.security_filters = self.load_security_filters()
        self.agent_registry = self.load_agent_registry()
        self.skill_triggers = self.load_skill_triggers()

        # Initialize context memory
        self.context_db = self.init_context_db()
        
    def generate_session_id(self) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def load_keyword_patterns(self) -> Dict[str, List[str]]:
        """Load keyword patterns for agent detection"""
        patterns_file = self.config_dir / 'keyword-patterns.json'
        if patterns_file.exists():
            with open(patterns_file, 'r') as f:
                return json.load(f)
        
        # Default patterns if file doesn't exist
        return {
            "engineering": {
                "ai-engineer": ["ai", "machine learning", "neural", "model", "ml", "artificial intelligence"],
                "rapid-prototyper": ["prototype", "mvp", "quick", "fast", "demo", "rapid"],
                "test-writer-fixer": ["test", "testing", "unit", "integration", "bug", "coverage"],
                "performance-optimizer": ["performance", "speed", "optimize", "slow", "latency", "bundle"],
                "security-auditor": ["security", "vulnerability", "audit", "safe", "breach", "exploit"],
                "code-reviewer": ["review", "quality", "standards", "refactor", "best practices"],
                "devops-automator": ["deploy", "pipeline", "ci/cd", "automation", "docker", "kubernetes"]
            },
            "product": {
                "feedback-synthesizer": ["feedback", "complaints", "users", "issues", "problems", "satisfaction"],
                "trend-researcher": ["trends", "viral", "popular", "market", "research", "analysis"],
                "feature-prioritizer": ["priority", "backlog", "features", "roadmap", "planning", "sprint"],
                "user-story-writer": ["story", "requirements", "specs", "documentation", "user needs"],
                "metrics-analyzer": ["metrics", "analytics", "kpi", "data", "performance", "tracking"]
            },
            "marketing": {
                "growth-hacker": ["growth", "viral", "marketing", "acquisition", "conversion", "funnel"],
                "tiktok-strategist": ["tiktok", "social", "content", "viral", "engagement", "influencer"],
                "seo-optimizer": ["seo", "search", "google", "ranking", "optimization", "keywords"],
                "brand-voice-keeper": ["brand", "voice", "messaging", "tone", "communication", "style"],
                "campaign-orchestrator": ["campaign", "marketing", "channels", "coordination", "advertising"]
            },
            "design": {
                "ui-designer": ["ui", "interface", "design", "layout", "components", "wireframe"],
                "whimsy-injector": ["whimsy", "delight", "fun", "engaging", "interactive", "creative"],
                "accessibility-guardian": ["accessibility", "a11y", "wcag", "inclusive", "disability", "screen reader"],
                "brand-consistency-enforcer": ["brand", "consistency", "design system", "guidelines", "standards"],
                "user-experience-optimizer": ["ux", "user experience", "flow", "usability", "journey", "persona"]
            },
            "project-management": {
                "sprint-master": ["sprint", "agile", "scrum", "ceremonies", "planning", "retrospective"],
                "risk-assessor": ["risk", "blocker", "dependencies", "timeline", "issues", "mitigation"],
                "stakeholder-communicator": ["stakeholder", "communication", "status", "reporting", "updates"],
                "resource-allocator": ["resources", "capacity", "allocation", "team", "workload", "bandwidth"],
                "deadline-enforcer": ["deadline", "timeline", "schedule", "delivery", "milestones", "due date"]
            },
            "operations": {
                "workflow-optimizer": ["workflow", "process", "efficiency", "optimization", "bottleneck", "streamline"],
                "documentation-maintainer": ["documentation", "docs", "knowledge", "wiki", "guide", "manual"],
                "quality-assurance-coordinator": ["qa", "quality", "testing", "validation", "standards", "compliance"],
                "environment-manager": ["environment", "deployment", "staging", "production", "infrastructure"],
                "incident-responder": ["incident", "emergency", "outage", "critical", "urgent", "downtime"]
            },
            "testing": {
                "automated-tester": ["automated", "testing", "suite", "coverage", "continuous", "regression"],
                "manual-tester": ["manual", "exploratory", "testing", "validation", "verification", "user testing"],
                "load-tester": ["load", "performance", "stress", "scalability", "capacity", "benchmark"],
                "security-tester": ["security", "penetration", "vulnerability", "exploit", "attack", "pen test"],
                "compatibility-tester": ["compatibility", "cross-platform", "browser", "device", "mobile", "responsive"]
            },
            "meta": {
                "next-action": ["popkit", "what should i", "where to go", "what now", "next steps",
                               "stuck", "unsure", "lost", "direction", "help me decide",
                               "don't know what", "what to work on", "where do i start",
                               "what's next", "recommend", "suggest"]
            }
        }
    
    def load_security_filters(self) -> List[str]:
        """Load security filters for malicious content detection"""
        return [
            r"rm\s+-rf\s+/",
            r"sudo\s+rm",
            r"format\s+c:",
            r"del\s+/s\s+/q",
            r"DROP\s+DATABASE",
            r"eval\s*\(",
            r"exec\s*\(",
            r"system\s*\(",
            r"shell_exec",
            r"passthru",
            r"curl.*\|\s*sh",
            r"wget.*\|\s*sh",
            r"\.\.\/.*\.\.\/",
            r"password\s*=\s*[\"'][^\"']+[\"']",
            r"secret\s*=\s*[\"'][^\"']+[\"']",
            r"api[_-]?key\s*=\s*[\"'][^\"']+[\"']"
        ]
    
    def load_agent_registry(self) -> Dict[str, Any]:
        """Load agent registry for capability mapping"""
        registry_file = self.config_dir / 'agent-registry.json'
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                return json.load(f)
        return {}

    def load_skill_triggers(self) -> Dict[str, Dict[str, Any]]:
        """Load skill triggers for skill awareness

        Maps keywords to skills with enforcement levels:
        - suggest: Show reminder (default)
        - require: Would block execution (for future use with skill_enforcement config)
        """
        return {
            # Debugging/Bug Fixing
            "bug": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "debug": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "error": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "broken": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "not working": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "fails": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},
            "crash": {"skill": "pop-systematic-debugging", "enforcement": "suggest"},

            # Testing
            "test": {"skill": "pop-test-driven-development", "enforcement": "suggest"},
            "testing": {"skill": "pop-test-driven-development", "enforcement": "suggest"},
            "flaky": {"skill": "pop-test-driven-development", "enforcement": "suggest"},
            "unit test": {"skill": "pop-test-driven-development", "enforcement": "suggest"},
            "integration test": {"skill": "pop-test-driven-development", "enforcement": "suggest"},
            "tdd": {"skill": "pop-test-driven-development", "enforcement": "suggest"},

            # Code Review Feedback
            "review feedback": {"skill": "pop-code-review", "enforcement": "suggest"},
            "pr comments": {"skill": "pop-code-review", "enforcement": "suggest"},
            "reviewer said": {"skill": "pop-code-review", "enforcement": "suggest"},
            "code review": {"skill": "pop-code-review", "enforcement": "suggest"},
            "requested changes": {"skill": "pop-code-review", "enforcement": "suggest"},

            # Root Cause
            "root cause": {"skill": "pop-root-cause-tracing", "enforcement": "suggest"},
            "trace": {"skill": "pop-root-cause-tracing", "enforcement": "suggest"},
            "where does": {"skill": "pop-root-cause-tracing", "enforcement": "suggest"},

            # Verification
            "verify": {"skill": "pop-verify-completion", "enforcement": "suggest"},
            "confirm": {"skill": "pop-verify-completion", "enforcement": "suggest"},
            "make sure": {"skill": "pop-verify-completion", "enforcement": "suggest"},

            # Brainstorming/Design
            "design": {"skill": "pop-brainstorming", "enforcement": "suggest"},
            "architect": {"skill": "pop-brainstorming", "enforcement": "suggest"},
            "plan": {"skill": "pop-brainstorming", "enforcement": "suggest"},
            "approach": {"skill": "pop-brainstorming", "enforcement": "suggest"},
        }

    def detect_skills(self, prompt: str) -> Dict[str, Dict[str, Any]]:
        """Detect which skills should be suggested based on keywords"""
        detected = {}
        prompt_lower = prompt.lower()

        for trigger, skill_info in self.skill_triggers.items():
            if trigger in prompt_lower:
                skill_name = skill_info["skill"]
                if skill_name not in detected:
                    detected[skill_name] = {
                        "enforcement": skill_info["enforcement"],
                        "matched_triggers": []
                    }
                detected[skill_name]["matched_triggers"].append(trigger)

        return detected

    def init_context_db(self) -> sqlite3.Connection:
        """Initialize context memory database"""
        db_path = self.config_dir / 'context-memory.db'
        conn = sqlite3.connect(str(db_path))
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS context_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                detected_agents TEXT,
                context_keywords TEXT,
                project_context TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_timestamp 
            ON context_memory(session_id, timestamp)
        ''')
        
        conn.commit()
        return conn
    
    def detect_security_issues(self, prompt: str) -> List[str]:
        """Detect potential security issues in user prompt"""
        issues = []
        prompt_lower = prompt.lower()
        
        for pattern in self.security_filters:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append(f"Potential security risk: {pattern}")
        
        return issues
    
    def detect_agents(self, prompt: str) -> Dict[str, List[str]]:
        """Detect which agents should be activated based on keywords"""
        detected = {}
        prompt_lower = prompt.lower()
        
        for category, agents in self.keyword_patterns.items():
            for agent_name, keywords in agents.items():
                matches = []
                for keyword in keywords:
                    if keyword.lower() in prompt_lower:
                        matches.append(keyword)
                
                if matches:
                    if category not in detected:
                        detected[category] = {}
                    detected[category][agent_name] = matches
        
        return detected
    
    def get_project_context(self) -> Dict[str, Any]:
        """Get current project context"""
        cwd = os.getcwd()
        context = {
            "working_directory": cwd,
            "project_name": Path(cwd).name,
            "has_package_json": os.path.exists(os.path.join(cwd, "package.json")),
            "has_claude_md": os.path.exists(os.path.join(cwd, "CLAUDE.md")),
            "has_local_claude": os.path.exists(os.path.join(cwd, ".claude")),
            "git_repository": os.path.exists(os.path.join(cwd, ".git"))
        }
        
        # Load local CLAUDE.md if exists
        claude_md_path = os.path.join(cwd, "CLAUDE.md")
        if os.path.exists(claude_md_path):
            try:
                with open(claude_md_path, 'r', encoding='utf-8') as f:
                    context["claude_md_content"] = f.read()[:1000]  # First 1000 chars
            except Exception:
                pass
        
        return context
    
    def store_context(self, prompt: str, detected_agents: Dict, project_context: Dict):
        """Store interaction context in memory database"""
        try:
            self.context_db.execute('''
                INSERT INTO context_memory 
                (session_id, timestamp, user_prompt, detected_agents, context_keywords, project_context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                datetime.now().isoformat(),
                prompt,
                json.dumps(detected_agents),
                json.dumps(self.extract_keywords(prompt)),
                json.dumps(project_context)
            ))
            self.context_db.commit()
        except Exception as e:
            print(f"Warning: Could not store context: {e}", file=sys.stderr)
    
    def extract_keywords(self, prompt: str) -> List[str]:
        """Extract important keywords from prompt"""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w{3,}\b', prompt.lower())
        
        # Filter out common words
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        keywords = [word for word in words if word not in stopwords]
        return list(set(keywords))  # Remove duplicates
    
    def log_event(self, event_data: Dict[str, Any]):
        """Log event to observability system"""
        try:
            response = requests.post(
                self.observability_endpoint,
                json=event_data,
                timeout=2
            )
            if response.status_code != 200:
                print(f"Warning: Observability logging failed: {response.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not log to observability system: {e}", file=sys.stderr)
    
    def route_to_orchestrator(self, prompt: str, detected_agents: Dict, project_context: Dict) -> Optional[Dict]:
        """Send routing request to orchestrator"""
        try:
            routing_data = {
                "session_id": self.session_id,
                "user_prompt": prompt,
                "detected_agents": detected_agents,
                "project_context": project_context,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                self.orchestrator_endpoint,
                json=routing_data,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Warning: Orchestrator routing failed: {response.status_code}", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Could not connect to orchestrator: {e}", file=sys.stderr)
        
        return None
    
    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """Main processing function for user prompts"""
        # Security check
        security_issues = self.detect_security_issues(prompt)
        if security_issues:
            return {
                "action": "block",
                "reason": "Security violation detected",
                "issues": security_issues,
                "session_id": self.session_id
            }

        # Parse thinking flags (-T, --thinking, --no-thinking)
        thinking_flags = parse_thinking_flags(prompt)

        # Agent detection
        detected_agents = self.detect_agents(prompt)

        # Skill detection (for skill awareness reminders)
        detected_skills = self.detect_skills(prompt)

        # Project context
        project_context = self.get_project_context()

        # Store context
        self.store_context(prompt, detected_agents, project_context)
        
        # Log to observability
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "sessionId": self.session_id,
            "eventType": "user_prompt_submit",
            "hookType": "user_prompt_submit",
            "userPrompt": prompt,
            "metadata": {
                "detected_agents": detected_agents,
                "project_context": project_context,
                "security_check": "passed"
            }
        }
        self.log_event(event_data)
        
        # Route to orchestrator
        orchestration_result = self.route_to_orchestrator(prompt, detected_agents, project_context)
        
        return {
            "action": "continue",
            "session_id": self.session_id,
            "detected_agents": detected_agents,
            "detected_skills": detected_skills,
            "thinking_flags": thinking_flags,
            "project_context": project_context,
            "orchestration_result": orchestration_result,
            "enhanced_prompt": self.enhance_prompt(prompt, detected_agents, detected_skills, project_context, thinking_flags)
        }
    
    def enhance_prompt(self, original_prompt: str, detected_agents: Dict, detected_skills: Dict, project_context: Dict, thinking_flags: Dict = None) -> str:
        """Enhance prompt with context, skill reminders, thinking mode, and agent routing information"""
        enhancements = []
        suggestions = []
        skill_reminders = []
        thinking_flags = thinking_flags or {}

        # Handle extended thinking flag
        if thinking_flags.get("force_thinking") is True:
            budget = thinking_flags.get("budget_tokens", 10000)
            enhancements.append(f"Extended thinking mode enabled (budget: {budget} tokens)")

        # Check for uncertainty/meta triggers
        if "meta" in detected_agents and "next-action" in detected_agents.get("meta", {}):
            suggestions.append("Try `/popkit:next` for context-aware recommendations")

        # Add skill reminders based on detected skills
        skill_descriptions = {
            "pop-systematic-debugging": "bug investigation (4-phase root cause analysis)",
            "pop-test-driven-development": "test-first approach (RED-GREEN-REFACTOR)",
            "pop-code-review": "code review (giving or receiving feedback)",
            "pop-root-cause-tracing": "tracing data flow to find bug origin",
            "pop-verify-completion": "evidence-based verification before claiming done",
            "pop-brainstorming": "design refinement through Socratic questioning",
        }

        for skill_name, skill_info in detected_skills.items():
            description = skill_descriptions.get(skill_name, skill_name)
            skill_reminders.append(f"/skill:{skill_name} - {description}")

        # Add project context
        if project_context.get("has_claude_md"):
            enhancements.append("Local CLAUDE.md context available")

        if project_context.get("git_repository"):
            enhancements.append("Git repository detected")

        # Add agent routing info
        if detected_agents:
            # Count agents excluding meta category
            agent_count = sum(len(agents) for cat, agents in detected_agents.items() if cat != "meta")
            if agent_count > 0:
                enhancements.append(f"{agent_count} specialized agents detected")

        result = original_prompt

        # Add extended thinking instruction if -T flag was used
        if thinking_flags.get("force_thinking") is True:
            result = f"{result}\n\n<!-- THINKING MODE: Extended thinking enabled. Take time to reason through this step by step, exploring the problem space thoroughly before responding. -->"

        # Add skill reminders as HTML comments (visible to Claude but not disruptive)
        if skill_reminders:
            skill_text = "\n".join(f"  - {r}" for r in skill_reminders)
            result = f"{result}\n\n<!-- SKILL REMINDER: Based on your request, consider using:\n{skill_text}\n-->"

        if suggestions:
            suggestion_text = " | ".join(suggestions)
            result = f"{result}\n\n<!-- Suggestion: {suggestion_text} -->"

        if enhancements:
            enhancement_text = " | ".join(enhancements)
            result = f"{result}\n\n<!-- System Context: {enhancement_text} -->"

        return result

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        user_prompt = input_data.get("prompt", input_data.get("user_prompt", ""))

        if not user_prompt:
            response = {"error": "No prompt provided in input", "decision": "block"}
            print(json.dumps(response))
            sys.exit(1)

        hook = UserPromptSubmitHook()
        result = hook.process_prompt(user_prompt)

        # Build JSON response
        response = {
            "decision": "approve" if result["action"] != "block" else "block",
            "reason": None,
            "session_id": result.get("session_id"),
            "detected_agents": result.get("detected_agents", {}),
            "detected_skills": result.get("detected_skills", {}),
            "thinking_flags": result.get("thinking_flags", {}),
            "project_context": result.get("project_context", {}),
            "enhanced_prompt": result.get("enhanced_prompt", user_prompt)
        }

        if result["action"] == "block":
            response["reason"] = result.get("reason", "Security violation")
            response["issues"] = result.get("issues", [])
            print(f"🚫 Security Alert: {result['reason']}", file=sys.stderr)
            for issue in result.get("issues", []):
                print(f"   - {issue}", file=sys.stderr)
        else:
            # Show thinking mode if enabled
            thinking_flags = result.get("thinking_flags", {})
            if thinking_flags.get("force_thinking") is True:
                budget = thinking_flags.get("budget_tokens", 10000)
                print(f"🧠 Extended thinking mode enabled (budget: {budget} tokens)", file=sys.stderr)

            # Debug information to stderr
            if result.get("detected_skills"):
                skill_names = list(result["detected_skills"].keys())
                print(f"📚 Skills suggested: {', '.join(skill_names)}", file=sys.stderr)

            if result.get("detected_agents"):
                agent_summary = []
                for category, agents in result["detected_agents"].items():
                    agent_summary.append(f"{category}: {', '.join(agents.keys())}")
                print(f"🎯 Agents activated: {' | '.join(agent_summary)}", file=sys.stderr)

        # Output JSON response to stdout
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"error": f"Invalid JSON input: {e}", "decision": "approve"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on JSON errors
    except Exception as e:
        response = {"error": str(e), "decision": "approve"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()