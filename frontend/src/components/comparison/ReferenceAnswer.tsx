import { useState } from 'react'
import type { AcceptedAnswerInfo } from '../../types'

interface ReferenceAnswerProps {
  acceptedAnswer: AcceptedAnswerInfo
  defaultExpanded?: boolean
}

export function ReferenceAnswer({
  acceptedAnswer,
  defaultExpanded = false
}: ReferenceAnswerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div style={{
      padding: '16px',
      backgroundColor: '#e8f5e9',
      borderRadius: '8px',
      marginBottom: '24px',
      border: '1px solid #c8e6c9'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '16px',
            padding: '4px'
          }}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
        <h3 style={{ margin: 0, color: '#2e7d32' }}>
          Akzeptierte StackOverflow-Antwort
        </h3>
        <span style={{
          padding: '4px 8px',
          backgroundColor: '#4caf50',
          color: 'white',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 500
        }}>
          Referenz
        </span>
        <span style={{
          fontSize: '14px',
          color: '#666'
        }}>
          Score: {acceptedAnswer.score}
        </span>
      </div>

      {/* Answer body - only when expanded */}
      {isExpanded && (
        <>
          <div style={{
            padding: '12px',
            backgroundColor: 'white',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            fontSize: '14px',
            lineHeight: '1.6',
            maxHeight: '400px',
            overflowY: 'auto',
            marginTop: '12px'
          }}>
            {acceptedAnswer.body}
          </div>
          {acceptedAnswer.owner_display_name && (
            <div style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#666'
            }}>
              Beantwortet von: {acceptedAnswer.owner_display_name}
            </div>
          )}
        </>
      )}
    </div>
  )
}
