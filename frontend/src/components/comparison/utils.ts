/**
 * Utility functions for comparison components
 */

export function getGraphTypeBadgeColor(graphType: string): { bg: string; color: string } {
  switch (graphType) {
    case 'adaptive_rag':
      return { bg: '#e3f2fd', color: '#1976d2' }
    case 'simple_rag':
      return { bg: '#fff3e0', color: '#f57c00' }
    case 'pure_llm':
      return { bg: '#f3e5f5', color: '#7b1fa2' }
    default:
      return { bg: '#f5f5f5', color: '#666' }
  }
}

export function getGraphTypeName(graphType: string): string {
  switch (graphType) {
    case 'adaptive_rag':
      return 'Adaptive RAG'
    case 'simple_rag':
      return 'Simple RAG'
    case 'pure_llm':
      return 'Pure LLM'
    default:
      return graphType
  }
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('de-DE')
}

/**
 * Format processing time for display
 */
export function formatProcessingTime(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  }
  return `${(ms / 1000).toFixed(1)}s`
}

/**
 * Get a star rating display string
 */
export function getRatingStars(rating: number | undefined): string {
  if (rating === undefined || rating === null) return '-'
  const fullStars = Math.floor(rating)
  const emptyStars = 5 - fullStars
  return '★'.repeat(fullStars) + '☆'.repeat(emptyStars)
}
