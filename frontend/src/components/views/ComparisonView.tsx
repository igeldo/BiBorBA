import { useState, useEffect, useCallback } from 'react'
import { apiService } from '../../services/api'
import type {
  GraphComparisonResponse,
  ComparisonMetricsSummary,
  EvaluationWithGraphType,
  PaginatedEvaluatedQuestionsResponse,
  Collection,
  BatchQueryJobStatus
} from '../../types'
import { getBertScoreColor } from '../../utils/formatting'
import { RatingStars } from '../RatingStars'
import { DocumentCard } from '../DocumentCard'
import { GraphTrace } from '../GraphTrace'

export function ComparisonView() {
  const [paginatedData, setPaginatedData] = useState<PaginatedEvaluatedQuestionsResponse | null>(null)
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null)
  const [comparisonData, setComparisonData] = useState<GraphComparisonResponse | null>(null)
  const [metricsData, setMetricsData] = useState<ComparisonMetricsSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedEvaluations, setExpandedEvaluations] = useState<Set<number>>(new Set())
  const [expandedDocuments, setExpandedDocuments] = useState<Set<string>>(new Set())

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Filter state
  const [filterMultipleGraphTypes, setFilterMultipleGraphTypes] = useState(true)
  const [tagFilter, setTagFilter] = useState('')
  const [minScoreFilter, setMinScoreFilter] = useState<number | null>(null)
  const [titleSearch, setTitleSearch] = useState('')

  // Sort state
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState('desc')

  // Rerun Modal state
  const [showRerunModal, setShowRerunModal] = useState(false)
  const [rerunGraphTypes, setRerunGraphTypes] = useState<string[]>(['adaptive_rag'])
  const [rerunCollections, setRerunCollections] = useState<number[]>([])
  const [rerunJobId, setRerunJobId] = useState<string | null>(null)
  const [rerunJobStatus, setRerunJobStatus] = useState<BatchQueryJobStatus | null>(null)
  const [rerunLoading, setRerunLoading] = useState(false)
  const [availableCollections, setAvailableCollections] = useState<Collection[]>([])

  // Load evaluated questions on mount and when filters change
  useEffect(() => {
    loadEvaluatedQuestions()
  }, [currentPage, pageSize, filterMultipleGraphTypes, sortBy, sortOrder])

  const loadEvaluatedQuestions = async () => {
    try {
      setLoading(true)
      const result = await apiService.getAllEvaluatedQuestions({
        page: currentPage,
        page_size: pageSize,
        has_multiple_graph_types: filterMultipleGraphTypes,
        sort_by: sortBy,
        sort_order: sortOrder,
        tags: tagFilter || undefined,
        min_score: minScoreFilter ?? undefined,
        title_search: titleSearch || undefined
      })
      setPaginatedData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }

  // Trigger search when filters change (with debounce effect)
  const handleFilterSearch = () => {
    setCurrentPage(1)
    loadEvaluatedQuestions()
  }

  // Handle column header click for sorting
  const handleColumnSort = (column: string) => {
    if (sortBy === column) {
      // Toggle order if same column
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      // New column, default to descending
      setSortBy(column)
      setSortOrder('desc')
    }
    setCurrentPage(1)
  }

  // Rerun feature functions
  const loadCollections = useCallback(async () => {
    try {
      const collections = await apiService.getCollectionsList()
      setAvailableCollections(collections)
    } catch (err) {
      console.error('Failed to load collections:', err)
    }
  }, [])

  const openRerunModal = () => {
    loadCollections()
    setRerunGraphTypes(['adaptive_rag'])
    setRerunCollections([])
    setRerunJobId(null)
    setRerunJobStatus(null)
    setShowRerunModal(true)
  }

  const closeRerunModal = () => {
    setShowRerunModal(false)
    setRerunJobId(null)
    setRerunJobStatus(null)
    setRerunLoading(false)
  }

  const toggleGraphType = (graphType: string) => {
    setRerunGraphTypes(prev =>
      prev.includes(graphType)
        ? prev.filter(gt => gt !== graphType)
        : [...prev, graphType]
    )
  }

  const toggleCollection = (collectionId: number) => {
    setRerunCollections(prev =>
      prev.includes(collectionId)
        ? prev.filter(id => id !== collectionId)
        : [...prev, collectionId]
    )
  }

  const startRerun = async () => {
    if (!selectedQuestionId || rerunGraphTypes.length === 0) return

    setRerunLoading(true)
    try {
      const response = await apiService.rerunQuestionEvaluation(selectedQuestionId, {
        graph_types: rerunGraphTypes,
        collection_ids: rerunCollections.length > 0 ? rerunCollections : undefined,
        session_id: `rerun_${Date.now()}`
      })

      setRerunJobId(response.job_id)

      // Start polling for job status
      pollRerunStatus(response.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start rerun')
      setRerunLoading(false)
    }
  }

  const pollRerunStatus = async (jobId: string) => {
    try {
      const status = await apiService.getBatchQueryStatus(jobId)
      setRerunJobStatus(status)

      if (status.status === 'running') {
        // Continue polling
        setTimeout(() => pollRerunStatus(jobId), 1000)
      } else if (status.status === 'completed') {
        setRerunLoading(false)
        // Reload comparison data to show new evaluations
        if (selectedQuestionId) {
          await loadComparisonData(selectedQuestionId)
        }
      } else if (status.status === 'failed') {
        setRerunLoading(false)
        setError(status.error || 'Rerun failed')
      }
    } catch (err) {
      setRerunLoading(false)
      setError(err instanceof Error ? err.message : 'Failed to get rerun status')
    }
  }

  const loadComparisonData = async (questionId: number) => {
    try {
      setLoading(true)
      setError(null)

      const [comparison, metrics] = await Promise.all([
        apiService.getComparisonForQuestion(questionId),
        apiService.getComparisonMetrics(questionId)
      ])

      setComparisonData(comparison)
      setMetricsData(metrics)
      setSelectedQuestionId(questionId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comparison data')
    } finally {
      setLoading(false)
    }
  }

  const toggleEvaluationExpanded = (evaluationId: number) => {
    const newExpanded = new Set(expandedEvaluations)
    if (newExpanded.has(evaluationId)) {
      newExpanded.delete(evaluationId)
    } else {
      newExpanded.add(evaluationId)
    }
    setExpandedEvaluations(newExpanded)
  }

  const toggleDocumentExpanded = (evaluationId: number, docIndex: number) => {
    const key = `${evaluationId}-${docIndex}`
    const newExpanded = new Set(expandedDocuments)
    if (newExpanded.has(key)) {
      newExpanded.delete(key)
    } else {
      newExpanded.add(key)
    }
    setExpandedDocuments(newExpanded)
  }

  const getGraphTypeBadgeColor = (graphType: string) => {
    switch (graphType) {
      case 'adaptive_rag':
        return { bg: '#e3f2fd', color: '#1976d2' }
      case 'simple_rag':
        return { bg: '#fff3e0', color: '#f57c00' }
      case 'pure_llm':
        return { bg: '#f3e5f5', color: '#7b1fa2' }
      default:
        return { bg: '#f5f5f5', color: '#666' }
    }
  }

  const getGraphTypeName = (graphType: string) => {
    switch (graphType) {
      case 'adaptive_rag':
        return 'Adaptive RAG'
      case 'simple_rag':
        return 'Simple RAG'
      case 'pure_llm':
        return 'Pure LLM'
      default:
        return graphType
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('de-DE')
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Graph Type Comparison</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Vergleiche die Performance verschiedener Graph-Typen auf denselben Fragen
      </p>

      {/* Question List Section */}
      <div style={{ marginBottom: '32px' }}>
        <h2>Evaluierte Fragen</h2>

        {/* Filter & Sort Controls */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '15px',
          padding: '15px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          marginBottom: '16px'
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
              Titel suchen:
            </label>
            <input
              type="text"
              value={titleSearch}
              onChange={(e) => setTitleSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleFilterSearch()}
              placeholder="z.B. SQL query, JOIN"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
              Tags filtern:
            </label>
            <input
              type="text"
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleFilterSearch()}
              placeholder="z.B. sql, postgresql"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
              Min Score:
            </label>
            <input
              type="number"
              min="0"
              value={minScoreFilter ?? ''}
              onChange={(e) => setMinScoreFilter(e.target.value ? parseInt(e.target.value) : null)}
              onKeyDown={(e) => e.key === 'Enter' && handleFilterSearch()}
              placeholder="0"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
              Sortieren nach:
            </label>
            <select
              value={sortBy}
              onChange={(e) => { setSortBy(e.target.value); setCurrentPage(1) }}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="creation_date">Erstellungsdatum</option>
              <option value="score">Score</option>
              <option value="evaluation_count">Anzahl Evaluations</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
              Reihenfolge:
            </label>
            <select
              value={sortOrder}
              onChange={(e) => { setSortOrder(e.target.value); setCurrentPage(1) }}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="desc">Absteigend</option>
              <option value="asc">Aufsteigend</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              onClick={handleFilterSearch}
              style={{
                padding: '8px 16px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Suchen
            </button>
          </div>
        </div>

        {/* Checkbox Filter */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={filterMultipleGraphTypes}
              onChange={(e) => { setFilterMultipleGraphTypes(e.target.checked); setCurrentPage(1) }}
              style={{ marginRight: '8px' }}
            />
            <span>Nur Fragen mit mehreren Graph-Typen</span>
          </label>
        </div>

        {loading && !comparisonData && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            Lade Fragen...
          </div>
        )}

        {!loading && paginatedData && paginatedData.items.length === 0 && (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
            color: '#666'
          }}>
            Keine evaluierten Fragen gefunden.
            {filterMultipleGraphTypes && (
              <span> Versuche den Filter zu deaktivieren.</span>
            )}
          </div>
        )}

        {paginatedData && paginatedData.items.length > 0 && (
          <>
          <div style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            overflow: 'hidden'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5' }}>
                  <th
                    onClick={() => handleColumnSort('question_id')}
                    style={{
                      padding: '12px',
                      textAlign: 'left',
                      borderBottom: '2px solid #ddd',
                      cursor: 'pointer',
                      backgroundColor: sortBy === 'question_id' ? '#e3f2fd' : undefined,
                      userSelect: 'none'
                    }}
                  >
                    ID {sortBy === 'question_id' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Titel</th>
                  <th
                    onClick={() => handleColumnSort('score')}
                    style={{
                      padding: '12px',
                      textAlign: 'center',
                      borderBottom: '2px solid #ddd',
                      cursor: 'pointer',
                      backgroundColor: sortBy === 'score' ? '#e3f2fd' : undefined,
                      userSelect: 'none'
                    }}
                  >
                    Score {sortBy === 'score' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Graph-Typen</th>
                  <th
                    onClick={() => handleColumnSort('evaluation_count')}
                    style={{
                      padding: '12px',
                      textAlign: 'center',
                      borderBottom: '2px solid #ddd',
                      cursor: 'pointer',
                      backgroundColor: sortBy === 'evaluation_count' ? '#e3f2fd' : undefined,
                      userSelect: 'none'
                    }}
                  >
                    Evaluations {sortBy === 'evaluation_count' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {paginatedData.items.map((question) => (
                  <tr
                    key={question.question_id}
                    style={{
                      backgroundColor: selectedQuestionId === question.question_id ? '#f0f7ff' : 'white',
                      borderBottom: '1px solid #eee'
                    }}
                  >
                    <td style={{ padding: '12px' }}>{question.question_id}</td>
                    <td style={{ padding: '12px', maxWidth: '400px' }}>
                      <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                        {question.question_title}
                      </div>
                      {question.tags.length > 0 && (
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {question.tags.slice(0, 3).map((tag, idx) => (
                            <span
                              key={idx}
                              style={{
                                display: 'inline-block',
                                marginRight: '4px',
                                padding: '2px 6px',
                                backgroundColor: '#e0e0e0',
                                borderRadius: '3px'
                              }}
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', fontWeight: 500 }}>
                      {question.score}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {question.available_graph_types.map((graphType, idx) => {
                          const colors = getGraphTypeBadgeColor(graphType)
                          return (
                            <span
                              key={idx}
                              style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                backgroundColor: colors.bg,
                                color: colors.color,
                                fontSize: '12px',
                                fontWeight: 500
                              }}
                            >
                              {getGraphTypeName(graphType)}
                            </span>
                          )
                        })}
                      </div>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>{question.total_evaluations}</td>
                    <td style={{ padding: '12px' }}>
                      <button
                        onClick={() => loadComparisonData(question.question_id)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#1976d2',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '14px'
                        }}
                      >
                        Vergleichen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '16px',
            padding: '12px 16px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px'
          }}>
            <div style={{ fontSize: '14px', color: '#666' }}>
              Zeige {paginatedData.items.length} von {paginatedData.total} Fragen
              (Seite {paginatedData.page} von {paginatedData.total_pages})
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={!paginatedData.has_prev || loading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: paginatedData.has_prev ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: paginatedData.has_prev ? 'pointer' : 'not-allowed'
                }}
              >
                Zurück
              </button>
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(parseInt(e.target.value)); setCurrentPage(1) }}
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value="10">10 pro Seite</option>
                <option value="20">20 pro Seite</option>
                <option value="50">50 pro Seite</option>
                <option value="100">100 pro Seite</option>
              </select>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={!paginatedData.has_next || loading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: paginatedData.has_next ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: paginatedData.has_next ? 'pointer' : 'not-allowed'
                }}
              >
                Weiter
              </button>
            </div>
          </div>
          </>
        )}
      </div>

      {/* Comparison Details Section */}
      {comparisonData && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>Vergleich: {comparisonData.question_title}</h2>
            <button
              onClick={openRerunModal}
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

          {/* Question Body */}
          <div style={{
            padding: '16px',
            backgroundColor: '#f9f9f9',
            borderRadius: '8px',
            marginBottom: '24px',
            border: '1px solid #e0e0e0'
          }}>
            <h3 style={{ marginTop: 0 }}>Frage:</h3>
            <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {comparisonData.question_body}
            </p>
          </div>

          {/* Accepted StackOverflow Answer */}
          {comparisonData.accepted_answer && (
            <div style={{
              padding: '16px',
              backgroundColor: '#e8f5e9',
              borderRadius: '8px',
              marginBottom: '24px',
              border: '1px solid #c8e6c9'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: '12px'
              }}>
                <h3 style={{ margin: 0, color: '#2e7d32' }}>
                  Akzeptierte StackOverflow-Antwort
                </h3>
                <span style={{
                  marginLeft: '12px',
                  padding: '4px 8px',
                  backgroundColor: '#4caf50',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 500
                }}>
                  Referenz
                </span>
                <span style={{
                  marginLeft: '8px',
                  fontSize: '14px',
                  color: '#666'
                }}>
                  Score: {comparisonData.accepted_answer.score}
                </span>
              </div>
              <div style={{
                padding: '12px',
                backgroundColor: 'white',
                borderRadius: '4px',
                whiteSpace: 'pre-wrap',
                fontSize: '14px',
                lineHeight: '1.6',
                maxHeight: '400px',
                overflowY: 'auto'
              }}>
                {comparisonData.accepted_answer.body}
              </div>
              {comparisonData.accepted_answer.owner_display_name && (
                <div style={{
                  marginTop: '8px',
                  fontSize: '12px',
                  color: '#666'
                }}>
                  Beantwortet von: {comparisonData.accepted_answer.owner_display_name}
                </div>
              )}
            </div>
          )}

          {/* Metrics Summary Table */}
          {metricsData.length > 0 && (
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
                        BERT F1
                      </th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                        BERT Precision
                      </th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #ddd' }}>
                        BERT Recall
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
                              <span style={{
                                color: getBertScoreColor(metrics.avg_bert_f1),
                                fontWeight: 'bold'
                              }}>
                                {metrics.avg_bert_f1.toFixed(4)}
                              </span>
                            ) : (
                              <span style={{ color: '#999' }}>-</span>
                            )}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center' }}>
                            {metrics.avg_bert_precision !== null && metrics.avg_bert_precision !== undefined ? (
                              <span style={{
                                color: getBertScoreColor(metrics.avg_bert_precision),
                                fontWeight: 'bold'
                              }}>
                                {metrics.avg_bert_precision.toFixed(4)}
                              </span>
                            ) : (
                              <span style={{ color: '#999' }}>-</span>
                            )}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center' }}>
                            {metrics.avg_bert_recall !== null && metrics.avg_bert_recall !== undefined ? (
                              <span style={{
                                color: getBertScoreColor(metrics.avg_bert_recall),
                                fontWeight: 'bold'
                              }}>
                                {metrics.avg_bert_recall.toFixed(4)}
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
          )}

          {/* Detailed Evaluations by Graph Type */}
          <h3>Detaillierte Evaluations</h3>
          {Object.entries(comparisonData.evaluations_by_graph_type).map(([graphType, evaluations]) => {
            const colors = getGraphTypeBadgeColor(graphType)
            return (
              <div key={graphType} style={{ marginBottom: '24px' }}>
                <h4 style={{
                  padding: '12px 16px',
                  backgroundColor: colors.bg,
                  color: colors.color,
                  borderRadius: '8px 8px 0 0',
                  margin: 0
                }}>
                  {getGraphTypeName(graphType)} ({evaluations.length} Evaluation{evaluations.length !== 1 ? 's' : ''})
                </h4>

                {evaluations.map((evaluation: EvaluationWithGraphType) => {
                  const isExpanded = expandedEvaluations.has(evaluation.id)
                  return (
                    <div
                      key={evaluation.id}
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
                        onClick={() => toggleEvaluationExpanded(evaluation.id)}
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
                                <span style={{
                                  fontWeight: 'bold',
                                  color: getBertScoreColor(evaluation.bert_f1)
                                }}>
                                  {evaluation.bert_f1.toFixed(4)}
                                </span>
                              </div>
                            )}
                            {evaluation.bert_precision !== null && evaluation.bert_precision !== undefined && (
                              <div>
                                <span style={{ fontSize: '12px', color: '#666' }}>Precision: </span>
                                <span style={{
                                  fontWeight: 'bold',
                                  color: getBertScoreColor(evaluation.bert_precision)
                                }}>
                                  {evaluation.bert_precision.toFixed(4)}
                                </span>
                              </div>
                            )}
                            {evaluation.bert_recall !== null && evaluation.bert_recall !== undefined && (
                              <div>
                                <span style={{ fontSize: '12px', color: '#666' }}>Recall: </span>
                                <span style={{
                                  fontWeight: 'bold',
                                  color: getBertScoreColor(evaluation.bert_recall)
                                }}>
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
                                    onToggle={() => toggleDocumentExpanded(evaluation.id, idx)}
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
                              onRatingSubmit={(rating) => {
                                // Update local state to reflect new rating
                                console.log(`Rating ${rating} submitted for evaluation ${evaluation.id}`)
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      )}

      {error && (
        <div style={{
          padding: '16px',
          backgroundColor: '#ffebee',
          color: '#c62828',
          borderRadius: '8px',
          marginTop: '16px'
        }}>
          {error}
        </div>
      )}

      {/* Rerun Modal */}
      {showRerunModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            minWidth: '500px',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflowY: 'auto',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>Frage erneut ausführen</h2>
              <button
                onClick={closeRerunModal}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#666'
                }}
              >
                ×
              </button>
            </div>

            {comparisonData && (
              <div style={{
                padding: '12px',
                backgroundColor: '#f5f5f5',
                borderRadius: '6px',
                marginBottom: '20px',
                fontSize: '14px'
              }}>
                <strong>Frage:</strong> {comparisonData.question_title}
              </div>
            )}

            {/* Graph Types Selection */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '12px' }}>Graph-Typen auswählen:</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {['adaptive_rag', 'simple_rag', 'pure_llm'].map((graphType) => {
                  const colors = getGraphTypeBadgeColor(graphType)
                  return (
                    <label
                      key={graphType}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '10px 12px',
                        backgroundColor: rerunGraphTypes.includes(graphType) ? colors.bg : '#f9f9f9',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        border: rerunGraphTypes.includes(graphType) ? `2px solid ${colors.color}` : '2px solid transparent'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={rerunGraphTypes.includes(graphType)}
                        onChange={() => toggleGraphType(graphType)}
                        style={{ marginRight: '10px' }}
                      />
                      <span style={{
                        padding: '4px 10px',
                        backgroundColor: colors.bg,
                        color: colors.color,
                        borderRadius: '4px',
                        fontWeight: 500
                      }}>
                        {getGraphTypeName(graphType)}
                      </span>
                    </label>
                  )
                })}
              </div>
              {rerunGraphTypes.length === 0 && (
                <div style={{ color: '#d32f2f', fontSize: '12px', marginTop: '8px' }}>
                  Mindestens ein Graph-Typ muss ausgewählt werden
                </div>
              )}
            </div>

            {/* Collections Selection */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '12px' }}>
                Collections (optional):
                <span style={{ fontWeight: 'normal', fontSize: '12px', color: '#666', marginLeft: '8px' }}>
                  Leer = StackOverflow Retriever
                </span>
              </h4>
              {availableCollections.length === 0 ? (
                <div style={{ color: '#666', fontStyle: 'italic', fontSize: '14px' }}>
                  Keine Collections verfügbar
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '150px', overflowY: 'auto' }}>
                  {availableCollections.map((collection) => (
                    <label
                      key={collection.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 12px',
                        backgroundColor: rerunCollections.includes(collection.id) ? '#e3f2fd' : '#f9f9f9',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        border: rerunCollections.includes(collection.id) ? '1px solid #1976d2' : '1px solid transparent'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={rerunCollections.includes(collection.id)}
                        onChange={() => toggleCollection(collection.id)}
                        style={{ marginRight: '10px' }}
                      />
                      <span style={{ flex: 1 }}>
                        {collection.name}
                        <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>
                          ({collection.question_count} Fragen)
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Job Status / Progress */}
            {rerunJobId && rerunJobStatus && (
              <div style={{
                padding: '16px',
                backgroundColor: rerunJobStatus.status === 'completed' ? '#e8f5e9' :
                                rerunJobStatus.status === 'failed' ? '#ffebee' : '#e3f2fd',
                borderRadius: '8px',
                marginBottom: '20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong>Status:</strong>
                  <span style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    backgroundColor: rerunJobStatus.status === 'completed' ? '#4caf50' :
                                    rerunJobStatus.status === 'failed' ? '#f44336' :
                                    rerunJobStatus.status === 'running' ? '#2196f3' : '#9e9e9e',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 500
                  }}>
                    {rerunJobStatus.status === 'running' ? 'Läuft...' :
                     rerunJobStatus.status === 'completed' ? 'Abgeschlossen' :
                     rerunJobStatus.status === 'failed' ? 'Fehlgeschlagen' : rerunJobStatus.status}
                  </span>
                </div>
                {rerunJobStatus.progress && (
                  <div style={{ fontSize: '14px' }}>
                    <div style={{ marginBottom: '4px' }}>
                      Fortschritt: {rerunJobStatus.progress.processed} / {rerunJobStatus.progress.total_questions}
                    </div>
                    {rerunJobStatus.progress.successful > 0 && (
                      <div style={{ color: '#4caf50' }}>
                        Erfolgreich: {rerunJobStatus.progress.successful}
                      </div>
                    )}
                    {rerunJobStatus.progress.failed > 0 && (
                      <div style={{ color: '#f44336' }}>
                        Fehlgeschlagen: {rerunJobStatus.progress.failed}
                      </div>
                    )}
                  </div>
                )}
                {rerunJobStatus.error && (
                  <div style={{ color: '#c62828', marginTop: '8px' }}>
                    Fehler: {rerunJobStatus.error}
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={closeRerunModal}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#f5f5f5',
                  color: '#333',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 500
                }}
              >
                {rerunJobStatus?.status === 'completed' ? 'Schließen' : 'Abbrechen'}
              </button>
              {(!rerunJobId || rerunJobStatus?.status === 'completed') && (
                <button
                  onClick={startRerun}
                  disabled={rerunGraphTypes.length === 0 || rerunLoading}
                  style={{
                    padding: '10px 24px',
                    backgroundColor: rerunGraphTypes.length === 0 || rerunLoading ? '#ccc' : '#ff9800',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: rerunGraphTypes.length === 0 || rerunLoading ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  {rerunLoading ? 'Wird ausgeführt...' : rerunJobStatus?.status === 'completed' ? 'Erneut starten' : 'Ausführen'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
