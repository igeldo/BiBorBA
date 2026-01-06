import React from 'react'
import type { RetrievedDocument } from '../types'

interface DocumentCardProps {
  document: RetrievedDocument
  expanded: boolean
  onToggle: () => void
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  expanded,
  onToggle
}) => {
  const getSourceStyle = (source: string) => {
    switch (source) {
      case 'pdf':
        return { bg: '#e3f2fd', color: '#1976d2' }
      case 'stackoverflow':
        return { bg: '#f3e5f5', color: '#7b1fa2' }
      default:
        return { bg: '#e8e8e8', color: '#666' }
    }
  }

  const getScoreColor = (score?: number) => {
    if (score === undefined || score === null) return undefined
    if (score > 0.7) return '#388e3c'
    if (score > 0.4) return '#f57c00'
    return '#d32f2f'
  }

  const sourceStyle = getSourceStyle(document.source)

  return (
    <div
      style={{
        backgroundColor: 'white',
        border: '1px solid #ddd',
        borderRadius: '6px',
        overflow: 'hidden'
      }}
    >
      <div
        style={{
          padding: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          cursor: 'pointer',
          backgroundColor: expanded ? '#f0f7ff' : 'white'
        }}
        onClick={onToggle}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              backgroundColor: sourceStyle.bg,
              color: sourceStyle.color
            }}>
              {document.source}
            </span>
            {document.relevance_score !== undefined && document.relevance_score !== null && (
              <span style={{
                fontSize: '12px',
                color: getScoreColor(document.relevance_score)
              }}>
                Score: {(document.relevance_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <div style={{ fontWeight: 500, fontSize: '14px', color: '#212529', marginBottom: '4px' }}>
            {document.title || 'Untitled Document'}
          </div>
          <div style={{ fontSize: '13px', color: '#666', lineHeight: 1.4 }}>
            {expanded ? document.full_content : document.content_preview}
          </div>
        </div>
        <div style={{
          marginLeft: '12px',
          color: '#007bff',
          fontSize: '18px',
          transition: 'transform 0.2s',
          transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)'
        }}>
          ▼
        </div>
      </div>
    </div>
  )
}
