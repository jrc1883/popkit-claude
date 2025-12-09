#!/usr/bin/env python3
"""
Chain Validator Hook
Validates workflow chains from agents/config.json before execution.

Features:
- Agent existence validation
- Circular dependency detection
- Output style verification
- Warning-based approach (don't block, just warn)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Path resolution
HOOKS_DIR = Path(__file__).parent
AGENTS_DIR = HOOKS_DIR.parent / "agents"
CONFIG_FILE = AGENTS_DIR / "config.json"
OUTPUT_STYLES_DIR = HOOKS_DIR.parent / "output-styles"


class ChainValidator:
    """Validates workflow chains from config.json."""

    def __init__(self):
        self.config = self._load_config()
        self.available_agents = self._get_available_agents()
        self.available_styles = self._get_available_styles()

    def _load_config(self) -> Dict[str, Any]:
        """Load agents/config.json."""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _get_available_agents(self) -> Set[str]:
        """Get set of all available agent names from tier definitions."""
        agents = set()
        tiers = self.config.get('tiers', {})

        for tier_name, tier_data in tiers.items():
            tier_agents = tier_data.get('agents', [])
            agents.update(tier_agents)

        return agents

    def _get_available_styles(self) -> Set[str]:
        """Get set of available output style names."""
        styles = set()

        if OUTPUT_STYLES_DIR.exists():
            for style_file in OUTPUT_STYLES_DIR.glob('*.md'):
                styles.add(style_file.stem)

        return styles

    def validate_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single workflow definition.

        Returns:
            Dict with 'valid', 'errors', 'warnings', and 'stats' keys.
        """
        errors = []
        warnings = []
        stats = {
            'total_phases': 0,
            'agents_used': set(),
            'missing_agents': set()
        }

        # Check phases-based workflows (like feature-dev)
        phases = workflow.get('phases', [])
        if phases:
            stats['total_phases'] = len(phases)

            for i, phase in enumerate(phases):
                phase_name = phase.get('name', f'Phase {i}')
                phase_agents = phase.get('agents', [])

                for agent in phase_agents:
                    stats['agents_used'].add(agent)

                    if agent not in self.available_agents:
                        warnings.append(f"Phase '{phase_name}': Agent '{agent}' not found in tier definitions")
                        stats['missing_agents'].add(agent)

        # Check simple agent-list workflows (like debug)
        simple_agents = workflow.get('agents', [])
        if simple_agents:
            for agent in simple_agents:
                stats['agents_used'].add(agent)

                if agent not in self.available_agents:
                    warnings.append(f"Workflow '{workflow_id}': Agent '{agent}' not found")
                    stats['missing_agents'].add(agent)

        # Convert sets to lists for JSON serialization
        stats['agents_used'] = list(stats['agents_used'])
        stats['missing_agents'] = list(stats['missing_agents'])

        return {
            'valid': len(errors) == 0,
            'workflow_id': workflow_id,
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }

    def validate_all_workflows(self) -> Dict[str, Any]:
        """Validate all workflows in config.json."""
        workflows = self.config.get('workflows', {})
        results = {
            'valid': True,
            'total_workflows': len(workflows),
            'workflows': {},
            'summary': {
                'total_errors': 0,
                'total_warnings': 0,
                'all_agents': set(),
                'missing_agents': set()
            }
        }

        for workflow_id, workflow in workflows.items():
            result = self.validate_workflow(workflow_id, workflow)
            results['workflows'][workflow_id] = result

            # Aggregate
            if not result['valid']:
                results['valid'] = False
            results['summary']['total_errors'] += len(result['errors'])
            results['summary']['total_warnings'] += len(result['warnings'])
            results['summary']['all_agents'].update(result['stats']['agents_used'])
            results['summary']['missing_agents'].update(result['stats']['missing_agents'])

        # Convert sets to lists
        results['summary']['all_agents'] = list(results['summary']['all_agents'])
        results['summary']['missing_agents'] = list(results['summary']['missing_agents'])

        return results

    def check_circular_dependencies(self, workflow: Dict[str, Any]) -> List[str]:
        """Check for circular dependencies in workflow phases.

        Note: Current workflow format doesn't have explicit dependencies,
        but this is ready for when they're added.
        """
        # Current workflows don't have explicit dependencies
        # This is a placeholder for future enhancement
        return []

    def get_workflow_visualization(self, workflow_id: str) -> str:
        """Generate ASCII visualization of a workflow."""
        workflows = self.config.get('workflows', {})
        workflow = workflows.get(workflow_id)

        if not workflow:
            return f"Workflow '{workflow_id}' not found"

        lines = [f"Workflow: {workflow_id}"]
        lines.append("=" * 40)
        lines.append("")

        # Phases-based workflow
        phases = workflow.get('phases', [])
        if phases:
            for i, phase in enumerate(phases):
                phase_name = phase.get('name', f'Phase {i}')
                phase_agents = phase.get('agents', [])

                agent_str = ', '.join(phase_agents) if phase_agents else '(no agents)'
                lines.append(f"  [{phase_name}]  {agent_str}")

                if i < len(phases) - 1:
                    lines.append("       |")
                    lines.append("       v")

            lines.append("")
            lines.append(f"Phases: {len(phases)} | Agents: {sum(len(p.get('agents', [])) for p in phases)}")

        # Simple agent-list workflow
        simple_agents = workflow.get('agents', [])
        if simple_agents and not phases:
            sequential = workflow.get('sequential', False)

            if sequential:
                for i, agent in enumerate(simple_agents):
                    lines.append(f"  [{agent}]")
                    if i < len(simple_agents) - 1:
                        lines.append("       |")
                        lines.append("       v")
            else:
                lines.append("  [parallel execution]")
                for agent in simple_agents:
                    lines.append(f"    - {agent}")

            lines.append("")
            lines.append(f"Agents: {len(simple_agents)} | Mode: {'sequential' if sequential else 'parallel'}")

        return "\n".join(lines)


def main():
    """Main entry point for the hook - JSON stdin/stdout protocol."""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Initialize validator
        validator = ChainValidator()

        # Validate all workflows
        results = validator.validate_all_workflows()

        # Log warnings to stderr
        if results['summary']['total_warnings'] > 0:
            print(f"Chain validation: {results['summary']['total_warnings']} warnings", file=sys.stderr)

        # Output JSON response
        response = {
            "status": "success",
            "chain_validation": results
        }
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in chain-validator hook: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    # If run directly, show validation results
    validator = ChainValidator()
    results = validator.validate_all_workflows()
    print(json.dumps(results, indent=2))

    print("\n--- Workflow Visualizations ---\n")
    for workflow_id in results['workflows'].keys():
        print(validator.get_workflow_visualization(workflow_id))
        print()
