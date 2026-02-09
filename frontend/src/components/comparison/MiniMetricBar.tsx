import { getBertScoreColor, getLLMCorrectnessColor } from '../../utils/formatting'

interface MiniMetricBarProps {
  value: number | null | undefined
  type: 'bert' | 'llm'
  showValue?: boolean
}

export function MiniMetricBar({ value, type, showValue = true }: MiniMetricBarProps) {
  if (value === null || value === undefined) {
    return <span style={{ color: '#999', fontSize: '12px' }}>-</span>
  }

  const color = type === 'bert' ? getBertScoreColor(value) : getLLMCorrectnessColor(value)
  const percentage = Math.round(value * 100)

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: '80px' }}>
      <div style={{
        flex: 1,
        height: '8px',
        backgroundColor: '#e0e0e0',
        borderRadius: '4px',
        overflow: 'hidden',
        minWidth: '40px'
      }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          backgroundColor: color,
          borderRadius: '4px',
          transition: 'width 0.3s ease'
        }} />
      </div>
      {showValue && (
        <span style={{
          fontSize: '11px',
          fontWeight: 'bold',
          color: 'inherit',
          minWidth: '35px',
          textAlign: 'right'
        }}>
          {value.toFixed(2)}
        </span>
      )}
    </div>
  )
}
