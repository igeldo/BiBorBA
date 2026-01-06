/**
 * Centralized color definitions for consistent styling
 */

export const graphTypeColors = {
  adaptive_rag: { bg: '#e3f2fd', text: '#1976d2', border: '#1976d2' },
  simple_rag: { bg: '#fff3e0', text: '#f57c00', border: '#f57c00' },
  pure_llm: { bg: '#f3e5f5', text: '#7b1fa2', border: '#7b1fa2' },
} as const

export const sourceColors = {
  pdf: { bg: '#e3f2fd', text: '#1976d2' },
  stackoverflow: { bg: '#f3e5f5', text: '#7b1fa2' },
  default: { bg: '#e8e8e8', text: '#666' },
} as const

export const confidenceColors = {
  high: '#28a745',      // >= 0.8
  medium: '#ffc107',    // >= 0.6
  low: '#fd7e14',       // >= 0.4
  veryLow: '#dc3545',   // < 0.4
} as const

export const scoreColors = {
  good: '#388e3c',      // > 0.7
  medium: '#f57c00',    // > 0.4
  poor: '#d32f2f',      // <= 0.4
} as const

export const statusColors = {
  success: '#28a745',
  warning: '#ffc107',
  error: '#dc3545',
  info: '#007bff',
} as const

// Type definitions for type-safe access
export type GraphType = keyof typeof graphTypeColors
export type SourceType = keyof typeof sourceColors

interface ColorPair {
  bg: string
  text: string
  border?: string
}

/**
 * Get colors for a graph type
 */
export function getGraphTypeColors(type: string): ColorPair {
  return graphTypeColors[type as GraphType] || graphTypeColors.adaptive_rag
}

/**
 * Get colors for a source type
 */
export function getSourceColors(source: string): ColorPair {
  return sourceColors[source as SourceType] || sourceColors.default
}

/**
 * Get confidence color based on score
 */
export function getConfidenceColor(score: number): string {
  if (score >= 0.8) return confidenceColors.high
  if (score >= 0.6) return confidenceColors.medium
  if (score >= 0.4) return confidenceColors.low
  return confidenceColors.veryLow
}

/**
 * Get score color based on relevance score
 */
export function getScoreColor(score: number): string {
  if (score > 0.7) return scoreColors.good
  if (score > 0.4) return scoreColors.medium
  return scoreColors.poor
}
