import React, { useState, useEffect } from 'react'
import { apiService } from '../../services/api'
import type { QuestionWithCollections, BatchQueryRequest, Collection } from '../../types'
import { GraphType } from '../../types'

export const BatchQuerySelection: React.FC = () => {
  const [questions, setQuestions] = useState<QuestionWithCollections[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [onlyWithoutCollections, setOnlyWithoutCollections] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tagFilter, setTagFilter] = useState('')
  const [minScoreFilter, setMinScoreFilter] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState<'creation_date' | 'score' | 'view_count'>('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Running job detection
  const [hasRunningJob, setHasRunningJob] = useState(false)
  const [checkingForJobs, setCheckingForJobs] = useState(true)

  // Collection selection
  const [availableCollections, setAvailableCollections] = useState<Collection[]>([])
  const [selectedCollections, setSelectedCollections] = useState<number[]>([])

  // Graph type selection
  const [selectedGraphTypes, setSelectedGraphTypes] = useState<GraphType[]>([GraphType.ADAPTIVE_RAG])

  // Fetch questions
  useEffect(() => {
    loadQuestions()
  }, [page, onlyWithoutCollections, tagFilter, minScoreFilter, sortBy, sortOrder])

  // Load available collections on mount
  useEffect(() => {
    const loadCollections = async () => {
      try {
        const collections = await apiService.getCollectionsList()
        setAvailableCollections(collections)
      } catch (err) {
        console.error('Failed to load collections:', err)
      }
    }
    loadCollections()
  }, [])

  // Check for running jobs on mount
  useEffect(() => {
    const checkRunningJobs = async () => {
      setCheckingForJobs(true)
      try {
        const runningJobs = await apiService.listBatchQueryJobs('running', 1)
        setHasRunningJob(runningJobs.length > 0)
      } catch (err) {
        console.error('Failed to check for running jobs:', err)
        setHasRunningJob(false)
      } finally {
        setCheckingForJobs(false)
      }
    }
    checkRunningJobs()
  }, [])

  const loadQuestions = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiService.getQuestionsWithCollections({
        page,
        page_size: 20,
        only_without_collections: onlyWithoutCollections,
        tags: tagFilter || undefined,
        min_score: minScoreFilter,
        sort_by: sortBy,
        sort_order: sortOrder
      })
      setQuestions(result.items)
      setTotalPages(result.total_pages)
      setTotal(result.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleSelection = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      if (newSelected.size >= 50) {
        alert('Maximum 50 questions per batch allowed')
        return
      }
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedIds.size === questions.length) {
      setSelectedIds(new Set())
    } else {
      const remainingSlots = 50 - selectedIds.size
      const limitedSelection = questions
        .filter(q => !selectedIds.has(q.id))
        .slice(0, remainingSlots)
        .map(q => q.id)
      setSelectedIds(new Set([...selectedIds, ...limitedSelection]))
    }
  }

  const handleStartBatch = async () => {
    // Double-check no job is running
    try {
      const runningJobs = await apiService.listBatchQueryJobs('running', 1)
      if (runningJobs.length > 0) {
        setError('A batch job is already running.')
        const existingJobId = runningJobs[0].job_id
        localStorage.setItem('current_batch_job_id', existingJobId)
        window.dispatchEvent(new CustomEvent('batch-started', { detail: { jobId: existingJobId } }))
        return
      }
    } catch (err) {
      console.error('Failed to check for running jobs:', err)
    }

    const request: BatchQueryRequest = {
      question_ids: Array.from(selectedIds),
      session_id: `batch_${Date.now()}`,
      collection_ids: selectedCollections.length > 0 ? selectedCollections : undefined,
      graph_types: selectedGraphTypes,
      include_graph_trace: true
    }

    try {
      const response = await apiService.startBatchQuery(request)
      localStorage.setItem('current_batch_job_id', response.job_id)
      window.dispatchEvent(new CustomEvent('batch-started', { detail: { jobId: response.job_id } }))
    } catch (error) {
      console.error('Failed to start batch:', error)
      setError(error instanceof Error ? error.message : 'Failed to start batch processing')
    }
  }

  const handleToggleCollection = (collectionId: number) => {
    setSelectedCollections(prev =>
      prev.includes(collectionId)
        ? prev.filter(id => id !== collectionId)
        : [...prev, collectionId]
    )
  }

  const handleToggleGraphType = (graphType: GraphType) => {
    setSelectedGraphTypes(prev => {
      if (prev.includes(graphType)) {
        // Don't allow removing all graph types
        if (prev.length === 1) return prev
        return prev.filter(gt => gt !== graphType)
      } else {
        return [...prev, graphType]
      }
    })
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  return (
    <div className="batch-selection-view">
      <div className="query-section">
        <h2>📋 Batch Query Processing</h2>
        <p>Select up to 50 questions to process in batch</p>

        {/* Running Job Warning */}
        {hasRunningJob && !checkingForJobs && (
          <div style={{
            padding: '15px',
            background: '#fff3cd',
            border: '2px solid #ffc107',
            borderRadius: '8px',
            marginTop: '15px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <span style={{ fontSize: '20px' }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <strong>A batch job is currently running.</strong>
              <br />
              <span style={{ fontSize: '14px', color: '#666' }}>
                You can start a new batch after the current job completes.
              </span>
            </div>
          </div>
        )}

        {/* Collection Selection */}
        {availableCollections.length > 0 && (
          <div style={{
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '8px',
            marginTop: '20px',
            marginBottom: '20px',
            border: '2px solid #dee2e6'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '15px', fontSize: '16px', fontWeight: 'bold' }}>
              Select Collections for Retrieval
            </h3>
            <p style={{ marginBottom: '15px', fontSize: '14px', color: '#666' }}>
              Choose which collections to use for document retrieval (optional). If none selected, StackOverflow retriever will be used.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px' }}>
              {availableCollections.map(collection => (
                <label
                  key={collection.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 15px',
                    background: selectedCollections.includes(collection.id) ? '#e7f3ff' : 'white',
                    border: `2px solid ${selectedCollections.includes(collection.id) ? '#007bff' : '#dee2e6'}`,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    minWidth: '200px'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedCollections.includes(collection.id)}
                    onChange={() => handleToggleCollection(collection.id)}
                    style={{ cursor: 'pointer' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                      {collection.name}
                    </div>
                    {collection.description && (
                      <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                        {collection.description}
                      </div>
                    )}
                    <div style={{ fontSize: '12px', color: '#999', marginTop: '2px' }}>
                      {collection.question_count} questions
                    </div>
                  </div>
                </label>
              ))}
            </div>
            {selectedCollections.length > 0 && (
              <div style={{ marginTop: '15px', padding: '10px', background: '#e7f3ff', borderRadius: '4px' }}>
                <strong>{selectedCollections.length}</strong> collection(s) selected for retrieval
              </div>
            )}
          </div>
        )}

        {/* Graph Type Selection */}
        <div style={{
          marginTop: '25px',
          padding: '20px',
          background: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <h3 style={{
            margin: '0 0 10px 0',
            fontSize: '16px',
            fontWeight: 'bold',
            color: '#333'
          }}>
            🔄 Graph Types to Execute
          </h3>
          <p style={{ marginBottom: '15px', fontSize: '14px', color: '#666' }}>
            Jede Frage wird mit {selectedGraphTypes.length > 1 ? 'jedem' : 'dem'} ausgewählten Graph-Typ verarbeitet.
            Total: <strong>{selectedIds.size} Fragen × {selectedGraphTypes.length} Graph-Typen = {selectedIds.size * selectedGraphTypes.length} Ausführungen</strong>
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 15px',
              background: selectedGraphTypes.includes(GraphType.ADAPTIVE_RAG) ? '#e3f2fd' : 'white',
              border: `2px solid ${selectedGraphTypes.includes(GraphType.ADAPTIVE_RAG) ? '#1976d2' : '#dee2e6'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              minWidth: '250px'
            }}>
              <input
                type="checkbox"
                checked={selectedGraphTypes.includes(GraphType.ADAPTIVE_RAG)}
                onChange={() => handleToggleGraphType(GraphType.ADAPTIVE_RAG)}
                style={{ cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#1976d2' }}>
                  Adaptive RAG
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                  Vollständig mit Grading & Rewriting
                </div>
              </div>
            </label>

            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 15px',
              background: selectedGraphTypes.includes(GraphType.SIMPLE_RAG) ? '#fff3e0' : 'white',
              border: `2px solid ${selectedGraphTypes.includes(GraphType.SIMPLE_RAG) ? '#f57c00' : '#dee2e6'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              minWidth: '250px'
            }}>
              <input
                type="checkbox"
                checked={selectedGraphTypes.includes(GraphType.SIMPLE_RAG)}
                onChange={() => handleToggleGraphType(GraphType.SIMPLE_RAG)}
                style={{ cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#f57c00' }}>
                  Simple RAG
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                  Nur Retrieval + Generation
                </div>
              </div>
            </label>

            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 15px',
              background: selectedGraphTypes.includes(GraphType.PURE_LLM) ? '#f3e5f5' : 'white',
              border: `2px solid ${selectedGraphTypes.includes(GraphType.PURE_LLM) ? '#7b1fa2' : '#dee2e6'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              minWidth: '250px'
            }}>
              <input
                type="checkbox"
                checked={selectedGraphTypes.includes(GraphType.PURE_LLM)}
                onChange={() => handleToggleGraphType(GraphType.PURE_LLM)}
                style={{ cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#7b1fa2' }}>
                  Pure LLM
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                  Kein Retrieval - Baseline
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Filters */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '15px',
          marginTop: '20px',
          marginBottom: '20px'
        }}>
          <div className="form-group">
            <label>Filter by Tags:</label>
            <input
              type="text"
              value={tagFilter}
              onChange={(e) => {
                setTagFilter(e.target.value)
                setPage(1)
              }}
              placeholder="e.g., mysql, sql"
            />
          </div>

          <div className="form-group">
            <label>Min Score:</label>
            <input
              type="number"
              min="0"
              value={minScoreFilter || ''}
              onChange={(e) => {
                setMinScoreFilter(e.target.value ? parseInt(e.target.value) : undefined)
                setPage(1)
              }}
            />
          </div>

          <div className="form-group">
            <label>Sort By:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as 'creation_date' | 'score' | 'view_count')}>
              <option value="creation_date">Creation Date</option>
              <option value="score">Score</option>
              <option value="view_count">View Count</option>
            </select>
          </div>

          <div className="form-group">
            <label>Order:</label>
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>

        {/* Quick Filters */}
        <div style={{
          display: 'flex',
          gap: '15px',
          alignItems: 'center',
          padding: '15px',
          background: '#f8f9fa',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={onlyWithoutCollections}
              onChange={(e) => {
                setOnlyWithoutCollections(e.target.checked)
                setPage(1)
              }}
            />
            <span>Show only questions not in collections</span>
          </label>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontWeight: 'bold', color: selectedIds.size >= 50 ? '#dc3545' : '#007bff' }}>
              {selectedIds.size} / 50 selected
            </span>
            {selectedIds.size > 0 && (
              <button
                onClick={clearSelection}
                style={{ padding: '4px 12px', fontSize: '14px', background: '#6c757d' }}
              >
                Clear Selection
              </button>
            )}
            <button
              onClick={handleStartBatch}
              disabled={selectedIds.size === 0 || selectedIds.size > 50 || hasRunningJob || checkingForJobs}
              style={{
                padding: '8px 16px',
                fontWeight: 'bold',
                background: hasRunningJob
                  ? '#dc3545'
                  : (selectedIds.size > 0 && selectedIds.size <= 50 ? '#28a745' : '#6c757d'),
                cursor: hasRunningJob ? 'not-allowed' : 'pointer'
              }}
              title={hasRunningJob ? 'A batch job is already running' : undefined}
            >
              {checkingForJobs
                ? 'Checking...'
                : hasRunningJob
                  ? 'Job Running...'
                  : `Start Batch (${selectedIds.size})`
              }
            </button>
          </div>
        </div>

        {/* Questions Table */}
        {loading && questions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <span className="loading"></span>
            <p>Loading questions...</p>
          </div>
        ) : (
          <>
            <div style={{ overflowX: 'auto', marginBottom: '20px' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                background: 'white',
                borderRadius: '8px',
                overflow: 'hidden',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
              }}>
                <thead>
                  <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                    <th style={{ padding: '12px', textAlign: 'center', width: '50px' }}>
                      <input
                        type="checkbox"
                        onChange={handleSelectAll}
                        checked={questions.length > 0 && questions.every(q => selectedIds.has(q.id))}
                        disabled={loading}
                      />
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Title</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Score</th>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Collections</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map(q => (
                    <tr key={q.id} style={{
                      borderBottom: '1px solid #f0f0f0',
                      background: selectedIds.has(q.id) ? '#e7f3ff' : 'transparent'
                    }}>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(q.id)}
                          onChange={() => handleToggleSelection(q.id)}
                          disabled={loading}
                        />
                      </td>
                      <td style={{ padding: '12px' }}>
                        <a
                          href={`https://stackoverflow.com/questions/${q.stack_overflow_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#007bff', textDecoration: 'none' }}
                        >
                          {q.title}
                        </a>
                        <div style={{ marginTop: '5px', display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                          {q.tags.slice(0, 3).map((tag, idx) => (
                            <span key={idx} className="tag">{tag}</span>
                          ))}
                        </div>
                      </td>
                      <td style={{
                        padding: '12px',
                        textAlign: 'center',
                        fontWeight: 'bold',
                        color: q.score > 5 ? '#28a745' : '#666'
                      }}>
                        {q.score}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {q.collections.length === 0 ? (
                          <span style={{ color: '#999', fontSize: '14px', fontStyle: 'italic' }}>
                            None
                          </span>
                        ) : (
                          <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                            {q.collections.map(c => (
                              <span
                                key={c.collection_id}
                                style={{
                                  padding: '2px 8px',
                                  borderRadius: '12px',
                                  fontSize: '12px',
                                  background: '#e3f2fd',
                                  color: '#1976d2',
                                  whiteSpace: 'nowrap'
                                }}
                              >
                                {c.collection_name}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td style={{
                        padding: '12px',
                        textAlign: 'center',
                        fontSize: '12px',
                        color: '#666'
                      }}>
                        {new Date(q.creation_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '15px',
              background: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <div>
                Showing {questions.length} of {total} questions
                (Page {page} of {totalPages})
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1 || loading}
                  style={{ padding: '8px 16px' }}
                >
                  ← Previous
                </button>
                <span style={{
                  padding: '8px 16px',
                  background: 'white',
                  border: '1px solid #dee2e6',
                  borderRadius: '4px'
                }}>
                  Page {page}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page === totalPages || loading}
                  style={{ padding: '8px 16px' }}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}

        {error && (
          <div className="error" style={{ marginTop: '20px' }}>
            <strong>Error:</strong> {error}
            <button
              onClick={() => setError(null)}
              style={{
                marginLeft: '10px',
                background: 'none',
                border: 'none',
                fontSize: '18px',
                cursor: 'pointer'
              }}
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
