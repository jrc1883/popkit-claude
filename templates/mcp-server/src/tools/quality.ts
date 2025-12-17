import { execa } from 'execa';

interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
}

export const qualityTools: Tool[] = [
  {
    name: 'run_typecheck',
    description: 'Run TypeScript type checking. Returns error count and details.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      try {
        const result = await execa('npx', ['tsc', '--noEmit'], {
          cwd: workspacePath,
          reject: false,
        });

        const errors = result.stdout
          .split('\n')
          .filter((line) => line.includes('error TS'))
          .map((line) => {
            const match = line.match(/^(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)$/);
            return match
              ? {
                  file: match[1],
                  line: parseInt(match[2]),
                  column: parseInt(match[3]),
                  code: match[4],
                  message: match[5],
                }
              : { raw: line };
          });

        return {
          success: result.exitCode === 0,
          errorCount: errors.length,
          errors: errors.slice(0, 20), // Limit to first 20
        };
      } catch (error) {
        return {
          error: true,
          message: error instanceof Error ? error.message : String(error),
        };
      }
    },
  },

  {
    name: 'run_lint',
    description: 'Run ESLint on the codebase. Returns warning and error counts.',
    inputSchema: {
      type: 'object',
      properties: {
        fix: {
          type: 'boolean',
          description: 'Auto-fix problems (default: false)',
          default: false,
        },
      },
    },
    async handler(args, workspacePath) {
      const fix = args.fix as boolean;

      try {
        const lintArgs = ['eslint', '.', '--format', 'json'];
        if (fix) lintArgs.push('--fix');

        const result = await execa('npx', lintArgs, {
          cwd: workspacePath,
          reject: false,
        });

        let parsed;
        try {
          parsed = JSON.parse(result.stdout);
        } catch {
          return {
            success: result.exitCode === 0,
            message: result.stdout || 'Lint completed',
          };
        }

        const summary = parsed.reduce(
          (acc: { errors: number; warnings: number }, file: { errorCount: number; warningCount: number }) => ({
            errors: acc.errors + file.errorCount,
            warnings: acc.warnings + file.warningCount,
          }),
          { errors: 0, warnings: 0 }
        );

        return {
          success: summary.errors === 0,
          errorCount: summary.errors,
          warningCount: summary.warnings,
          fixed: fix,
        };
      } catch (error) {
        return {
          error: true,
          message: error instanceof Error ? error.message : String(error),
        };
      }
    },
  },

  {
    name: 'run_tests',
    description: 'Run test suite. Returns pass/fail counts.',
    inputSchema: {
      type: 'object',
      properties: {
        pattern: {
          type: 'string',
          description: 'Test file pattern to run',
        },
      },
    },
    async handler(args, workspacePath) {
      const pattern = args.pattern as string | undefined;

      try {
        // Customize test command for your project
        const testArgs = ['test'];
        if (pattern) testArgs.push('--', pattern);

        const result = await execa('npm', testArgs, {
          cwd: workspacePath,
          reject: false,
        });

        // Parse test output (customize for your test framework)
        const output = result.stdout + result.stderr;
        const passMatch = output.match(/(\d+) pass/);
        const failMatch = output.match(/(\d+) fail/);

        return {
          success: result.exitCode === 0,
          passed: passMatch ? parseInt(passMatch[1]) : 0,
          failed: failMatch ? parseInt(failMatch[1]) : 0,
          output: output.slice(-2000), // Last 2000 chars
        };
      } catch (error) {
        return {
          error: true,
          message: error instanceof Error ? error.message : String(error),
        };
      }
    },
  },
];
