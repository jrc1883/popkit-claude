# {{PROJECT_NAME}} Dev MCP Server

Project-specific MCP (Model Context Protocol) server for {{PROJECT_NAME}} development.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Build:
```bash
npm run build
```

3. Add to Claude Code settings (`.claude/settings.json`):
```json
{
  "mcpServers": {
    "{{PROJECT_NAME}}-dev": {
      "command": "node",
      "args": [".claude/mcp-servers/{{PROJECT_NAME}}-dev/dist/index.js"]
    }
  }
}
```

4. Restart Claude Code

## Available Tools

### Health Checks
- `check_dev_server` - Check if dev server is running
- `check_database` - Check database connectivity

### Git Tools
- `git_status` - Get repository status
- `git_diff` - View uncommitted changes
- `git_recent_commits` - List recent commits

### Quality Tools
- `run_typecheck` - Run TypeScript type checking
- `run_lint` - Run ESLint (with optional auto-fix)
- `run_tests` - Run test suite

### Routines
- `morning_routine` - Morning health check (Ready to Code score)
- `nightly_routine` - End-of-day cleanup (Sleep Score)

### Discovery
- `tool_search` - Search for tools by natural language description

## Customization

Edit the tools in `src/tools/` to match your project's needs:

- **Ports**: Update `{{DEV_PORT}}` and `{{DB_PORT}}` in health.ts
- **Test command**: Update test runner in quality.ts
- **Database**: Update database type/command in health.ts

## Development

```bash
# Watch mode
npm run dev

# Build
npm run build

# Run
npm start
```

## Tool Search

The server includes a semantic tool search that lets you find tools by description:

```
tool_search("check if services are running")
→ Returns: check_dev_server, check_database

tool_search("view recent code changes")
→ Returns: git_diff, git_recent_commits
```
