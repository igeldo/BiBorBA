import type { EvaluationWithGraphType } from '../../types'
import { MiniMetricBar } from './MiniMetricBar'
import { getGraphTypeBadgeColor, getGraphTypeName, formatProcessingTime } from './utils'

interface EvaluationTableRowProps {
  evaluation: EvaluationWithGraphType
  index: number
  isExpanded: boolean
  onToggleExpand: () => void
}

export function EvaluationTableRow({
  evaluation,
  index,
  isExpanded,
  onToggleExpand
}: EvaluationTableRowProps) {
  const colors = getGraphTypeBadgeColor(evaluation.graph_type)

  return (
    <tr
      style={{
        backgroundColor: isExpanded ? '#f0f7ff' : (index % 2 === 0 ? 'white' : '#fafafa'),
        borderBottom: '1px solid #eee',
        cursor: 'pointer',
        transition: 'background-color 0.15s ease'
      }}
      onClick={onToggleExpand}
    >
      {/* Index */}
      <td style={{ padding: '10px 12px', textAlign: 'center', fontSize: '12px', color: '#666' }}>
        {index + 1}
      </td>

      {/* Config (Graph Type + LLM Model) */}
      <td style={{ padding: '10px 12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{
            padding: '3px 8px',
            borderRadius: '4px',
            backgroundColor: colors.bg,
            color: colors.color,
            fontSize: '11px',
            fontWeight: 500,
            display: 'inline-block',
            width: 'fit-content'
          }}>
            {getGraphTypeName(evaluation.graph_type)}
          </span>
          {evaluation.llm_model && (
            <span style={{
              fontSize: '11px',
              color: '#666',
              fontFamily: 'monospace'
            }}>
              LLM: {evaluation.llm_model}
            </span>
          )}
          {evaluation.embedding_model && (
            <span style={{
              fontSize: '11px',
              color: '#888',
              fontFamily: 'monospace'
            }}>
              Emb: {evaluation.embedding_model}
            </span>
          )}
        </div>
      </td>

      {/* BERT F1 */}
      <td style={{ padding: '10px 12px' }}>
        <MiniMetricBar value={evaluation.bert_f1} type="bert" />
      </td>

      {/* LLM Correctness */}
      <td style={{ padding: '10px 12px' }}>
        <MiniMetricBar value={evaluation.llm_correctness_score} type="llm" />
      </td>

      {/* Processing Time */}
      <td style={{ padding: '10px 12px', textAlign: 'center', fontSize: '12px' }}>
        {evaluation.processing_time_ms
          ? formatProcessingTime(evaluation.processing_time_ms)
          : '-'
        }
      </td>

      {/* Expand Button */}
      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
        <button
          style={{
            padding: '4px 8px',
            backgroundColor: isExpanded ? '#1976d2' : '#f5f5f5',
            color: isExpanded ? 'white' : '#666',
            border: isExpanded ? 'none' : '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
            fontWeight: 500,
            transition: 'all 0.15s ease'
          }}
          onClick={(e) => {
            e.stopPropagation()
            onToggleExpand()
          }}
        >
          {isExpanded ? '▼ Vergleich' : '▶ Vergleich'}
        </button>
      </td>
    </tr>
  )
}
