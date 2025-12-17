#!/usr/bin/env python3
"""
Output Validator Hook
Validates agent outputs against their declared output_style schema.

Part of the popkit plugin output validation layer.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime


def load_schema(output_style: str) -> dict | None:
    """Load JSON schema for given output style."""
    # Try relative to hooks directory first, then project root
    schema_paths = [
        Path(__file__).parent.parent / f"output-styles/schemas/{output_style}.schema.json",
        Path(f"output-styles/schemas/{output_style}.schema.json"),
    ]

    for schema_path in schema_paths:
        if schema_path.exists():
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
    return None


def extract_fields_from_markdown(output: str) -> dict:
    """Extract structured fields from markdown output."""
    extracted = {}

    # Common patterns to extract
    patterns = {
        "from": r"\*\*From:\*\*\s*(.+?)(?:\n|$)",
        "to": r"\*\*To:\*\*\s*(.+?)(?:\n|$)",
        "task": r"\*\*Task:\*\*\s*(.+?)(?:\n|$)",
        "status": r"\*\*Status:\*\*\s*(.+?)(?:\n|$)",
        "confidence": r"\*\*(?:Confidence|Handoff Confidence):\*\*\s*(\d+)",
        "severity": r"\*\*Severity:\*\*\s*(.+?)(?:\n|$)",
        "healthScore": r"\*\*Health Score:\*\*\s*(\d+)",
        "securityScore": r"\*\*Security Score:\*\*\s*(\d+)",
        "recommendation": r"\*\*Recommendation:\*\*\s*(.+?)(?:\n|$)",
        "auditDate": r"\*\*Audit Date:\*\*\s*(.+?)(?:\n|$)",
        "date": r"\*\*Date:\*\*\s*(.+?)(?:\n|$)",
        "scope": r"\*\*Scope:\*\*\s*(.+?)(?:\n|$)",
        "issueTitle": r"## (?:Debugging Report|Bug Investigation Report):\s*(.+?)(?:\n|$)",
        "projectName": r"## (?:Analysis Report|Security Audit Report):\s*(.+?)(?:\n|$)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Convert numeric fields
            if field in ["confidence", "healthScore", "securityScore"]:
                try:
                    extracted[field] = int(value)
                except ValueError:
                    extracted[field] = value
            else:
                extracted[field] = value

    # Check for summary section
    summary_match = re.search(r"### Summary\s*\n(.+?)(?:\n###|\n---|\Z)", output, re.DOTALL)
    if summary_match:
        extracted["summary"] = summary_match.group(1).strip()[:500]  # Limit length

    # Check for symptom section (debugging report)
    symptom_match = re.search(r"### Symptom\s*\n(.+?)(?:\n###|\n---|\Z)", output, re.DOTALL)
    if symptom_match:
        extracted["symptom"] = {"description": symptom_match.group(1).strip()[:500]}

    return extracted


def validate_required_fields(extracted: dict, schema: dict) -> list:
    """Check for missing required fields."""
    missing = []
    required = schema.get("required", [])

    for field in required:
        if field not in extracted or extracted[field] is None or extracted[field] == "":
            missing.append(field)

    return missing


def calculate_confidence(extracted: dict, schema: dict) -> int:
    """Calculate validation confidence score."""
    required = schema.get("required", [])
    if not required:
        return 100

    present = sum(1 for field in required if field in extracted and extracted[field])
    return int((present / len(required)) * 100)


def validate_output(output: str, schema: dict) -> dict:
    """Validate output against schema, return validation result."""
    # Extract structured fields from markdown
    extracted = extract_fields_from_markdown(output)

    # Check required fields
    missing = validate_required_fields(extracted, schema)

    # Calculate confidence
    confidence = calculate_confidence(extracted, schema)

    return {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "extracted_fields": list(extracted.keys()),
        "confidence": confidence,
        "field_count": len(extracted)
    }


def main():
    """Main entry point - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        agent_name = data.get("agent", data.get("subagent_type", "unknown"))
        output = data.get("output", data.get("result", ""))
        output_style = data.get("output_style")

        # Try to get output_style from agent config if not provided
        if not output_style:
            # Check if we can infer from agent metadata
            agent_config_path = Path(__file__).parent.parent / f"agents/*/{agent_name}.md"
            # For now, skip validation if no output_style declared
            response = {
                "status": "skip",
                "reason": "no output_style declared",
                "agent": agent_name,
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(response))
            return

        # Load schema
        schema = load_schema(output_style)
        if not schema:
            response = {
                "status": "warning",
                "reason": f"schema not found: {output_style}",
                "agent": agent_name,
                "output_style": output_style,
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(response))
            return

        # Validate output
        result = validate_output(output, schema)
        result["status"] = "valid" if result["valid"] else "invalid"
        result["agent"] = agent_name
        result["output_style"] = output_style
        result["timestamp"] = datetime.now().isoformat()

        # Add suggestions for missing fields
        if not result["valid"]:
            result["suggestion"] = f"Agent output missing required fields: {', '.join(result['missing_fields'])}. Please ensure the output follows the {output_style} format."

        print(json.dumps(result))

    except json.JSONDecodeError as e:
        response = {
            "status": "error",
            "error": f"Invalid JSON input: {e}",
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(response))
        print(f"Error in output-validator hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors


if __name__ == "__main__":
    main()
