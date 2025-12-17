#!/usr/bin/env python3
"""
Research Findings Extraction Script.

Extract key findings from collected research content.

Usage:
    python extract_findings.py [--input FILE] [--url URL] [--format FORMAT]

Output:
    JSON object with extracted findings
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error


def fetch_url_content(url: str) -> Optional[str]:
    """Fetch content from a URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; PopKit/1.0)'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8', errors='ignore')
            return content
    except Exception as e:
        return None


def extract_headings(content: str) -> List[str]:
    """Extract headings from markdown or HTML content."""
    headings = []

    # Markdown headings
    md_headings = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    headings.extend(md_headings)

    # HTML headings
    html_headings = re.findall(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', content, re.IGNORECASE)
    headings.extend(html_headings)

    return headings


def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """Extract code blocks from content."""
    blocks = []

    # Markdown code blocks
    md_blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
    for lang, code in md_blocks:
        blocks.append({
            "language": lang or "text",
            "code": code.strip()
        })

    return blocks


def extract_links(content: str) -> List[Dict[str, str]]:
    """Extract links from content."""
    links = []

    # Markdown links
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, url in md_links:
        links.append({"text": text, "url": url})

    # HTML links
    html_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', content, re.IGNORECASE)
    for url, text in html_links:
        links.append({"text": text, "url": url})

    return links


def extract_key_points(content: str) -> List[str]:
    """Extract key points and bullet items from content."""
    points = []

    # Bullet points
    bullets = re.findall(r'^[\*\-\+]\s+(.+)$', content, re.MULTILINE)
    points.extend(bullets)

    # Numbered items
    numbered = re.findall(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
    points.extend(numbered)

    return points


def extract_definitions(content: str) -> List[Dict[str, str]]:
    """Extract term definitions from content."""
    definitions = []

    # Pattern: Term: Definition
    colon_defs = re.findall(r'^([A-Z][^:]+):\s+(.+)$', content, re.MULTILINE)
    for term, definition in colon_defs:
        if len(term) < 50:  # Avoid matching sentences
            definitions.append({"term": term.strip(), "definition": definition.strip()})

    return definitions


def summarize_content(content: str, max_length: int = 500) -> str:
    """Generate a brief summary of the content."""
    # Remove code blocks for summary
    clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', clean)

    # Get first few sentences
    sentences = re.split(r'[.!?]+', clean)
    summary = []
    length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and length + len(sentence) < max_length:
            summary.append(sentence)
            length += len(sentence)
        elif length > 0:
            break

    return '. '.join(summary) + '.' if summary else ''


def extract_findings(content: str, source: str = None) -> Dict[str, Any]:
    """Extract all findings from content."""
    return {
        "source": source,
        "extracted_at": datetime.now().isoformat(),
        "summary": summarize_content(content),
        "headings": extract_headings(content),
        "key_points": extract_key_points(content),
        "definitions": extract_definitions(content),
        "code_blocks": extract_code_blocks(content)[:10],  # Limit code blocks
        "links": extract_links(content)[:20],  # Limit links
        "word_count": len(content.split()),
        "line_count": len(content.split('\n'))
    }


def assess_quality(findings: Dict[str, Any]) -> Dict[str, Any]:
    """Assess the quality of extracted findings."""
    scores = {
        "has_summary": 1 if findings["summary"] else 0,
        "has_headings": 1 if findings["headings"] else 0,
        "has_key_points": 1 if findings["key_points"] else 0,
        "has_code_examples": 1 if findings["code_blocks"] else 0,
        "has_references": 1 if findings["links"] else 0,
        "sufficient_length": 1 if findings["word_count"] > 100 else 0
    }

    total = sum(scores.values())
    max_score = len(scores)

    return {
        "scores": scores,
        "total": total,
        "max": max_score,
        "percentage": round(total / max_score * 100),
        "quality_level": "high" if total >= 5 else "medium" if total >= 3 else "low"
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract research findings")
    parser.add_argument("--input", "-i", help="Input file path")
    parser.add_argument("--url", "-u", help="URL to fetch")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    parser.add_argument("--assess", action="store_true", help="Include quality assessment")
    args = parser.parse_args()

    content = None
    source = None

    # Get content from input
    if args.input:
        input_path = Path(args.input)
        if input_path.exists():
            content = input_path.read_text()
            source = str(input_path)
        else:
            print(json.dumps({
                "success": False,
                "error": f"File not found: {args.input}"
            }, indent=2))
            return 1

    elif args.url:
        content = fetch_url_content(args.url)
        source = args.url
        if not content:
            print(json.dumps({
                "success": False,
                "error": f"Failed to fetch URL: {args.url}"
            }, indent=2))
            return 1

    else:
        # Read from stdin
        content = sys.stdin.read()
        source = "stdin"

    # Extract findings
    findings = extract_findings(content, source)

    # Assess quality if requested
    if args.assess:
        findings["quality"] = assess_quality(findings)

    # Output
    if args.format == "markdown":
        output = generate_markdown(findings)
        print(output)
    else:
        print(json.dumps({
            "operation": "extract_findings",
            "success": True,
            **findings
        }, indent=2))

    return 0


def generate_markdown(findings: Dict[str, Any]) -> str:
    """Generate markdown from findings."""
    lines = [
        f"# Research Findings",
        f"",
        f"**Source:** {findings['source']}",
        f"**Extracted:** {findings['extracted_at']}",
        f"",
        f"## Summary",
        f"",
        findings['summary'] or "No summary available.",
        f""
    ]

    if findings['headings']:
        lines.extend([
            "## Structure",
            ""
        ])
        for heading in findings['headings'][:10]:
            lines.append(f"- {heading}")
        lines.append("")

    if findings['key_points']:
        lines.extend([
            "## Key Points",
            ""
        ])
        for point in findings['key_points'][:15]:
            lines.append(f"- {point}")
        lines.append("")

    if findings['definitions']:
        lines.extend([
            "## Definitions",
            ""
        ])
        for defn in findings['definitions'][:10]:
            lines.append(f"- **{defn['term']}**: {defn['definition']}")
        lines.append("")

    if findings.get('quality'):
        q = findings['quality']
        lines.extend([
            "## Quality Assessment",
            "",
            f"- Quality Level: **{q['quality_level']}** ({q['percentage']}%)",
            f"- Score: {q['total']}/{q['max']}",
            ""
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
