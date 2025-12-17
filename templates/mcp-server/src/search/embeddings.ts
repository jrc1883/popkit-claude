/**
 * Embedding utilities for semantic tool search
 *
 * Loads pre-computed embeddings from .claude/tool_embeddings.json
 * for semantic search capabilities.
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

/**
 * Tool embedding record with pre-computed vector
 */
export interface ToolEmbedding {
  name: string;
  description: string;
  embedding: number[];
}

/**
 * Embedding file format
 */
export interface EmbeddingsFile {
  generated_at: string;
  model: string;
  dimension: number;
  tools: ToolEmbedding[];
}

/**
 * Load embeddings from the project's .claude directory
 *
 * @param workspacePath - Project root directory
 * @returns Array of tool embeddings, empty if file not found
 */
export function loadEmbeddings(workspacePath: string): ToolEmbedding[] {
  const embeddingsPath = join(workspacePath, '.claude', 'tool_embeddings.json');

  if (!existsSync(embeddingsPath)) {
    return [];
  }

  try {
    const content = readFileSync(embeddingsPath, 'utf-8');
    const data: EmbeddingsFile = JSON.parse(content);

    // Validate structure
    if (!Array.isArray(data.tools)) {
      console.warn('Invalid embeddings file: tools array not found');
      return [];
    }

    // Filter out invalid entries
    return data.tools.filter((tool) => {
      return (
        typeof tool.name === 'string' &&
        typeof tool.description === 'string' &&
        Array.isArray(tool.embedding) &&
        tool.embedding.length > 0
      );
    });
  } catch (error) {
    console.warn(`Failed to load embeddings: ${error}`);
    return [];
  }
}

/**
 * Check if embeddings are available for the workspace
 */
export function hasEmbeddings(workspacePath: string): boolean {
  const embeddingsPath = join(workspacePath, '.claude', 'tool_embeddings.json');
  return existsSync(embeddingsPath);
}

/**
 * Get embedding metadata (without loading all vectors)
 */
export function getEmbeddingsMetadata(
  workspacePath: string
): { count: number; model: string; generatedAt: string } | null {
  const embeddingsPath = join(workspacePath, '.claude', 'tool_embeddings.json');

  if (!existsSync(embeddingsPath)) {
    return null;
  }

  try {
    const content = readFileSync(embeddingsPath, 'utf-8');
    const data: EmbeddingsFile = JSON.parse(content);

    return {
      count: data.tools?.length ?? 0,
      model: data.model ?? 'unknown',
      generatedAt: data.generated_at ?? 'unknown',
    };
  } catch {
    return null;
  }
}
