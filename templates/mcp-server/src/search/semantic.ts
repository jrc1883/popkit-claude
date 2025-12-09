/**
 * Semantic search implementation using cosine similarity
 *
 * Enables natural language queries to find relevant tools
 * using pre-computed embeddings.
 */

import type { ToolEmbedding } from './embeddings.js';

/**
 * Semantic search result
 */
export interface SemanticSearchResult {
  toolName: string;
  description: string;
  similarity: number;
}

/**
 * Calculate cosine similarity between two vectors
 *
 * @param a - First vector
 * @param b - Second vector
 * @returns Similarity score between -1 and 1
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error(`Vector dimension mismatch: ${a.length} vs ${b.length}`);
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const denominator = Math.sqrt(normA) * Math.sqrt(normB);

  if (denominator === 0) {
    return 0;
  }

  return dotProduct / denominator;
}

/**
 * Semantic search using pre-computed embeddings
 *
 * Since we can't compute query embeddings at runtime without
 * an API call, this function uses a hybrid approach:
 *
 * 1. If a query embedding is provided, use cosine similarity
 * 2. Otherwise, fall back to keyword-based matching against descriptions
 *
 * @param query - Search query string
 * @param embeddings - Pre-computed tool embeddings
 * @param queryEmbedding - Optional pre-computed query embedding
 * @param topK - Number of results to return
 * @param minSimilarity - Minimum similarity threshold
 * @returns Sorted search results
 */
export function semanticSearch(
  query: string,
  embeddings: ToolEmbedding[],
  queryEmbedding?: number[],
  topK: number = 5,
  minSimilarity: number = 0.3
): SemanticSearchResult[] {
  if (embeddings.length === 0) {
    return [];
  }

  // If we have a query embedding, use cosine similarity
  if (queryEmbedding && queryEmbedding.length > 0) {
    const results = embeddings.map((tool) => ({
      toolName: tool.name,
      description: tool.description,
      similarity: cosineSimilarity(queryEmbedding, tool.embedding),
    }));

    return results
      .filter((r) => r.similarity >= minSimilarity)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, topK);
  }

  // Fallback: keyword-based semantic matching
  // Match query words against tool descriptions
  const queryWords = extractWords(query);

  const results = embeddings.map((tool) => {
    const descWords = extractWords(tool.description);
    const nameWords = extractWords(tool.name);
    const allToolWords = new Set([...descWords, ...nameWords]);

    // Calculate overlap score
    let matches = 0;
    for (const qWord of queryWords) {
      if (allToolWords.has(qWord)) {
        matches++;
      } else {
        // Partial match bonus
        for (const tWord of allToolWords) {
          if (tWord.includes(qWord) || qWord.includes(tWord)) {
            matches += 0.5;
            break;
          }
        }
      }
    }

    // Normalize to 0-1 range (rough approximation of similarity)
    const similarity = queryWords.size > 0 ? matches / queryWords.size : 0;

    return {
      toolName: tool.name,
      description: tool.description,
      similarity: Math.min(similarity, 1), // Cap at 1
    };
  });

  return results
    .filter((r) => r.similarity > 0)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, topK);
}

/**
 * Extract words from text for keyword matching
 */
function extractWords(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((word) => word.length > 2)
  );
}

/**
 * Hybrid search combining semantic and keyword results
 *
 * Merges results from both approaches, de-duplicating and
 * boosting tools that appear in both result sets.
 *
 * @param semanticResults - Results from semantic search
 * @param keywordResults - Results from keyword search
 * @param semanticWeight - Weight for semantic results (0-1)
 * @returns Merged and re-ranked results
 */
export function hybridSearch(
  semanticResults: SemanticSearchResult[],
  keywordResults: { toolName: string; score: number }[],
  semanticWeight: number = 0.7
): SemanticSearchResult[] {
  const keywordWeight = 1 - semanticWeight;
  const combined = new Map<string, { description: string; score: number }>();

  // Add semantic results
  for (const result of semanticResults) {
    combined.set(result.toolName, {
      description: result.description,
      score: result.similarity * semanticWeight,
    });
  }

  // Add/merge keyword results
  for (const result of keywordResults) {
    const existing = combined.get(result.toolName);
    if (existing) {
      // Boost score for tools appearing in both
      existing.score += result.score * keywordWeight * 1.2;
    } else {
      combined.set(result.toolName, {
        description: '',
        score: result.score * keywordWeight,
      });
    }
  }

  // Convert back to sorted array
  return Array.from(combined.entries())
    .map(([toolName, data]) => ({
      toolName,
      description: data.description,
      similarity: data.score,
    }))
    .sort((a, b) => b.similarity - a.similarity);
}
