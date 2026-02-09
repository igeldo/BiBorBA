import type { ComparisonMetricsSummary } from '../../types'
import { getGraphTypeBadgeColor, getGraphTypeName } from './utils'

interface MetricsSummaryProps {
  metricsData: ComparisonMetricsSummary[]
}

export function MetricsSummary({ metricsData }: MetricsSummaryProps) {
  if (metricsData.length === 0) {
    return null
  }

  return (
    <div style={{ marginBottom: '32px' }}>
      <h3>Metriken-Übersicht</h3>
      <div style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f5f5f5' }}>
              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>
                Graph Type
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Ø BERT F1
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Ø Precision
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Ø Recall
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Ø LLM Corr.
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Zeit (ms)
              </th>
              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                Anzahl
              </th>
            </tr>
          </thead>
          <tbody>
            {metricsData.map((metrics, idx) => {
              const colors = getGraphTypeBadgeColor(metrics.graph_type)
              return (
                <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '4px 12px',
                      borderRadius: '4px',
                      backgroundColor: colors.bg,
                      color: colors.color,
                      fontWeight: 500
                    }}>
                      {getGraphTypeName(metrics.graph_type)}
                    </span>
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.avg_bert_f1 !== null && metrics.avg_bert_f1 !== undefined ? (
                      <span style={{ fontWeight: 'bold' }}>
                        {metrics.avg_bert_f1.toFixed(4)}
                      </span>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.avg_bert_precision !== null && metrics.avg_bert_precision !== undefined ? (
                      <span style={{ fontWeight: 'bold' }}>
                        {metrics.avg_bert_precision.toFixed(4)}
                      </span>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.avg_bert_recall !== null && metrics.avg_bert_recall !== undefined ? (
                      <span style={{ fontWeight: 'bold' }}>
                        {metrics.avg_bert_recall.toFixed(4)}
                      </span>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.avg_llm_correctness !== null && metrics.avg_llm_correctness !== undefined ? (
                      <span style={{ fontWeight: 'bold' }}>
                        {metrics.avg_llm_correctness.toFixed(4)}
                      </span>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.avg_processing_time_ms !== null && metrics.avg_processing_time_ms !== undefined
                      ? Math.round(metrics.avg_processing_time_ms)
                      : '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {metrics.evaluation_count}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
