#!/usr/bin/env python3
"""
Agent Orchestrator Hook
Intelligent agent selection and task distribution based on context
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
from datetime import datetime
import hashlib

# Add utils directory to path for telemetry imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

# Import test telemetry for behavioral validation (Issue #258)
try:
    from test_telemetry import is_test_mode, emit_routing_decision, emit_agent_invocation
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    def is_test_mode(): return False
    def emit_routing_decision(*args, **kwargs): pass
    def emit_agent_invocation(*args, **kwargs): pass

class AgentOrchestrator:
    def __init__(self):
        self.claude_dir = Path.home() / '.claude'
        self.agents_dir = self.claude_dir / 'agents' / 'contains-studio'
        self.memory_db = self.claude_dir / 'OPTIMUS_MEMORY_DB.json'
        self.context_db = self.claude_dir / 'OPTIMUS_CONTEXT.db'
        
        # Load configurations
        self.agents = self.load_agents()
        self.patterns = self.load_patterns()
        self.memory = self.load_memory()
        
    def load_agents(self) -> Dict[str, Any]:
        """Load all available agents"""
        agents = {}
        
        # Categories to scan
        categories = [
            'engineering', 'operations', 'marketing', 'product',
            'design', 'orchestration', 'project-management'
        ]
        
        for category in categories:
            category_path = self.agents_dir / category
            if category_path.exists():
                for agent_file in category_path.glob('*.md'):
                    agent_name = agent_file.stem
                    agents[agent_name] = {
                        'category': category,
                        'path': str(agent_file),
                        'capabilities': self.extract_capabilities(agent_file)
                    }
        
        return agents
    
    def extract_capabilities(self, agent_file: Path) -> List[str]:
        """Extract agent capabilities from markdown file"""
        capabilities = []
        
        try:
            content = agent_file.read_text(encoding='utf-8')
            
            # Look for Primary Capabilities section
            if '## Primary Capabilities' in content:
                section = content.split('## Primary Capabilities')[1]
                section = section.split('##')[0]  # Get until next section
                
                # Extract bullet points
                for line in section.split('\n'):
                    if line.strip().startswith('-'):
                        capability = line.strip('- ').strip('*').strip()
                        if capability:
                            capabilities.append(capability.lower())
        except:
            pass
        
        return capabilities
    
    def load_patterns(self) -> Dict[str, List[str]]:
        """Load keyword patterns"""
        patterns_file = self.claude_dir / 'config' / 'keyword-patterns.json'
        if patterns_file.exists():
            with open(patterns_file, 'r') as f:
                return json.load(f)
        return {}
    
    def load_memory(self) -> Dict[str, Any]:
        """Load memory database"""
        if self.memory_db.exists():
            with open(self.memory_db, 'r') as f:
                return json.load(f)
        return {}
    
    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze user prompt to determine intent and required agents"""
        prompt_lower = prompt.lower()
        
        analysis = {
            'intent': self.detect_intent(prompt_lower),
            'complexity': self.assess_complexity(prompt),
            'domains': self.detect_domains(prompt_lower),
            'suggested_agents': [],
            'confidence': 0.0
        }
        
        # Find matching agents based on keywords
        for category, patterns in self.patterns.items():
            for agent, keywords in patterns.items():
                score = sum(1 for keyword in keywords if keyword in prompt_lower)
                if score > 0:
                    analysis['suggested_agents'].append({
                        'name': agent,
                        'category': category,
                        'score': score,
                        'reason': f"Matched {score} keywords"
                    })
        
        # Sort by score
        analysis['suggested_agents'].sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate confidence
        if analysis['suggested_agents']:
            top_score = analysis['suggested_agents'][0]['score']
            analysis['confidence'] = min(top_score / 5.0, 1.0)  # Max confidence at 5 matches
        
        return analysis
    
    def detect_intent(self, prompt: str) -> str:
        """Detect the primary intent of the prompt"""
        intents = {
            'build': ['create', 'build', 'develop', 'implement', 'make'],
            'fix': ['fix', 'debug', 'resolve', 'solve', 'repair'],
            'optimize': ['optimize', 'improve', 'enhance', 'speed up', 'refactor'],
            'analyze': ['analyze', 'review', 'examine', 'inspect', 'audit'],
            'deploy': ['deploy', 'release', 'ship', 'launch', 'rollout'],
            'document': ['document', 'write docs', 'explain', 'describe'],
            'test': ['test', 'validate', 'verify', 'check', 'ensure']
        }
        
        for intent, keywords in intents.items():
            if any(keyword in prompt for keyword in keywords):
                return intent
        
        return 'general'
    
    def assess_complexity(self, prompt: str) -> str:
        """Assess task complexity"""
        # Simple heuristics
        word_count = len(prompt.split())
        
        if word_count < 10:
            return 'simple'
        elif word_count < 50:
            return 'moderate'
        else:
            return 'complex'
    
    def detect_domains(self, prompt: str) -> List[str]:
        """Detect technical domains mentioned"""
        domains = {
            'frontend': ['react', 'vue', 'angular', 'ui', 'frontend', 'css', 'html'],
            'backend': ['api', 'server', 'database', 'backend', 'node', 'python'],
            'database': ['sql', 'postgres', 'mongodb', 'redis', 'database', 'query'],
            'devops': ['docker', 'kubernetes', 'deploy', 'ci/cd', 'pipeline'],
            'security': ['security', 'auth', 'encrypt', 'vulnerability', 'audit'],
            'performance': ['performance', 'optimize', 'speed', 'cache', 'latency']
        }
        
        detected = []
        for domain, keywords in domains.items():
            if any(keyword in prompt for keyword in keywords):
                detected.append(domain)
        
        return detected
    
    def select_agents(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Select the best agents for the task"""
        selected = []
        
        # Get top agents based on score
        for agent in analysis['suggested_agents'][:3]:  # Top 3 agents
            if agent['score'] >= 2:  # Minimum threshold
                agent_info = self.agents.get(agent['name'])
                if agent_info:
                    selected.append({
                        'name': agent['name'],
                        'category': agent['category'],
                        'confidence': agent['score'] / 5.0,
                        'parallel': self.can_run_parallel(agent['name'], selected)
                    })
        
        # If no agents matched well, suggest based on intent
        if not selected:
            selected = self.suggest_by_intent(analysis['intent'])
        
        return selected
    
    def can_run_parallel(self, agent: str, selected: List[Dict]) -> bool:
        """Determine if agent can run in parallel with selected agents"""
        # Simple rules - can be enhanced
        conflicting_pairs = [
            ('code-reviewer', 'test-writer-fixer'),  # Sequential: test then review
            ('migration-specialist', 'deployment-validator'),  # Sequential: migrate then validate
        ]
        
        for selected_agent in selected:
            for pair in conflicting_pairs:
                if agent in pair and selected_agent['name'] in pair:
                    return False
        
        return True
    
    def suggest_by_intent(self, intent: str) -> List[Dict[str, Any]]:
        """Suggest agents based on intent"""
        intent_agents = {
            'build': ['rapid-prototyper', 'code-reviewer'],
            'fix': ['bug-whisperer', 'test-writer-fixer'],
            'optimize': ['performance-optimizer', 'cache-optimizer'],
            'analyze': ['code-reviewer', 'security-auditor'],
            'deploy': ['deployment-validator', 'rollback-specialist'],
            'document': ['documentation-maintainer', 'knowledge-curator'],
            'test': ['test-writer-fixer', 'pr-reviewer']
        }
        
        agents = intent_agents.get(intent, ['workflow-optimizer-agent'])
        
        return [
            {
                'name': agent,
                'category': self.find_agent_category(agent),
                'confidence': 0.5,
                'parallel': True
            }
            for agent in agents if agent in self.agents
        ]
    
    def find_agent_category(self, agent_name: str) -> str:
        """Find category for an agent"""
        agent_info = self.agents.get(agent_name)
        return agent_info['category'] if agent_info else 'unknown'
    
    def create_orchestration_plan(self, prompt: str) -> Dict[str, Any]:
        """Create complete orchestration plan"""
        analysis = self.analyze_prompt(prompt)
        selected_agents = self.select_agents(analysis)

        # Emit routing decision telemetry (Issue #258)
        if TELEMETRY_AVAILABLE and is_test_mode():
            # Build trigger information
            trigger = {
                'type': 'intent_analysis',
                'value': analysis['intent'],
                'confidence': int(analysis['confidence'] * 100)
            }

            # Build candidate list from suggested_agents
            candidates = [
                {
                    'agent': agent['name'],
                    'score': agent['score'],
                    'matched': [analysis['intent']] + analysis.get('domains', [])
                }
                for agent in analysis.get('suggested_agents', [])[:5]  # Top 5
            ]

            # Build selected list
            selected = [agent['name'] for agent in selected_agents]

            emit_routing_decision(
                trigger=trigger,
                candidates=candidates,
                selected=selected,
                confidence=int(analysis['confidence'] * 100),
                reasoning=f"Intent: {analysis['intent']}, Complexity: {analysis['complexity']}"
            )
        
        # Group agents by execution order
        parallel_groups = []
        sequential = []
        
        for agent in selected_agents:
            if agent['parallel']:
                # Find or create parallel group
                added = False
                for group in parallel_groups:
                    if all(self.can_run_parallel(agent['name'], [a]) for a in group):
                        group.append(agent)
                        added = True
                        break
                
                if not added:
                    parallel_groups.append([agent])
            else:
                sequential.append(agent)
        
        plan = {
            'id': hashlib.md5(f"{prompt}{datetime.now()}".encode()).hexdigest()[:8],
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'analysis': analysis,
            'execution_plan': {
                'parallel_groups': parallel_groups,
                'sequential': sequential,
                'estimated_time': len(parallel_groups) * 30 + len(sequential) * 30  # seconds
            },
            'recommendations': self.generate_recommendations(analysis, selected_agents)
        }
        
        # Save to memory
        self.save_to_memory(plan)
        
        return plan
    
    def generate_recommendations(self, analysis: Dict, agents: List) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if analysis['confidence'] < 0.5:
            recommendations.append("Low confidence in agent selection. Consider being more specific.")
        
        if analysis['complexity'] == 'complex':
            recommendations.append("Complex task detected. Consider breaking it into smaller subtasks.")
        
        if len(agents) > 3:
            recommendations.append("Multiple agents needed. Execution may take longer.")
        
        if not agents:
            recommendations.append("No specific agents matched. Using general-purpose workflow optimizer.")
        
        return recommendations
    
    def save_to_memory(self, plan: Dict[str, Any]):
        """Save orchestration plan to memory"""
        try:
            # Update memory database
            if 'orchestration_history' not in self.memory:
                self.memory['orchestration_history'] = []
            
            self.memory['orchestration_history'].append({
                'id': plan['id'],
                'timestamp': plan['timestamp'],
                'prompt_summary': plan['prompt'][:100],
                'agents_used': [a['name'] for group in plan['execution_plan']['parallel_groups'] for a in group],
                'success': None  # To be updated after execution
            })
            
            # Keep only last 100 entries
            self.memory['orchestration_history'] = self.memory['orchestration_history'][-100:]
            
            # Save to file
            with open(self.memory_db, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"Error saving to memory: {e}", file=sys.stderr)
    
    def execute(self, prompt: str) -> Dict[str, Any]:
        """Main execution function"""
        plan = self.create_orchestration_plan(prompt)
        
        # Output plan for Claude Code
        output = {
            'type': 'orchestration_plan',
            'plan': plan,
            'suggested_command': self.generate_command(plan)
        }
        
        return output
    
    def generate_command(self, plan: Dict[str, Any]) -> str:
        """Generate Claude Code command for executing agents"""
        commands = []
        
        for group in plan['execution_plan']['parallel_groups']:
            if len(group) == 1:
                agent = group[0]
                commands.append(f"claude agent {agent['name']}")
            else:
                # Parallel execution
                agent_names = ' '.join(a['name'] for a in group)
                commands.append(f"claude agent --parallel {agent_names}")
        
        for agent in plan['execution_plan']['sequential']:
            commands.append(f"claude agent {agent['name']}")
        
        return ' && '.join(commands) if commands else 'claude agent workflow-optimizer-agent'


def check_stop_reason(data: Dict[str, Any]) -> Dict[str, Any]:
    """Check and handle Claude API stop reasons.

    Returns dict with truncation info and recovery suggestions.
    """
    result = {
        "truncated": False,
        "stop_reason": data.get("stop_reason"),
        "warning": None,
        "recovery_action": None
    }

    stop_reason = result["stop_reason"]
    if stop_reason == "max_tokens":
        result["truncated"] = True
        result["warning"] = "Previous response was truncated"
        result["recovery_action"] = "continue_from_checkpoint"
    elif stop_reason == "stop_sequence":
        result["warning"] = "Custom stop sequence triggered"

    return result


def main():
    """Main entry point for hook - JSON stdin/stdout protocol"""
    try:
        # Read JSON input from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Check for stop reason issues
        stop_info = check_stop_reason(data)
        if stop_info["warning"]:
            print(f"⚠️  {stop_info['warning']}", file=sys.stderr)
        if stop_info["truncated"]:
            print("💡 Consider breaking task into smaller steps", file=sys.stderr)

        # Extract prompt from JSON
        prompt = data.get("prompt", data.get("user_prompt", ""))
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # If this is a Task tool call, use the prompt from tool_input
        if tool_name == "Task":
            prompt = tool_input.get("prompt", prompt)

        if not prompt:
            response = {
                "status": "error",
                "error": "No prompt provided",
                "decision": "approve"
            }
            print(json.dumps(response))
            return 1

        orchestrator = AgentOrchestrator()
        result = orchestrator.execute(prompt)

        # Add decision field for hook protocol compliance
        result["decision"] = "approve"
        result["status"] = "success"
        result["stop_info"] = stop_info

        # If truncated, add recovery recommendation
        if stop_info["truncated"]:
            if "recommendations" not in result.get("plan", {}):
                result["plan"]["recommendations"] = []
            result["plan"]["recommendations"].insert(0, "Previous response was truncated - consider smaller task scope")

        print(json.dumps(result, indent=2))
        return 0

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}", "decision": "approve"}
        print(json.dumps(response))
        return 1
    except Exception as e:
        response = {"status": "error", "error": str(e), "decision": "approve"}
        print(json.dumps(response))
        return 1


if __name__ == '__main__':
    sys.exit(main())