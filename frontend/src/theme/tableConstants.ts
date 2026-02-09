/**
 * Centralized table constants for consistent styling across all views
 */

export const TABLE_COLORS = {
  // Links
  link: '#1976d2',
  stackoverflow: '#f48024',

  // Scores
  scoreHigh: '#388e3c',
  scoreMedium: '#666',
  scoreLow: '#999',

  // Selection & Hover
  selectedRow: '#e3f2fd',
  hoverRow: '#f5f5f5',

  // Tags
  tagBg: '#e3f2fd',
  tagText: '#1976d2',

  // Borders
  headerBorder: '#ddd',
  rowBorder: '#f0f0f0',

  // Backgrounds
  headerBg: '#f5f5f5',

  // Buttons
  buttonPrimary: '#1976d2',
  buttonSecondary: '#6c757d',
  buttonDisabled: '#ccc',
} as const

// Unified page sizes (superset of all previously used options)
export const TABLE_PAGE_SIZES = [10, 20, 25, 50, 100, 200] as const
export const DEFAULT_PAGE_SIZE = 20

// Type for page sizes
export type TablePageSize = typeof TABLE_PAGE_SIZES[number]

/**
 * Get score color based on value
 */
export function getScoreDisplayColor(score: number, threshold = 5): string {
  return score > threshold ? TABLE_COLORS.scoreHigh : TABLE_COLORS.scoreMedium
}
