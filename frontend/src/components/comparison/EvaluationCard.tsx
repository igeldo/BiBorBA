import type { EvaluationWithGraphType } from '../../types'
import { GraphTrace } from '../GraphTrace'
import { DocumentCard } from '../DocumentCard'
import { RatingStars } from '../RatingStars'
import { formatDate } from './utils'

interface EvaluationCardProps {
  evaluation: EvaluationWithGraphType
  isExpanded: boolean
  expandedDocuments: Set<string>
  onToggleExpand: () => void
  onToggleDocument: (docIndex: number) => void
}

export function EvaluationCard({
  evaluation,
  isExpanded,
  expandedDocuments,
  onToggleExpand,
  onToggleDocument
}: EvaluationCardProps) {
  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderTop: 'none',
        padding: '16px',
        backgroundColor: 'white'
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          cursor: 'pointer'
        }}
        onClick={onToggleExpand}
      >
        <div style={{ flex: 1 }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '12px',
            marginBottom: '8px'
          }}>
            {evaluation.bert_f1 !== null && evaluation.bert_f1 !== undefined && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>BERT F1: </span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_f1.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.bert_precision !== null && evaluation.bert_precision !== undefined && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>Precision: </span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_precision.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.bert_recall !== null && evaluation.bert_recall !== undefined && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>Recall: </span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_recall.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.processing_time_ms && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>Zeit: </span>
                <span style={{ fontWeight: 500 }}>{evaluation.processing_time_ms}ms</span>
              </div>
            )}
            {evaluation.llm_model && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>Modell: </span>
                <span style={{
                  fontWeight: 500,
                  padding: '2px 6px',
                  backgroundColor: '#f0f0f0',
                  borderRadius: '3px'
                }}>
                  {evaluation.llm_model}
                </span>
              </div>
            )}
            {evaluation.llm_correctness_score !== undefined && (
              <div>
                <span style={{ fontSize: '12px', color: '#666' }}>LLM Corr.: </span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.llm_correctness_score.toFixed(4)}
                </span>
                <span style={{ color: '#666', marginLeft: '4px', fontSize: '12px' }}>
                  ({(evaluation.llm_correctness_score * 4 + 1).toFixed(0)}/5)
                </span>
                {evaluation.llm_correctness_model && (
                  <span style={{ fontSize: '11px', color: '#999', marginLeft: '6px' }}>
                    via {evaluation.llm_correctness_model}
                  </span>
                )}
              </div>
            )}
            <div>
              <span style={{ fontSize: '12px', color: '#666' }}>Erstellt: </span>
              <span style={{ fontSize: '12px' }}>{formatDate(evaluation.created_at)}</span>
            </div>
          </div>
        </div>
        <button
          style={{
            padding: '4px 12px',
            backgroundColor: '#f5f5f5',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {isExpanded ? '▼ Einklappen' : '▶ Erweitern'}
        </button>
      </div>

      {isExpanded && (
        <div style={{
          marginTop: '16px',
          paddingTop: '16px',
          borderTop: '1px solid #eee'
        }}>
          {/* Rewritten Question */}
          {evaluation.rewritten_question && (
            <div style={{
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: '#fff3e0',
              borderRadius: '4px',
              border: '1px solid #ffe0b2'
            }}>
              <span style={{ fontWeight: 500, color: '#e65100' }}>
                Query optimiert:
              </span>
              <span style={{ marginLeft: '8px', fontStyle: 'italic' }}>
                "{evaluation.rewritten_question}"
              </span>
            </div>
          )}

          {/* Generated Answer */}
          <h5 style={{ marginTop: 0 }}>Generierte Antwort:</h5>
          <div style={{
            padding: '12px',
            backgroundColor: '#f9f9f9',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            fontSize: '14px',
            lineHeight: '1.6',
            marginBottom: '16px'
          }}>
            {evaluation.generated_answer}
          </div>

          {/* Graph Trace */}
          {evaluation.graph_trace && evaluation.graph_trace.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <h5 style={{ marginTop: 0, marginBottom: '12px' }}>
                Graph Trace ({evaluation.graph_trace.length} Knoten):
              </h5>
              <GraphTrace
                graphTrace={evaluation.graph_trace}
                nodeTimings={evaluation.node_timings}
              />
            </div>
          )}

          {/* Iteration Metrics */}
          {evaluation.iteration_metrics && (
            <div style={{
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: '#f5f5f5',
              borderRadius: '4px'
            }}>
              <h5 style={{ marginTop: 0, marginBottom: '8px' }}>Iteration Metriken:</h5>
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', fontSize: '13px' }}>
                <div>
                  <span style={{ color: '#666' }}>Gesamt-Iterationen: </span>
                  <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.total_iterations}</span>
                </div>
                <div>
                  <span style={{ color: '#666' }}>Generation-Versuche: </span>
                  <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.generation_attempts}</span>
                </div>
                <div>
                  <span style={{ color: '#666' }}>Transform-Versuche: </span>
                  <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.transform_attempts}</span>
                </div>
                {evaluation.iteration_metrics.max_iterations_reached && (
                  <div style={{ color: '#d32f2f', fontWeight: 500 }}>
                    Max Iterationen erreicht!
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Retrieved Documents */}
          {evaluation.retrieved_documents && evaluation.retrieved_documents.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <h5 style={{ marginTop: 0, marginBottom: '12px' }}>
                Verwendete Dokumente ({evaluation.retrieved_documents.length}):
              </h5>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {evaluation.retrieved_documents.map((doc, idx) => (
                  <DocumentCard
                    key={idx}
                    document={doc}
                    expanded={expandedDocuments.has(`${evaluation.id}-${idx}`)}
                    onToggle={() => onToggleDocument(idx)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Rating Stars */}
          <div style={{ marginTop: '16px' }}>
            <RatingStars
              evaluationId={evaluation.id}
              initialRating={evaluation.manual_rating}
              compact={true}
              onRatingSubmit={() => {}}
            />
          </div>
        </div>
      )}
    </div>
  )
}
