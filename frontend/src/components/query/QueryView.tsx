import React, { useState } from 'react'
import { useQuery, useCollections } from '../../hooks'
import { CollectionSelector } from '../CollectionSelector'
import { RatingStars } from '../RatingStars'
import { DocumentCard } from '../DocumentCard'
import { GraphTrace } from '../GraphTrace'
import { getSourceColor } from '../../utils/formatting'
import { GraphType } from '../../types'

export const QueryView: React.FC = () => {
  const {
    question,
    setQuestion,
    sessionId,
    setSessionId,
    selectedGraphType,
    setSelectedGraphType,
    temperature,
    setTemperature,
    loading,
    error,
    setError,
    result,
    handleSubmit,
    resetResult
  } = useQuery()

  const {
    selectedCollections,
    setSelectedCollections,
    availableCollections
  } = useCollections(true)

  const [expandedDocs, setExpandedDocs] = useState<Set<number>>(new Set())

  const onSubmit = (e: React.FormEvent) => {
    resetResult()
    setExpandedDocs(new Set())
    handleSubmit(e, selectedCollections)
  }

  const toggleDocExpanded = (index: number) => {
    const newExpanded = new Set(expandedDocs)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedDocs(newExpanded)
  }

  return (
    <>
      {/* Query Form */}
      <div className="query-section">
        <h2>Ask a Question</h2>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label htmlFor="question">Your Question:</label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter your question here..."
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="sessionId">Session ID:</label>
            <input
              type="text"
              id="sessionId"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="temperature">Temperature (0-1):</label>
            <input
              type="number"
              id="temperature"
              min="0"
              max="1"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              disabled={loading}
            />
          </div>

          {/* Graph Type Selector */}
          <div className="form-group">
            <label htmlFor="graphType">Graph Type:</label>
            <select
              id="graphType"
              value={selectedGraphType}
              onChange={(e) => setSelectedGraphType(e.target.value as GraphType)}
              disabled={loading}
              style={{
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '14px',
                width: '100%',
                backgroundColor: '#fff'
              }}
            >
              <option value={GraphType.ADAPTIVE_RAG}>
                Adaptive RAG (Vollständig mit Grading & Rewriting)
              </option>
              <option value={GraphType.SIMPLE_RAG}>
                Simple RAG (Nur Retrieval + Generation)
              </option>
              <option value={GraphType.PURE_LLM}>
                Pure LLM (Kein Retrieval - Baseline)
              </option>
            </select>
          </div>

          {/* Collection Selector */}
          <CollectionSelector
            collections={availableCollections}
            selectedIds={selectedCollections}
            onSelectionChange={setSelectedCollections}
            disabled={loading}
          />

          <button type="submit" className="button" disabled={loading}>
            {loading && <span className="loading"></span>}
            {loading ? 'Processing...' : 'Submit Query'}
          </button>
        </form>
      </div>

      {/* Query Results */}
      {result && !loading && (
        <div className="result-section">
          <div className="result-header">
            <h2>Answer</h2>
            <div className="source-breakdown">
              {result.source_breakdown && Object.entries(result.source_breakdown).map(([source, count]) => (
                <span key={source} className="source-tag">
                  {source}: {count}
                </span>
              ))}
            </div>
          </div>

          {/* Rewritten Question Notice */}
          {result.rewritten_question && result.rewritten_question !== question && (
            <div className="rewritten-question-notice">
              <div className="notice-header">
                <span className="notice-icon">🔄</span>
                <strong>Question was optimized for better retrieval:</strong>
              </div>
              <div className="notice-content">
                <div className="original-question">
                  <strong>Original:</strong> {question}
                </div>
                <div className="rewritten-question">
                  <strong>Optimized:</strong> {result.rewritten_question}
                </div>
              </div>
            </div>
          )}

          <div className="result-content">
            <p style={{ whiteSpace: 'pre-wrap' }}>{result.answer}</p>
          </div>

          {/* Disclaimer Warning */}
          {result.iteration_metrics?.disclaimer && (
            <div style={{
              marginTop: '15px',
              padding: '12px 15px',
              backgroundColor: '#fff3cd',
              borderRadius: '4px',
              border: '1px solid #ffc107',
              color: '#856404',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px'
            }}>
              <span style={{ fontSize: '18px' }}>⚠️</span>
              <span>{result.iteration_metrics.disclaimer}</span>
            </div>
          )}

          {/* User Rating Section */}
          <RatingStars sessionId={result.session_id} />

          {/* Collection Breakdown */}
          {result.collection_breakdown && result.collection_breakdown.length > 0 && (
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px',
              border: '1px solid #dee2e6'
            }}>
              <h4 style={{ marginBottom: '10px', fontSize: '16px', fontWeight: 600 }}>
                📚 Collection Breakdown
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                {result.collection_breakdown.map((breakdown, idx) => (
                  <div key={idx} style={{
                    padding: '8px 12px',
                    backgroundColor: 'white',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                      {breakdown.collection_name}
                    </div>
                    <div style={{ fontSize: '0.9em', color: '#666' }}>
                      {breakdown.document_count} documents
                      <span style={{
                        marginLeft: '6px',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '0.85em',
                        backgroundColor: breakdown.collection_type === 'pdf' ? '#e3f2fd' : '#f3e5f5',
                        color: breakdown.collection_type === 'pdf' ? '#1976d2' : '#7b1fa2'
                      }}>
                        {breakdown.collection_type}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="metadata">
            <div className="metadata-item">
              <div className="metadata-label">Documents Retrieved</div>
              <div className="metadata-value">{result.documents_retrieved}</div>
            </div>

            {result.stackoverflow_documents !== undefined && result.stackoverflow_documents > 0 && (
              <div className="metadata-item">
                <div className="metadata-label">StackOverflow Documents</div>
                <div className="metadata-value">{result.stackoverflow_documents}</div>
              </div>
            )}

            {result.graph_type && (
              <div className="metadata-item">
                <div className="metadata-label">Graph Type</div>
                <div className="metadata-value">
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor:
                      result.graph_type === 'adaptive_rag' ? '#e3f2fd' :
                      result.graph_type === 'simple_rag' ? '#fff3e0' :
                      '#f3e5f5',
                    color:
                      result.graph_type === 'adaptive_rag' ? '#1976d2' :
                      result.graph_type === 'simple_rag' ? '#f57c00' :
                      '#7b1fa2',
                    fontWeight: 500,
                    fontSize: '13px'
                  }}>
                    {result.graph_type === 'adaptive_rag' ? 'Adaptive RAG' :
                     result.graph_type === 'simple_rag' ? 'Simple RAG' :
                     'Pure LLM'}
                  </span>
                </div>
              </div>
            )}

            <div className="metadata-item">
              <div className="metadata-label">Processing Time</div>
              <div className="metadata-value">{result.processing_time_ms}ms</div>
            </div>

            <div className="metadata-item">
              <div className="metadata-label">Session ID</div>
              <div className="metadata-value" style={{ fontSize: '12px', wordBreak: 'break-all' }}>
                {result.session_id}
              </div>
            </div>
          </div>

          {/* Iteration Metrics Section */}
          {result.iteration_metrics && (
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: result.iteration_metrics.max_iterations_reached ? '#fff3cd' : '#e8f5e9',
              borderRadius: '4px',
              border: `1px solid ${result.iteration_metrics.max_iterations_reached ? '#ffc107' : '#4caf50'}`
            }}>
              <h4 style={{
                marginBottom: '12px',
                fontSize: '16px',
                fontWeight: 600,
                color: result.iteration_metrics.max_iterations_reached ? '#856404' : '#2e7d32',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                {result.iteration_metrics.max_iterations_reached ? '⚠️' : '🔄'} Graph Iteration Metrics
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
                <div style={{
                  padding: '10px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1976d2' }}>
                    {result.iteration_metrics.total_iterations}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>Total Iterations</div>
                </div>
                <div style={{
                  padding: '10px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#388e3c' }}>
                    {result.iteration_metrics.generation_attempts}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>Generation Attempts</div>
                </div>
                <div style={{
                  padding: '10px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f57c00' }}>
                    {result.iteration_metrics.transform_attempts}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>Transform Attempts</div>
                </div>
              </div>
            </div>
          )}

          {/* Retrieved Documents Section */}
          {result.retrieved_documents && result.retrieved_documents.length > 0 && (
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px',
              border: '1px solid #dee2e6'
            }}>
              <h4 style={{
                marginBottom: '15px',
                fontSize: '16px',
                fontWeight: 600,
                color: '#495057',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                📄 Retrieved Documents ({result.retrieved_documents.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {result.retrieved_documents.map((doc, index) => (
                  <DocumentCard
                    key={index}
                    document={doc}
                    expanded={expandedDocs.has(index)}
                    onToggle={() => toggleDocExpanded(index)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Graph Trace Section */}
          {result.graph_trace && result.graph_trace.length > 0 && (
            <GraphTrace
              graphTrace={result.graph_trace}
              nodeTimings={result.node_timings}
            />
          )}

          {/* Source Breakdown Details */}
          {result.source_breakdown && Object.keys(result.source_breakdown).length > 0 && (
            <div className="source-breakdown-section">
              <h3>📊 Source Distribution</h3>
              <div className="source-breakdown-chart">
                {Object.entries(result.source_breakdown).map(([source, count]) => {
                  const percentage = (count / result.documents_retrieved * 100).toFixed(1)
                  return (
                    <div key={source} className="source-bar-container">
                      <div className="source-bar-label">
                        <span className="source-name">{source.toUpperCase()}</span>
                        <span className="source-count">{count} docs ({percentage}%)</span>
                      </div>
                      <div className="source-bar-background">
                        <div
                          className="source-bar-fill"
                          style={{
                            width: `${percentage}%`,
                            backgroundColor: getSourceColor(source)
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error">
          <strong>Error:</strong> {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: '10px', background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}
    </>
  )
}
