#!/usr/bin/env python3
"""
Agent Context Integration Hook
Integrates project-aware agent loading into Claude Code's agent system.
This hook intercepts agent loading requests and adds project context.

DEPRECATED: This hook is disabled (removed from hooks.json) because:
1. It imports agent_context_loader.py which does not exist
2. The functionality is already provided by semantic_router.py
3. It was silently failing on every Task tool call

See Issue #204 for details. If you need project-aware agent routing,
use semantic_router.py instead.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our context loading system
config_dir = Path.home() / ".claude" / "config"
sys.path.insert(0, str(config_dir))

try:
    from agent_context_loader import agent_context_loader, load_agent, get_agents, recommend_agents, get_project_info
    CONTEXT_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent context system not available: {e}")
    CONTEXT_SYSTEM_AVAILABLE = False

def enhance_agent_loading(agent_name: str, working_directory: str = None) -> dict:
    """
    Enhance agent loading with project context
    This function is called by Claude Code when loading agents
    """
    if not CONTEXT_SYSTEM_AVAILABLE:
        logger.warning("Context system unavailable, falling back to default agent loading")
        return {}
    
    try:
        # Use our context loader to get enhanced agent
        enhanced_agent = load_agent(agent_name, working_directory)
        
        if enhanced_agent:
            logger.info(f"Successfully enhanced agent '{agent_name}' with project context")
            
            # Add metadata about the enhancement
            enhanced_agent['_context_enhanced'] = True
            enhanced_agent['_enhancement_timestamp'] = str(Path().cwd())
            
            return enhanced_agent
        else:
            logger.warning(f"Could not enhance agent '{agent_name}' - not found")
            return {}
            
    except Exception as e:
        logger.error(f"Error enhancing agent '{agent_name}': {e}")
        return {}

def get_agent_suggestions(user_input: str, working_directory: str = None) -> list:
    """
    Get intelligent agent suggestions based on user input
    This helps with automatic agent selection
    """
    if not CONTEXT_SYSTEM_AVAILABLE:
        return []
    
    try:
        recommendations = recommend_agents(user_input, working_directory)
        
        # Format recommendations for Claude Code
        suggestions = []
        for rec in recommendations:
            agent = rec['agent']
            suggestions.append({
                'name': agent.get('name'),
                'score': rec['score'],
                'reasons': rec['reasons'],
                'description': agent.get('description', ''),
                'is_project_specific': agent.get('project_specific', False),
                'is_enhanced': 'project_context' in agent
            })
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting agent suggestions: {e}")
        return []

def get_context_status(working_directory: str = None) -> dict:
    """
    Get current project context status for debugging and user info
    """
    if not CONTEXT_SYSTEM_AVAILABLE:
        return {'status': 'unavailable', 'reason': 'Context system not loaded'}
    
    try:
        status = get_project_info(working_directory)
        return {
            'status': 'available',
            'project_detected': status['detected_project'] is not None,
            'project_info': status['detected_project'],
            'has_overrides': status['has_overrides'],
            'has_custom_agents': status['has_custom_agents'],
            'available_overrides': status['available_overrides'],
            'available_custom_agents': status['available_custom_agents']
        }
        
    except Exception as e:
        logger.error(f"Error getting context status: {e}")
        return {'status': 'error', 'error': str(e)}

def list_all_agents(working_directory: str = None) -> dict:
    """
    List all available agents with project context awareness
    """
    if not CONTEXT_SYSTEM_AVAILABLE:
        return {'global': [], 'project_specific': [], 'enhanced_global': []}
    
    try:
        agents = get_agents(working_directory)
        
        # Add metadata for UI display
        for category, agent_list in agents.items():
            for agent in agent_list:
                agent['_category'] = category
                agent['_has_project_context'] = 'project_context' in agent
        
        return agents
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {'global': [], 'project_specific': [], 'enhanced_global': []}

# Main hook function - this is called by Claude Code
def on_agent_request(event_data: dict) -> dict:
    """
    Main hook function called by Claude Code for agent-related requests
    """
    event_type = event_data.get('type')
    working_dir = event_data.get('working_directory', os.getcwd())
    
    if event_type == 'load_agent':
        agent_name = event_data.get('agent_name')
        return enhance_agent_loading(agent_name, working_dir)
    
    elif event_type == 'suggest_agents':
        user_input = event_data.get('user_input', '')
        return {'suggestions': get_agent_suggestions(user_input, working_dir)}
    
    elif event_type == 'list_agents':
        return list_all_agents(working_dir)
    
    elif event_type == 'context_status':
        return get_context_status(working_dir)
    
    else:
        logger.warning(f"Unknown event type: {event_type}")
        return {}

# Main entry point - JSON stdin/stdout protocol
if __name__ == "__main__":
    try:
        # Read JSON input from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Extract event data
        event_type = data.get("type", data.get("event_type", "context_status"))
        working_dir = data.get("working_directory", os.getcwd())

        # Route to appropriate handler
        if event_type == "load_agent":
            agent_name = data.get("agent_name", data.get("tool_input", {}).get("agent_name", ""))
            result = enhance_agent_loading(agent_name, working_dir)
            response = {
                "status": "success" if result else "error",
                "agent": result,
                "enhanced": result.get("_context_enhanced", False) if result else False
            }
        elif event_type == "suggest_agents":
            user_input = data.get("user_input", data.get("prompt", ""))
            suggestions = get_agent_suggestions(user_input, working_dir)
            response = {
                "status": "success",
                "suggestions": suggestions
            }
        elif event_type == "list_agents":
            agents = list_all_agents(working_dir)
            response = {
                "status": "success",
                "agents": agents
            }
        else:  # context_status or default
            status = get_context_status(working_dir)
            response = {
                "status": "success",
                "context": status
            }

        response["system_available"] = CONTEXT_SYSTEM_AVAILABLE
        print(json.dumps(response, indent=2))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors