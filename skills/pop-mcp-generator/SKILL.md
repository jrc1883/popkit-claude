---
name: mcp-generator
description: "Use when setting up project-specific development tools or after analyzing a codebase - generates custom MCP server with semantic search, project-aware tools, and health monitoring capabilities. Do NOT use if generic popkit commands are sufficient or for small projects where MCP server overhead isn't justified - stick with built-in tools for simple workflows."
---

# MCP Server Generator

## Overview

Generate a custom MCP (Model Context Protocol) server tailored to the specific project's needs, including semantic search, project-specific tools, and contextual capabilities.

**Core principle:** Every project deserves tools that understand its unique architecture.

**Trigger:** `/popkit:project mcp` command after project analysis

## Arguments

| Flag | Description |
|------|-------------|
| `--from-analysis` | Use `.claude/analysis.json` for tool selection |
| `--no-embed` | Skip auto-embedding of tools |
| `--no-semantic` | Don't include semantic search capabilities |
| `--tools <list>` | Comma-separated list of tools to generate |

## What Gets Generated

```
.claude/mcp-servers/[project-name]-dev/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # MCP server entry point
│   ├── tools/
│   │   ├── project-tools.ts  # Project-specific tools
│   │   ├── health-check.ts   # Service health checks
│   │   └── search.ts         # Semantic search
│   └── resources/
│       └── project-context.ts # Project documentation
└── README.md
```

## Generation Process

### Step 1: Analyze Project

Gather project information:

```bash
# Detect tech stack
ls package.json Cargo.toml pyproject.toml go.mod 2>/dev/null

# Find main directories
ls -d src lib app components 2>/dev/null

# Detect test framework
grep -l "jest\|mocha\|vitest\|pytest" package.json pyproject.toml 2>/dev/null

# Find configuration files
ls .env* config/ *.config.* 2>/dev/null
```

### Step 2: Determine Tools to Generate

Based on project type, select tools:

**Node.js:**
- check_nextjs / check_vite / check_express
- run_typecheck
- run_lint
- run_tests
- npm_scripts

**Python:**
- run_pytest
- run_mypy
- check_virtualenv
- run_lint (ruff/black)

**Rust:**
- cargo_check
- cargo_test
- cargo_clippy

**Common:**
- git_status
- git_diff
- git_recent_commits
- morning_routine
- nightly_routine
- tool_search (semantic)

### Step 3: Generate package.json

```json
{
  "name": "[project]-dev-mcp",
  "version": "1.0.0",
  "description": "MCP server for [project] development",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx src/index.ts"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "latest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tsx": "^4.0.0"
  }
}
```

### Step 4: Generate Tool Implementations

For each tool, generate TypeScript implementation:

```typescript
// Example: health check tool
export const checkService = {
  name: "[project]__check_[service]",
  description: "Check if [service] is running on port [port]",
  inputSchema: {
    type: "object",
    properties: {},
    required: []
  },
  async execute() {
    const response = await fetch(`http://localhost:[port]/health`);
    return {
      running: response.ok,
      url: `http://localhost:[port]`,
      status: response.status
    };
  }
};
```

### Step 5: Generate Semantic Search

Create tool search with embeddings:

```typescript
// Tool search with semantic matching
export const toolSearch = {
  name: "[project]__tool_search",
  description: "Search for tools by description",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Natural language query" },
      top_k: { type: "number", default: 5 }
    },
    required: ["query"]
  },
  async execute({ query, top_k = 5 }) {
    // Match against tool descriptions
    const tools = getAllTools();
    return rankByRelevance(tools, query, top_k);
  }
};
```

### Step 6: Generate Index File

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// Import all tools
import { projectTools } from "./tools/project-tools.js";
import { healthChecks } from "./tools/health-check.js";
import { searchTools } from "./tools/search.js";

const server = new Server({
  name: "[project]-dev",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

// Register all tools
const allTools = [...projectTools, ...healthChecks, ...searchTools];

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: allTools.map(t => ({
    name: t.name,
    description: t.description,
    inputSchema: t.inputSchema
  }))
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const tool = allTools.find(t => t.name === request.params.name);
  if (!tool) throw new Error(`Unknown tool: ${request.params.name}`);
  return await tool.execute(request.params.arguments);
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Step 7: Register in Claude Settings

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "[project]-dev": {
      "command": "node",
      "args": [".claude/mcp-servers/[project]-dev/dist/index.js"]
    }
  }
}
```

## Post-Generation

After generating:

```
MCP server generated at .claude/mcp-servers/[project]-dev/

Tools created:
- [project]__check_[services]
- [project]__run_typecheck
- [project]__run_lint
- [project]__run_tests
- [project]__git_status
- [project]__tool_search

Next steps:
1. cd .claude/mcp-servers/[project]-dev
2. npm install
3. npm run build
4. Restart Claude Code to load MCP server

Would you like me to build and test it?
```

## Analysis-Driven Generation

When `.claude/analysis.json` exists (from `/popkit:project analyze --json`), the generator uses structured data:

### Step 0: Check for Analysis

```python
import json
from pathlib import Path

analysis_path = Path.cwd() / ".claude" / "analysis.json"
if analysis_path.exists():
    analysis = json.loads(analysis_path.read_text())
    frameworks = analysis.get("frameworks", [])
    patterns = analysis.get("patterns", [])
    commands = analysis.get("commands", {})
else:
    # Fall back to manual detection
    frameworks = []
    patterns = []
    commands = {}
```

### Analysis-Informed Tool Selection

| Framework | Generated Tools |
|-----------|-----------------|
| `nextjs` | `check_dev_server`, `check_build`, `run_typecheck` |
| `express` | `check_api_server`, `health_endpoints` |
| `prisma` | `check_database`, `run_migrations`, `prisma_studio` |
| `supabase` | `check_supabase`, `supabase_status` |
| `redis` | `check_redis`, `redis_info` |
| `docker-compose` | `docker_status`, `docker_logs` |

## Embedding-Friendly Tool Descriptions

Tool descriptions should be detailed enough for semantic matching:

### Before (Too Brief)
```typescript
{
  name: "health:dev-server",
  description: "Check dev server"
}
```

### After (Semantic-Friendly)
```typescript
{
  name: "health:dev-server",
  description: "Check if the Next.js development server is running and responding on port 3000. Use this to verify the dev environment is working, troubleshoot startup issues, or confirm the app is accessible. Returns status, URL, and response time."
}
```

### Description Guidelines

1. **State the action clearly** - "Check if...", "Run...", "Get..."
2. **Include the target** - "...Next.js development server..."
3. **Mention common use cases** - "...troubleshoot startup issues..."
4. **List what it returns** - "Returns status, URL, and response time"

## Auto-Embedding Tools

After generating the MCP server, automatically embed tool descriptions:

### Export Tool Embeddings

```python
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "hooks/utils")
from voyage_client import VoyageClient

def export_tool_embeddings(tools: list, output_path: str):
    """Export embeddings for semantic search."""
    client = VoyageClient()

    if not client.is_available:
        print("⚠ Voyage API not available, skipping embeddings")
        return False

    descriptions = [t["description"] for t in tools]
    embeddings = client.embed(descriptions, input_type="document")

    output = {
        "generated_at": datetime.now().isoformat(),
        "model": "voyage-3.5",
        "dimension": len(embeddings[0]) if embeddings else 0,
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "embedding": emb
            }
            for t, emb in zip(tools, embeddings)
        ]
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(output, indent=2))
    print(f"✓ Exported {len(tools)} tool embeddings to {output_path}")
    return True

# After generating MCP server
tools = [
    {"name": "health:dev-server", "description": "Check if the Next.js..."},
    {"name": "health:database", "description": "Check database connectivity..."},
    # ... other tools
]

export_tool_embeddings(tools, ".claude/tool_embeddings.json")
```

### Register in Embedding Store

Also store in the global embedding database for cross-project discovery:

```python
from embedding_project import auto_embed_item

# After writing each tool file
for tool_file in tool_files:
    success = auto_embed_item(tool_file, "mcp-tool")
    if success:
        print(f"  └─ Embedded: {tool_file}")
```

## Updated Generation Flow

```
1. Check for .claude/analysis.json
2. If exists: Use recommended tools from analysis
3. If not: Fall back to project detection
4. Generate MCP server with detailed descriptions
5. Export tool_embeddings.json for semantic search
6. Register tools in embedding store
7. Update .claude/settings.json
8. Report status with embedding summary
```

## Post-Generation

After generating:

```
MCP server generated at .claude/mcp-servers/[project]-dev/

Tools created (8):
✓ health:dev-server - Check Next.js dev server
  └─ Embedded for semantic search
✓ health:database - Check PostgreSQL connectivity
  └─ Embedded for semantic search
✓ quality:typecheck - Run TypeScript type checking
  └─ Embedded for semantic search
✓ quality:lint - Run ESLint checks
  └─ Embedded for semantic search
✓ quality:test - Run Jest test suite
  └─ Embedded for semantic search
✓ git:status - Get git working tree status
  └─ Embedded for semantic search
✓ git:diff - Show staged and unstaged changes
  └─ Embedded for semantic search
✓ search:tools - Semantic tool search
  └─ Embedded for semantic search

Embedding Summary:
- Tool embeddings: .claude/tool_embeddings.json
- Total tools: 8
- Successfully embedded: 8
- Model: voyage-3.5

Next steps:
1. cd .claude/mcp-servers/[project]-dev
2. npm install
3. npm run build
4. Restart Claude Code to load MCP server

Would you like me to build and test it?
```

## Integration

**Requires:**
- Project analysis (via analyze-project skill) for best results
- Voyage AI API key for auto-embedding (optional, but recommended)

**Enables:**
- Project-specific tools in Claude Code
- Semantic tool search with natural language queries
- Health monitoring with detailed status
- Custom workflows tailored to your stack
- Discoverable tools across projects
