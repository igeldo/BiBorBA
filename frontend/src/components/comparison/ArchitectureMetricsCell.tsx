import type { ArchitectureMetrics } from '../../types'

interface ArchitectureMetricsCellProps {
  metrics?: ArchitectureMetrics
}

/**
 * Compact cell for displaying architecture-specific metrics in the question list.
 * Shows average BERT F1 and LLM Correctness values, or "-" if not available.
 */
export function ArchitectureMetricsCell({ metrics }: ArchitectureMetricsCellProps) {
  if (!metrics) {
    return (
      <div style={{
        color: '#999',
        fontSize: '13px',
        textAlign: 'center'
      }}>
        -
      </div>
    )
  }

  const hasBertF1 = metrics.avg_bert_f1 !== null && metrics.avg_bert_f1 !== undefined
  const hasLLMCorr = metrics.avg_llm_correctness !== null && metrics.avg_llm_correctness !== undefined

  if (!hasBertF1 && !hasLLMCorr) {
    return (
      <div style={{
        color: '#999',
        fontSize: '13px',
        textAlign: 'center'
      }}>
        -
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
      fontSize: '12px'
    }}>
      {hasBertF1 && (
        <MetricRow
          label="F1"
          value={metrics.avg_bert_f1!}
          color={getMetricColor(metrics.avg_bert_f1!)}
        />
      )}
      {hasLLMCorr && (
        <MetricRow
          label="LLM"
          value={metrics.avg_llm_correctness!}
          color={getMetricColor(metrics.avg_llm_correctness!)}
        />
      )}
    </div>
  )
}

interface MetricRowProps {
  label: string
  value: number
  color: string
}

function MetricRow({ label, value, color }: MetricRowProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '4px'
    }}>
      <span style={{
        color: '#666',
        minWidth: '26px'
      }}>
        {label}:
      </span>
      <span style={{
        fontWeight: 600,
        color: color
      }}>
        {value.toFixed(2)}
      </span>
    </div>
  )
}

function getMetricColor(value: number): string {
  // Color scale: red (low) -> orange -> green (high)
  if (value >= 0.8) return '#2e7d32' // Green
  if (value >= 0.6) return '#558b2f' // Light green
  if (value >= 0.4) return '#f9a825' // Orange
  if (value >= 0.2) return '#ef6c00' // Dark orange
  return '#c62828' // Red
}
