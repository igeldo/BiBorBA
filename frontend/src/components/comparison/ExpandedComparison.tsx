import type { EvaluationWithGraphType, AcceptedAnswerInfo } from '../../types'
import { AnswerPanel } from './AnswerPanel'
import { GraphTrace } from '../GraphTrace'
import { DocumentCard } from '../DocumentCard'
import { RatingStars } from '../RatingStars'
import { getGraphTypeName, formatDate } from './utils'

interface ExpandedComparisonProps {
  evaluation: EvaluationWithGraphType
  referenceAnswer?: AcceptedAnswerInfo
  expandedDocuments: Set<string>
  onToggleDocument: (docIndex: number) => void
}

export function ExpandedComparison({
  evaluation,
  referenceAnswer,
  expandedDocuments,
  onToggleDocument
}: ExpandedComparisonProps) {
  return (
    <tr>
      <td colSpan={6} style={{ padding: 0 }}>
        <div style={{
          padding: '20px',
          backgroundColor: '#f8fafc',
          borderTop: '2px solid #1976d2',
          borderBottom: '2px solid #1976d2'
        }}>
          {/* Metrics Summary Bar */}
          <div style={{
            display: 'flex',
            gap: '24px',
            marginBottom: '16px',
            padding: '12px 16px',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '1px solid #e0e0e0',
            flexWrap: 'wrap'
          }}>
            {evaluation.bert_f1 !== null && evaluation.bert_f1 !== undefined && (
              <div>
                <span style={{ fontSize: '11px', color: '#666', marginRight: '4px' }}>BERT F1:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_f1.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.bert_precision !== null && evaluation.bert_precision !== undefined && (
              <div>
                <span style={{ fontSize: '11px', color: '#666', marginRight: '4px' }}>Precision:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_precision.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.bert_recall !== null && evaluation.bert_recall !== undefined && (
              <div>
                <span style={{ fontSize: '11px', color: '#666', marginRight: '4px' }}>Recall:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.bert_recall.toFixed(4)}
                </span>
              </div>
            )}
            {evaluation.llm_correctness_score !== undefined && (
              <div>
                <span style={{ fontSize: '11px', color: '#666', marginRight: '4px' }}>LLM Corr.:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {evaluation.llm_correctness_score.toFixed(4)}
                </span>
                <span style={{ fontSize: '10px', color: '#999', marginLeft: '4px' }}>
                  ({(evaluation.llm_correctness_score * 4 + 1).toFixed(0)}/5)
                </span>
              </div>
            )}
            <div style={{ marginLeft: 'auto', fontSize: '11px', color: '#666' }}>
              {formatDate(evaluation.created_at)}
            </div>
          </div>

          {/* Rewritten Question */}
          {evaluation.rewritten_question && (
            <div style={{
              marginBottom: '16px',
              padding: '10px 14px',
              backgroundColor: '#fff3e0',
              borderRadius: '6px',
              border: '1px solid #ffe0b2',
              fontSize: '13px'
            }}>
              <span style={{ fontWeight: 500, color: '#e65100' }}>Query optimiert:</span>
              <span style={{ marginLeft: '8px', fontStyle: 'italic' }}>
                "{evaluation.rewritten_question}"
              </span>
            </div>
          )}

          {/* Side-by-Side Comparison */}
          <div style={{
            display: 'flex',
            gap: '16px',
            marginBottom: '16px'
          }}>
            {/* Reference Answer */}
            {referenceAnswer ? (
              <AnswerPanel
                title="Akzeptierte StackOverflow-Antwort"
                body={referenceAnswer.body}
                score={referenceAnswer.score}
                author={referenceAnswer.owner_display_name}
                isReference={true}
                maxHeight="350px"
              />
            ) : (
              <div style={{
                flex: 1,
                minWidth: '300px',
                padding: '40px',
                backgroundColor: '#f5f5f5',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
                fontStyle: 'italic'
              }}>
                Keine Referenzantwort verfügbar
              </div>
            )}

            {/* Generated Answer */}
            <AnswerPanel
              title={`Generiert (${getGraphTypeName(evaluation.graph_type)})`}
              body={evaluation.generated_answer}
              author={evaluation.llm_model}
              isReference={false}
              maxHeight="350px"
            />
          </div>

          {/* Additional Details in Collapsible Sections */}
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            {/* Graph Trace */}
            {evaluation.graph_trace && evaluation.graph_trace.length > 0 && (
              <div style={{
                flex: '1 1 400px',
                backgroundColor: 'white',
                borderRadius: '8px',
                border: '1px solid #e0e0e0',
                overflow: 'hidden'
              }}>
                <div style={{
                  padding: '10px 14px',
                  backgroundColor: '#f5f5f5',
                  borderBottom: '1px solid #e0e0e0',
                  fontWeight: 500,
                  fontSize: '13px'
                }}>
                  Graph Trace ({evaluation.graph_trace.length} Knoten)
                </div>
                <div style={{ padding: '12px' }}>
                  <GraphTrace
                    graphTrace={evaluation.graph_trace}
                    nodeTimings={evaluation.node_timings}
                  />
                </div>
              </div>
            )}

            {/* Iteration Metrics */}
            {evaluation.iteration_metrics && (
              <div style={{
                flex: '0 1 250px',
                backgroundColor: 'white',
                borderRadius: '8px',
                border: '1px solid #e0e0e0',
                overflow: 'hidden'
              }}>
                <div style={{
                  padding: '10px 14px',
                  backgroundColor: '#f5f5f5',
                  borderBottom: '1px solid #e0e0e0',
                  fontWeight: 500,
                  fontSize: '13px'
                }}>
                  Iteration Metriken
                </div>
                <div style={{ padding: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#666' }}>Gesamt-Iterationen:</span>
                      <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.total_iterations}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#666' }}>Generation-Versuche:</span>
                      <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.generation_attempts}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#666' }}>Transform-Versuche:</span>
                      <span style={{ fontWeight: 500 }}>{evaluation.iteration_metrics.transform_attempts}</span>
                    </div>
                    {evaluation.iteration_metrics.max_iterations_reached && (
                      <div style={{
                        padding: '4px 8px',
                        backgroundColor: '#ffebee',
                        color: '#c62828',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 500,
                        textAlign: 'center'
                      }}>
                        Max Iterationen erreicht!
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Retrieved Documents */}
          {evaluation.retrieved_documents && evaluation.retrieved_documents.length > 0 && (
            <div style={{
              marginTop: '16px',
              backgroundColor: 'white',
              borderRadius: '8px',
              border: '1px solid #e0e0e0',
              overflow: 'hidden'
            }}>
              <div style={{
                padding: '10px 14px',
                backgroundColor: '#f5f5f5',
                borderBottom: '1px solid #e0e0e0',
                fontWeight: 500,
                fontSize: '13px'
              }}>
                Verwendete Dokumente ({evaluation.retrieved_documents.length})
              </div>
              <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
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

          {/* Rating */}
          <div style={{
            marginTop: '16px',
            padding: '12px 16px',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '1px solid #e0e0e0',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <span style={{ fontWeight: 500, fontSize: '13px' }}>Bewertung:</span>
            <RatingStars
              evaluationId={evaluation.id}
              initialRating={evaluation.manual_rating}
              compact={true}
              onRatingSubmit={() => {}}
            />
          </div>
        </div>
      </td>
    </tr>
  )
}
