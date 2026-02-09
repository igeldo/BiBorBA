import React from 'react'
import { TABLE_COLORS } from '../../theme/tableConstants'

interface TagListProps {
  tags: string | string[] | undefined | null
  maxTags?: number
}

/**
 * Normalizes tags from string (comma-separated) or array format
 */
function normalizeTags(tags: string | string[] | undefined | null): string[] {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
}

export const TagList: React.FC<TagListProps> = ({
  tags,
  maxTags = 3
}) => {
  const normalizedTags = normalizeTags(tags)
  const displayTags = normalizedTags.slice(0, maxTags)
  const hasMore = normalizedTags.length > maxTags

  if (displayTags.length === 0) {
    return null
  }

  return (
    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
      {displayTags.map((tag, idx) => (
        <span
          key={`${tag}-${idx}`}
          style={{
            backgroundColor: TABLE_COLORS.tagBg,
            color: TABLE_COLORS.tagText,
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 500
          }}
        >
          {tag}
        </span>
      ))}
      {hasMore && (
        <span
          style={{
            color: '#999',
            fontSize: '11px',
            padding: '2px 4px'
          }}
          title={normalizedTags.join(', ')}
        >
          +{normalizedTags.length - maxTags}
        </span>
      )}
    </div>
  )
}
