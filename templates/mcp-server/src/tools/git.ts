import { execa } from 'execa';

interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
}

export const gitTools: Tool[] = [
  {
    name: 'git_status',
    description: 'Get git repository status including branch, uncommitted changes, and remote sync status.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      try {
        const [branchResult, statusResult, remoteResult] = await Promise.all([
          execa('git', ['branch', '--show-current'], { cwd: workspacePath }),
          execa('git', ['status', '--porcelain'], { cwd: workspacePath }),
          execa('git', ['rev-list', '--count', '--left-right', '@{u}...HEAD'], { cwd: workspacePath }).catch(() => ({ stdout: '0\t0' })),
        ]);

        const branch = branchResult.stdout.trim();
        const changes = statusResult.stdout.split('\n').filter(Boolean);
        const [behind, ahead] = remoteResult.stdout.split('\t').map(Number);

        return {
          branch,
          uncommittedFiles: changes.length,
          staged: changes.filter((c) => c[0] !== ' ' && c[0] !== '?').length,
          unstaged: changes.filter((c) => c[1] !== ' ').length,
          untracked: changes.filter((c) => c.startsWith('??')).length,
          behind,
          ahead,
          clean: changes.length === 0,
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
    name: 'git_diff',
    description: 'Get diff of uncommitted changes. Can show staged changes only.',
    inputSchema: {
      type: 'object',
      properties: {
        cached: {
          type: 'boolean',
          description: 'Show staged changes only (default: false)',
          default: false,
        },
        file: {
          type: 'string',
          description: 'Optional specific file to diff',
        },
      },
    },
    async handler(args, workspacePath) {
      const cached = args.cached as boolean;
      const file = args.file as string | undefined;

      const gitArgs = ['diff'];
      if (cached) gitArgs.push('--cached');
      if (file) gitArgs.push(file);

      try {
        const result = await execa('git', gitArgs, { cwd: workspacePath });
        return {
          diff: result.stdout,
          hasChanges: result.stdout.length > 0,
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
    name: 'git_recent_commits',
    description: 'Get recent commits from git history.',
    inputSchema: {
      type: 'object',
      properties: {
        count: {
          type: 'number',
          description: 'Number of commits to retrieve (default: 10)',
          default: 10,
        },
      },
    },
    async handler(args, workspacePath) {
      const count = (args.count as number) || 10;

      try {
        const result = await execa(
          'git',
          ['log', `--oneline`, `-${count}`, '--format=%h %s (%ar)'],
          { cwd: workspacePath }
        );

        const commits = result.stdout.split('\n').filter(Boolean).map((line) => {
          const match = line.match(/^(\w+) (.+) \((.+)\)$/);
          return match
            ? { hash: match[1], message: match[2], when: match[3] }
            : { raw: line };
        });

        return { commits };
      } catch (error) {
        return {
          error: true,
          message: error instanceof Error ? error.message : String(error),
        };
      }
    },
  },
];
