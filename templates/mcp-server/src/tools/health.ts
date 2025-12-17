import { execa } from 'execa';

interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
}

// Check if a port is in use (service running)
async function checkPort(port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://localhost:${port}`);
    return response.ok || response.status < 500;
  } catch {
    return false;
  }
}

// Health check tools - customize ports and services for your project
export const healthTools: Tool[] = [
  {
    name: 'check_dev_server',
    description: 'Check if development server is running. Returns health status and URL.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      // Customize port for your project (replaced by generator)
      const port = 3000; // {{DEV_PORT}}
      const running = await checkPort(port);

      return {
        running,
        url: running ? `http://localhost:${port}` : null,
        port,
        message: running ? 'Dev server is running' : 'Dev server is not running',
      };
    },
  },

  {
    name: 'check_database',
    description: 'Check database connectivity. Returns connection status.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      // Customize for your database (replaced by generator)
      const port = 5432; // {{DB_PORT}}

      try {
        // For PostgreSQL - customize for your database type
        const result = await execa('pg_isready', ['-h', 'localhost', '-p', String(port)], {
          cwd: workspacePath,
          timeout: 5000,
        });

        return {
          connected: result.exitCode === 0,
          port,
          message: 'Database is connected',
        };
      } catch {
        return {
          connected: false,
          port,
          message: 'Database is not connected',
        };
      }
    },
  },
];
