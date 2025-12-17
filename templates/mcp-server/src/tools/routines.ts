import { execa } from 'execa';
import * as fs from 'fs/promises';
import * as path from 'path';

interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
}

export const routineTools: Tool[] = [
  {
    name: 'morning_routine',
    description: 'Run comprehensive morning health check. Returns Ready to Code score (0-100).',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      const checks: { name: string; passed: boolean; message: string }[] = [];
      let score = 100;

      // Check dev server
      try {
        const response = await fetch('http://localhost:{{DEV_PORT}}');
        checks.push({
          name: 'Dev Server',
          passed: response.ok || response.status < 500,
          message: response.ok ? 'Running' : 'Not responding correctly',
        });
      } catch {
        checks.push({ name: 'Dev Server', passed: false, message: 'Not running' });
        score -= 20;
      }

      // Check git status
      try {
        const result = await execa('git', ['status', '--porcelain'], { cwd: workspacePath });
        const changes = result.stdout.split('\n').filter(Boolean).length;
        checks.push({
          name: 'Git Status',
          passed: true,
          message: changes > 0 ? `${changes} uncommitted files` : 'Clean',
        });
        if (changes > 10) score -= 10;
      } catch {
        checks.push({ name: 'Git Status', passed: false, message: 'Not a git repository' });
        score -= 10;
      }

      // Check TypeScript
      try {
        const result = await execa('npx', ['tsc', '--noEmit'], { cwd: workspacePath, reject: false });
        const hasErrors = result.exitCode !== 0;
        const errorCount = (result.stdout.match(/error TS/g) || []).length;
        checks.push({
          name: 'TypeScript',
          passed: !hasErrors,
          message: hasErrors ? `${errorCount} errors` : 'No errors',
        });
        if (hasErrors) score -= 15;
      } catch {
        checks.push({ name: 'TypeScript', passed: false, message: 'TypeScript check failed' });
        score -= 15;
      }

      return {
        score: Math.max(0, score),
        status: score >= 80 ? 'Ready to code' : score >= 50 ? 'Issues need attention' : 'Critical issues',
        checks,
        recommendations: checks
          .filter((c) => !c.passed)
          .map((c) => `Fix: ${c.name} - ${c.message}`),
      };
    },
  },

  {
    name: 'nightly_routine',
    description: 'Run end-of-day cleanup. Returns Sleep Score (0-100).',
    inputSchema: {
      type: 'object',
      properties: {},
    },
    async handler(_args, workspacePath) {
      const actions: { name: string; success: boolean; message: string }[] = [];
      let score = 100;

      // Check for uncommitted changes
      try {
        const result = await execa('git', ['status', '--porcelain'], { cwd: workspacePath });
        const changes = result.stdout.split('\n').filter(Boolean).length;
        if (changes > 0) {
          actions.push({
            name: 'Uncommitted Changes',
            success: false,
            message: `${changes} files not committed`,
          });
          score -= 30;
        } else {
          actions.push({
            name: 'Git Status',
            success: true,
            message: 'All changes committed',
          });
        }
      } catch {
        actions.push({ name: 'Git Check', success: false, message: 'Failed to check git status' });
      }

      // Clean old logs
      try {
        const logsDir = path.join(workspacePath, '.claude', 'logs');
        const files = await fs.readdir(logsDir).catch(() => []);
        const oldFiles = [];
        const now = Date.now();
        const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

        for (const file of files) {
          const stat = await fs.stat(path.join(logsDir, file)).catch(() => null);
          if (stat && now - stat.mtimeMs > maxAge) {
            oldFiles.push(file);
            await fs.unlink(path.join(logsDir, file)).catch(() => {});
          }
        }

        actions.push({
          name: 'Log Cleanup',
          success: true,
          message: oldFiles.length > 0 ? `Removed ${oldFiles.length} old logs` : 'No old logs',
        });
      } catch {
        actions.push({ name: 'Log Cleanup', success: true, message: 'Skipped (no logs directory)' });
      }

      // Git maintenance
      try {
        await execa('git', ['gc', '--auto'], { cwd: workspacePath });
        actions.push({ name: 'Git Maintenance', success: true, message: 'Completed' });
      } catch {
        actions.push({ name: 'Git Maintenance', success: false, message: 'Failed' });
      }

      return {
        score: Math.max(0, score),
        safeToClose: score >= 70,
        status: score >= 90 ? 'Safe to close' : score >= 70 ? 'Minor issues' : 'Uncommitted work',
        actions,
        warnings: actions.filter((a) => !a.success).map((a) => `${a.name}: ${a.message}`),
      };
    },
  },
];
