/**
 * Tool search with semantic and keyword matching
 *
 * Uses pre-computed embeddings for semantic search when available,
 * falls back to keyword matching otherwise.
 */

import { loadEmbeddings, hasEmbeddings, type ToolEmbedding } from './embeddings.js';
import { semanticSearch, hybridSearch, type SemanticSearchResult } from './semantic.js';

interface Tool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (args: Record<string, unknown>, workspacePath: string) => Promise<unknown>;
}

interface SearchResult {
  tool: Tool;
  score: number;
  method: 'semantic' | 'keyword' | 'hybrid';
}

interface ToolSearchConfig {
  workspacePath?: string;
  useSemanticSearch?: boolean;
  minSimilarity?: number;
}

export function createToolSearch(tools: Tool[], config: ToolSearchConfig = {}) {
  const { workspacePath = process.cwd(), useSemanticSearch = true, minSimilarity = 0.3 } = config;

  // Pre-process tool descriptions into keywords
  const toolKeywords = tools.map((tool) => ({
    tool,
    keywords: extractKeywords(tool.name + ' ' + tool.description),
  }));

  // Create tool lookup map
  const toolMap = new Map<string, Tool>(tools.map((tool) => [tool.name, tool]));

  // Load embeddings if available
  let embeddings: ToolEmbedding[] = [];
  if (useSemanticSearch && hasEmbeddings(workspacePath)) {
    embeddings = loadEmbeddings(workspacePath);
    console.log(`Loaded ${embeddings.length} tool embeddings for semantic search`);
  }

  return {
    /**
     * Search for tools matching a query
     *
     * Uses semantic search when embeddings are available,
     * falls back to keyword matching otherwise.
     */
    search(query: string, topK: number = 5): Promise<SearchResult[]> {
      // Get keyword results
      const keywordResults = keywordSearch(query, toolKeywords, topK);

      // If we have embeddings, use hybrid search
      if (embeddings.length > 0) {
        const semanticResults = semanticSearch(query, embeddings, undefined, topK, minSimilarity);

        // If semantic found results, use hybrid approach
        if (semanticResults.length > 0) {
          const hybridResults = hybridSearch(
            semanticResults,
            keywordResults.map((r) => ({ toolName: r.tool.name, score: r.score }))
          );

          // Map back to tools
          return Promise.resolve(
            hybridResults
              .slice(0, topK)
              .map((r: SemanticSearchResult) => ({
                tool: toolMap.get(r.toolName)!,
                score: r.similarity,
                method: 'hybrid' as const,
              }))
              .filter((r: SearchResult) => r.tool !== undefined)
          );
        }
      }

      // Keyword-only fallback
      return Promise.resolve(
        keywordResults.map((r) => ({ ...r, method: 'keyword' as const }))
      );
    },

    /**
     * Check if semantic search is available
     */
    hasSemanticSearch(): boolean {
      return embeddings.length > 0;
    },

    /**
     * Get search configuration info
     */
    getInfo(): { embeddingsCount: number; toolsCount: number } {
      return {
        embeddingsCount: embeddings.length,
        toolsCount: tools.length,
      };
    },
  };
}

/**
 * Keyword-based search (original implementation)
 */
function keywordSearch(
  query: string,
  toolKeywords: { tool: Tool; keywords: Set<string> }[],
  topK: number
): { tool: Tool; score: number }[] {
  const queryKeywords = extractKeywords(query);

  // Score each tool based on keyword overlap
  const scored = toolKeywords.map(({ tool, keywords }) => {
    const score = calculateScore(queryKeywords, keywords);
    return { tool, score };
  });

  // Sort by score and return top K
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .filter((r) => r.score > 0);
}

function extractKeywords(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((word) => word.length > 2)
  );
}

function calculateScore(queryKeywords: Set<string>, toolKeywords: Set<string>): number {
  let matches = 0;
  for (const keyword of queryKeywords) {
    if (toolKeywords.has(keyword)) {
      matches++;
    } else {
      // Partial match
      for (const toolKeyword of toolKeywords) {
        if (toolKeyword.includes(keyword) || keyword.includes(toolKeyword)) {
          matches += 0.5;
          break;
        }
      }
    }
  }
  return matches / Math.max(queryKeywords.size, 1);
}
