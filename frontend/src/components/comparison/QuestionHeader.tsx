import { useState } from 'react'

interface QuestionHeaderProps {
  title: string
  body: string
  onRerun: () => void
  defaultExpanded?: boolean
}

export function QuestionHeader({
  title,
  body,
  onRerun,
  defaultExpanded = false
}: QuestionHeaderProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
          <h2 style={{ margin: 0 }}>Vergleich: {title}</h2>
        </div>
        <button
          onClick={onRerun}
          style={{
            padding: '10px 20px',
            backgroundColor: '#ff9800',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          Erneut ausführen
        </button>
      </div>

      {/* Question Body - only when expanded */}
      {isExpanded && (
        <div style={{
          padding: '16px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          marginBottom: '24px',
          border: '1px solid #e0e0e0'
        }}>
          <h3 style={{ marginTop: 0 }}>Frage:</h3>
          <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
            {body}
          </p>
        </div>
      )}
    </>
  )
}
