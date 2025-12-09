#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

// Import tool handlers
import { healthTools } from './tools/health.js';
import { gitTools } from './tools/git.js';
import { qualityTools } from './tools/quality.js';
import { routineTools } from './tools/routines.js';
import { createToolSearch } from './search/search.js';

// Tool interface
interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
  examples?: Array<{
    scenario: string;
    input: Record<string, unknown>;
    output: unknown;
  }>;
}

// Workspace path (mounted from host)
const WORKSPACE_PATH = process.env.WORKSPACE_PATH || process.cwd();

class ProjectDevServer {
  private server: Server;
  private allTools: Tool[];
  private toolSearch: ReturnType<typeof createToolSearch>;

  constructor() {
    this.server = new Server(
      {
        name: '{{PROJECT_NAME}}-dev',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Combine all tools
    this.allTools = [...healthTools, ...gitTools, ...qualityTools, ...routineTools];

    // Initialize tool search
    this.toolSearch = createToolSearch(this.allTools);

    // Setup handlers
    this.setupToolHandlers();

    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    // List tools handler - expose tool_search for progressive discovery
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        // Expose tool_search for dynamic discovery
        {
          name: 'tool_search',
          description:
            'Search for relevant development tools using natural language. Returns matching tools that can then be called.',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description:
                  'Natural language description of needed capability (e.g., "check if services are running", "get git status")',
              },
              top_k: {
                type: 'number',
                description: 'Number of tools to return (default: 5)',
                default: 5,
              },
            },
            required: ['query'],
          },
        },
        // Also expose all tools directly for when Claude knows what it needs
        ...this.allTools.map((tool) => ({
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
        })),
      ],
    }));

    // Call tool handler
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      if (name === 'tool_search') {
        // Return matching tools with their schemas
        const results = await this.toolSearch.search(
          (args as Record<string, unknown>).query as string,
          ((args as Record<string, unknown>).top_k as number) || 5
        );

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  message: `Found ${results.length} relevant tools. You can call these directly.`,
                  tools: results.map((r) => ({
                    name: r.tool.name,
                    description: r.tool.description,
                    inputSchema: r.tool.inputSchema,
                    relevanceScore: r.score.toFixed(3),
                  })),
                },
                null,
                2
              ),
            },
          ],
        };
      }

      // Find and execute the tool
      const tool = this.allTools.find((t) => t.name === name);
      if (!tool) {
        throw new Error(`Tool not found: ${name}. Use tool_search to find available tools.`);
      }

      try {
        const result = await tool.handler((args as Record<string, unknown>) || {}, WORKSPACE_PATH);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  error: true,
                  message: error instanceof Error ? error.message : String(error),
                  tool: name,
                },
                null,
                2
              ),
            },
          ],
          isError: true,
        };
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('{{PROJECT_NAME}} Dev MCP server running on stdio');
  }
}

const server = new ProjectDevServer();
server.run().catch(console.error);
