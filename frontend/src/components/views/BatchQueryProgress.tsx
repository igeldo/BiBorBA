import React, { useState, useEffect } from 'react'
import { apiService } from '../../services/api'
import type { BatchQueryJobStatus } from '../../types'
import { GraphTrace } from '../GraphTrace'
import { StackOverflowLink } from '../table'
import { TABLE_COLORS } from '../../theme/tableConstants'

interface BatchQueryProgressProps {
  jobId: string
  onBack?: (jobStatus: string) => void
}

export const BatchQueryProgress: React.FC<BatchQueryProgressProps> = ({ jobId, onBack }) => {
  const [job, setJob] = useState<BatchQueryJobStatus | null>(null)
  const [polling, setPolling] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  const toggleRow = (questionId: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId)
    } else {
      newExpanded.add(questionId)
    }
    setExpandedRows(newExpanded)
  }

  useEffect(() => {
    if (!jobId) return

    const fetchStatus = async () => {
      try {
        const status = await apiService.getBatchQueryStatus(jobId)
        setJob(status)

        // Stop polling when job finishes
        if (['completed', 'failed', 'cancelled'].includes(status.status)) {
          setPolling(false)
        }
      } catch (error) {
        console.error('Failed to fetch job status:', error)
        setError(error instanceof Error ? error.message : 'Failed to fetch job status')
        setPolling(false)
      }
    }

    // Initial fetch
    fetchStatus()

    // Poll every 2 seconds if still running
    let interval: number | null = null
    if (polling) {
      interval = setInterval(fetchStatus, 2000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [jobId, polling])

  if (!job && !error) {
    return (
      <div className="query-section" style={{ textAlign: 'center', padding: '40px' }}>
        <span className="loading"></span>
        <p>Job-Status wird geladen...</p>
      </div>
    )
  }

  if (error && !job) {
    return (
      <div className="query-section">
        <div className="error">
          <strong>Error:</strong> {error}
        </div>
        {onBack && (
          <button onClick={() => onBack('failed')} style={{ marginTop: '20px' }}>
            ← Zurück zur Auswahl
          </button>
        )}
      </div>
    )
  }

  if (!job) return null

  const progressPercent = (job.progress.processed / job.progress.total_questions) * 100

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return TABLE_COLORS.buttonPrimary
      case 'completed': return TABLE_COLORS.scoreHigh
      case 'failed': return '#dc3545'
      case 'cancelled': return TABLE_COLORS.buttonSecondary
      default: return TABLE_COLORS.buttonSecondary
    }
  }

  const getResultBadgeColor = (status: string) => {
    switch (status) {
      case 'success': return TABLE_COLORS.scoreHigh
      case 'failed': return '#dc3545'
      case 'skipped': return '#ffc107'
      default: return TABLE_COLORS.buttonSecondary
    }
  }

  const downloadResults = () => {
    const dataStr = JSON.stringify(job.results, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `batch_results_${jobId}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const downloadCSV = () => {
    const headers = ['Question ID', 'Title', 'Status', 'BERT F1', 'BERT Precision', 'BERT Recall', 'LLM Correctness', 'Processing Time (ms)']
    const rows = job.results.map(r => [
      r.question_id,
      `"${r.question_title.replace(/"/g, '""')}"`,
      r.status,
      r.bert_score?.f1.toFixed(3) || '',
      r.bert_score?.precision.toFixed(3) || '',
      r.bert_score?.recall.toFixed(3) || '',
      r.llm_correctness?.score.toFixed(3) || '',
      r.processing_time_ms || ''
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(r => r.join(','))
    ].join('\n')

    const dataBlob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `batch_results_${jobId}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="batch-progress-view">
      <div className="query-section">
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px'
        }}>
          <div>
            <h2>📊 Batch-Abfrage-Fortschritt</h2>
            <p style={{ color: '#666', fontSize: '14px', margin: '5px 0' }}>Job-ID: {jobId}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                padding: '8px 16px',
                borderRadius: '20px',
                fontWeight: 'bold',
                color: 'white',
                background: getStatusColor(job.status),
                textTransform: 'uppercase',
                fontSize: '14px'
              }}
            >
              {job.status}
            </span>
            {onBack && (
              <button
                onClick={() => onBack(job.status)}
                style={{ background: '#6c757d' }}
              >
                ← Back
              </button>
            )}
          </div>
        </div>

        {/* Progress Section */}
        <div style={{
          padding: '20px',
          background: '#f8f9fa',
          borderRadius: '8px',
          marginBottom: '20px',
          border: '2px solid #dee2e6'
        }}>
          <div style={{ marginBottom: '15px' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '8px',
              fontSize: '14px',
              fontWeight: 500
            }}>
              <span>Fortschritt</span>
              <span>{job.progress.processed} / {job.progress.total_questions} Fragen</span>
            </div>
            <div style={{
              width: '100%',
              height: '30px',
              background: '#e9ecef',
              borderRadius: '15px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: '100%',
                  background: `linear-gradient(90deg, ${getStatusColor(job.status)}, ${getStatusColor(job.status)}dd)`,
                  transition: 'width 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '14px'
                }}
              >
                {progressPercent.toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Stats */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '15px',
            marginTop: '15px'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745' }}>
                {job.progress.successful}
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                ✓ Erfolgreich
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc3545' }}>
                {job.progress.failed}
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                ✗ Fehlgeschlagen
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffc107' }}>
                {job.progress.skipped}
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                ⊘ Übersprungen
              </div>
            </div>
          </div>

          {/* Current Question */}
          {job.status === 'running' && job.progress.current_question_title && (
            <div style={{
              marginTop: '15px',
              padding: '10px',
              background: 'white',
              borderRadius: '4px',
              borderLeft: '4px solid #007bff'
            }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                Wird gerade verarbeitet:
              </div>
              <div style={{ fontWeight: 500 }}>
                {job.progress.current_question_title}
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        <div style={{
          background: 'white',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px'
          }}>
            <h3 style={{ margin: 0 }}>Ergebnisse ({job.results.length})</h3>
            {job.status === 'completed' && job.results.length > 0 && (
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={downloadCSV} style={{ background: '#28a745' }}>
                  CSV herunterladen
                </button>
                <button onClick={downloadResults} style={{ background: '#007bff' }}>
                  JSON herunterladen
                </button>
              </div>
            )}
          </div>

          {job.results.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              <p>Noch keine Ergebnisse. Verarbeitung beginnt in Kürze...</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px'
              }}>
                <thead>
                  <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                    <th style={{ padding: '12px', textAlign: 'center', width: '40px' }}>▼</th>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Frage</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Status</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>BERT F1</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Precision</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Recall</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>LLM Corr.</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Zeit (ms)</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Aktionen</th>
                  </tr>
                </thead>
                <tbody>
                  {job.results.map((result, idx) => (
                    <React.Fragment key={idx}>
                      {/* Main Row - Clickable */}
                      <tr
                        onClick={() => toggleRow(result.question_id)}
                        style={{
                          borderBottom: '1px solid #f0f0f0',
                          cursor: 'pointer',
                          transition: 'background-color 0.2s',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = '#f8f9fa'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent'
                        }}
                      >
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{ fontSize: '16px', color: '#666' }}>
                            {expandedRows.has(result.question_id) ? '▼' : '▶'}
                          </span>
                        </td>
                        <td style={{ padding: '12px', maxWidth: '400px' }}>
                          <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                            {result.stack_overflow_id ? (
                              <>
                                <StackOverflowLink
                                  stackOverflowId={result.stack_overflow_id}
                                  title={result.question_title}
                                />
                                {' '}({result.graph_type})
                              </>
                            ) : `${result.question_title} (${result.graph_type})`}
                          </div>
                          {result.error_message && (
                            <div style={{ fontSize: '12px', color: '#dc3545', marginTop: '4px' }}>
                              Error: {result.error_message}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '12px',
                            fontSize: '12px',
                            fontWeight: 'bold',
                            color: 'white',
                            background: getResultBadgeColor(result.status),
                            textTransform: 'uppercase'
                          }}>
                            {result.status}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.bert_score ? (
                            <span style={{ fontWeight: 'bold', fontSize: '16px' }}>
                              {result.bert_score.f1.toFixed(3)}
                            </span>
                          ) : (
                            <span style={{ color: '#999' }}>-</span>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.bert_score ? (
                            <span style={{ fontWeight: 'bold' }}>
                              {result.bert_score.precision.toFixed(3)}
                            </span>
                          ) : (
                            <span style={{ color: '#999' }}>-</span>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.bert_score ? (
                            <span style={{ fontWeight: 'bold' }}>
                              {result.bert_score.recall.toFixed(3)}
                            </span>
                          ) : (
                            <span style={{ color: '#999' }}>-</span>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.llm_correctness ? (
                            <span style={{ fontWeight: 'bold', fontSize: '16px' }}>
                              {result.llm_correctness.score.toFixed(3)}
                            </span>
                          ) : (
                            <span style={{ color: '#999' }}>-</span>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.processing_time_ms || <span style={{ color: '#999' }}>-</span>}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          {result.evaluation_id && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation() // Prevent row toggle
                                alert(`Evaluierungs-ID: ${result.evaluation_id}`)
                              }}
                              style={{
                                padding: '4px 12px',
                                fontSize: '12px',
                                background: '#007bff'
                              }}
                            >
                              Details
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Details Row */}
                      {expandedRows.has(result.question_id) && (
                        <tr key={`${idx}-details`}>
                          <td colSpan={9} style={{
                            padding: '20px',
                            backgroundColor: '#f9f9f9',
                            borderTop: '2px solid #ddd',
                            borderBottom: '2px solid #ddd'
                          }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                              {/* BERT Scores Summary */}
                              {result.bert_score && (
                                <div style={{
                                  padding: '12px 16px',
                                  backgroundColor: '#e8f5e9',
                                  borderRadius: '4px',
                                  border: '1px solid #c8e6c9'
                                }}>
                                  <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#2e7d32' }}>
                                    BERT Score Details
                                  </div>
                                  <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>F1: </span>
                                      <span style={{ fontWeight: 'bold' }}>
                                        {result.bert_score.f1.toFixed(4)}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>Precision: </span>
                                      <span style={{ fontWeight: 'bold' }}>
                                        {result.bert_score.precision.toFixed(4)}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>Recall: </span>
                                      <span style={{ fontWeight: 'bold' }}>
                                        {result.bert_score.recall.toFixed(4)}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* LLM Correctness */}
                              {result.llm_correctness && (
                                <div style={{
                                  padding: '12px 16px',
                                  backgroundColor: '#e3f2fd',
                                  borderRadius: '4px',
                                  border: '1px solid #bbdefb'
                                }}>
                                  <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1565c0' }}>
                                    LLM Correctness
                                  </div>
                                  <div>
                                    <span style={{ color: '#666', fontSize: '12px' }}>Score: </span>
                                    <span style={{ fontWeight: 'bold' }}>
                                      {result.llm_correctness.score.toFixed(4)}
                                    </span>
                                    <span style={{ color: '#666', marginLeft: '8px' }}>
                                      ({(result.llm_correctness.score * 4 + 1).toFixed(0)}/5)
                                    </span>
                                  </div>
                                  <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                    Model: {result.llm_correctness.model}
                                  </div>
                                </div>
                              )}

                              {/* Question Body Section (first, collapsed) */}
                              {result.question_body && (
                                <details>
                                  <summary style={{
                                    fontWeight: 'bold',
                                    cursor: 'pointer',
                                    fontSize: '0.9em',
                                    color: '#2c3e50',
                                    padding: '8px',
                                    backgroundColor: '#e9ecef',
                                    borderRadius: '4px',
                                    listStyle: 'none'
                                  }}>
                                    ❓ Vollständige Frage
                                  </summary>
                                  <div style={{
                                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                    fontSize: '0.85em',
                                    whiteSpace: 'pre-wrap',
                                    backgroundColor: '#ffffff',
                                    padding: '15px',
                                    borderRadius: '4px',
                                    border: '1px solid #dee2e6',
                                    maxHeight: '300px',
                                    overflowY: 'auto',
                                    marginTop: '8px'
                                  }}>
                                    {result.question_body}
                                  </div>
                                </details>
                              )}

                              {/* Generated Answer Section (open by default) */}
                              <details open>
                                <summary style={{
                                  fontWeight: 'bold',
                                  cursor: 'pointer',
                                  fontSize: '0.9em',
                                  color: '#2c3e50',
                                  padding: '8px',
                                  backgroundColor: '#e9ecef',
                                  borderRadius: '4px',
                                  listStyle: 'none'
                                }}>
                                  🤖 Generierte Antwort
                                </summary>
                                <div style={{
                                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                  fontSize: '0.85em',
                                  whiteSpace: 'pre-wrap',
                                  backgroundColor: '#ffffff',
                                  padding: '15px',
                                  borderRadius: '4px',
                                  border: '1px solid #dee2e6',
                                  maxHeight: '400px',
                                  overflowY: 'auto',
                                  marginTop: '8px'
                                }}>
                                  {result.generated_answer || (
                                    <span style={{ color: '#999', fontStyle: 'italic' }}>
                                      Keine Antwort generiert
                                    </span>
                                  )}
                                </div>
                              </details>

                              {/* StackOverflow Reference Answer Section (collapsed) */}
                              {result.reference_answer && (
                                <details>
                                  <summary style={{
                                    fontWeight: 'bold',
                                    cursor: 'pointer',
                                    fontSize: '0.9em',
                                    color: '#2c3e50',
                                    padding: '8px',
                                    backgroundColor: '#e9ecef',
                                    borderRadius: '4px',
                                    listStyle: 'none'
                                  }}>
                                    📚 StackOverflow Referenz
                                  </summary>
                                  <div style={{
                                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                    fontSize: '0.85em',
                                    whiteSpace: 'pre-wrap',
                                    backgroundColor: '#ffffff',
                                    padding: '15px',
                                    borderRadius: '4px',
                                    border: '1px solid #dee2e6',
                                    maxHeight: '400px',
                                    overflowY: 'auto',
                                    marginTop: '8px'
                                  }}>
                                    {result.reference_answer}
                                  </div>
                                </details>
                              )}

                              {/* Iteration Metrics Section */}
                              {result.iteration_metrics && (
                                <div style={{
                                  padding: '12px 16px',
                                  backgroundColor: result.iteration_metrics.max_iterations_reached ? '#fff3cd' : '#e3f2fd',
                                  borderRadius: '4px',
                                  border: `1px solid ${result.iteration_metrics.max_iterations_reached ? '#ffc107' : '#bbdefb'}`
                                }}>
                                  <div style={{
                                    fontWeight: 'bold',
                                    marginBottom: '8px',
                                    color: result.iteration_metrics.max_iterations_reached ? '#856404' : '#1565c0',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                  }}>
                                    {result.iteration_metrics.max_iterations_reached ? '⚠️' : '🔄'} Iteration Metrics
                                    {result.iteration_metrics.max_iterations_reached && (
                                      <span style={{
                                        padding: '2px 8px',
                                        backgroundColor: '#ffc107',
                                        color: '#856404',
                                        borderRadius: '4px',
                                        fontSize: '11px',
                                        fontWeight: 'bold'
                                      }}>
                                        MAX ITERATIONS
                                      </span>
                                    )}
                                  </div>
                                  <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>Total Iterations: </span>
                                      <span style={{ fontWeight: 'bold', color: '#1976d2' }}>
                                        {result.iteration_metrics.total_iterations}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>Generation Attempts: </span>
                                      <span style={{ fontWeight: 'bold', color: '#388e3c' }}>
                                        {result.iteration_metrics.generation_attempts}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: '#666', fontSize: '12px' }}>Transform Attempts: </span>
                                      <span style={{ fontWeight: 'bold', color: '#f57c00' }}>
                                        {result.iteration_metrics.transform_attempts}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Node Timings Section */}
                              {result.node_timings && Object.keys(result.node_timings).length > 0 && (
                                <div style={{
                                  padding: '12px 16px',
                                  backgroundColor: '#f5f5f5',
                                  borderRadius: '4px',
                                  border: '1px solid #e0e0e0'
                                }}>
                                  <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#555' }}>
                                    Node Timings
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                                    {Object.entries(result.node_timings).map(([node, time]) => (
                                      <div key={node} style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>{node}:</span>
                                        <span style={{ fontWeight: 500 }}>{time.toFixed(0)}ms</span>
                                      </div>
                                    ))}
                                    <div style={{
                                      borderTop: '1px solid #ddd',
                                      marginTop: '4px',
                                      paddingTop: '4px',
                                      display: 'flex',
                                      justifyContent: 'space-between',
                                      fontWeight: 'bold'
                                    }}>
                                      <span>Gesamt:</span>
                                      <span>{Object.values(result.node_timings).reduce((a, b) => a + b, 0).toFixed(0)}ms</span>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Graph Trace Section */}
                              {result.graph_trace && result.graph_trace.length > 0 && (
                                <details>
                                  <summary style={{
                                    fontWeight: 'bold',
                                    cursor: 'pointer',
                                    fontSize: '0.9em',
                                    color: '#2c3e50',
                                    padding: '8px',
                                    backgroundColor: '#e9ecef',
                                    borderRadius: '4px',
                                    listStyle: 'none'
                                  }}>
                                    🔄 Graph Trace ({result.graph_trace.length} Knoten)
                                  </summary>
                                  <div style={{ marginTop: '8px' }}>
                                    <GraphTrace graphTrace={result.graph_trace} nodeTimings={result.node_timings} />
                                  </div>
                                </details>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Error Display */}
        {job.error && (
          <div className="error" style={{ marginTop: '20px' }}>
            <strong>Job-Fehler:</strong> {job.error}
          </div>
        )}

        {/* Timing Info */}
        <div style={{
          marginTop: '20px',
          padding: '15px',
          background: '#f8f9fa',
          borderRadius: '8px',
          fontSize: '14px',
          color: '#666'
        }}>
          <div style={{ marginBottom: '5px' }}>
            <strong>Gestartet:</strong> {new Date(job.started_at).toLocaleString()}
          </div>
          {job.completed_at && (
            <div>
              <strong>Abgeschlossen:</strong> {new Date(job.completed_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
