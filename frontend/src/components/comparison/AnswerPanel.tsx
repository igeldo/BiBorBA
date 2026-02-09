interface AnswerPanelProps {
  title: string
  body: string
  score?: number
  author?: string
  isReference?: boolean
  maxHeight?: string
}

export function AnswerPanel({
  title,
  body,
  score,
  author,
  isReference = false,
  maxHeight = '400px'
}: AnswerPanelProps) {
  const bgColor = isReference ? '#e8f5e9' : '#f5f5f5'
  const borderColor = isReference ? '#c8e6c9' : '#e0e0e0'
  const titleColor = isReference ? '#2e7d32' : '#333'
  const badgeColor = isReference ? '#4caf50' : '#1976d2'

  return (
    <div style={{
      flex: 1,
      minWidth: '300px',
      backgroundColor: bgColor,
      borderRadius: '8px',
      border: `1px solid ${borderColor}`,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${borderColor}`,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap'
      }}>
        <h4 style={{ margin: 0, color: titleColor, fontSize: '14px' }}>
          {title}
        </h4>
        {isReference && (
          <span style={{
            padding: '2px 8px',
            backgroundColor: badgeColor,
            color: 'white',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 500
          }}>
            Referenz
          </span>
        )}
        {score !== undefined && (
          <span style={{
            fontSize: '12px',
            color: '#666',
            marginLeft: 'auto'
          }}>
            Score: {score}
          </span>
        )}
      </div>

      {/* Content */}
      <div style={{
        padding: '12px 16px',
        flex: 1,
        overflowY: 'auto',
        maxHeight: maxHeight
      }}>
        <div style={{
          whiteSpace: 'pre-wrap',
          fontSize: '13px',
          lineHeight: '1.6',
          color: '#333'
        }}>
          {body}
        </div>
      </div>

      {/* Footer */}
      {author && (
        <div style={{
          padding: '8px 16px',
          borderTop: `1px solid ${borderColor}`,
          fontSize: '11px',
          color: '#666'
        }}>
          {isReference ? 'Beantwortet von: ' : 'Generiert mit: '}{author}
        </div>
      )}
    </div>
  )
}
