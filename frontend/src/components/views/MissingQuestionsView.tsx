import React, { useState, useEffect, useMemo } from 'react'
import { apiService } from '../../services/api'
import type {
  MissingQuestionsResponse,
  GraphType,
  Collection
} from '../../types'
import { SortableHeader, HeaderCell, TablePagination, StackOverflowLink, TagList } from '../table'
import { TABLE_PAGE_SIZES, TABLE_COLORS } from '../../theme/tableConstants'

interface MissingQuestionsViewProps {
  onStartBatch?: (jobId: string) => void
}

export const MissingQuestionsView: React.FC<MissingQuestionsViewProps> = ({ onStartBatch }) => {
  // State
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<MissingQuestionsResponse | null>(null)
  const [collections, setCollections] = useState<Collection[]>([])

  // Selection state
  const [selectedGraphTypes, setSelectedGraphTypes] = useState<Set<string>>(
    new Set(['adaptive_rag', 'simple_rag', 'pure_llm'])
  )
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<Set<number>>(new Set())
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<number[]>([])
  const [excludeSelectedCollections, setExcludeSelectedCollections] = useState(false)

  // Pagination state
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [sortBy, setSortBy] = useState('score')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Batch start state
  const [startingBatch, setStartingBatch] = useState(false)
  const [sessionId, setSessionId] = useState(() => {
    const date = new Date().toISOString().split('T')[0]
    return `backfill_${date}`
  })

  // Load data
  useEffect(() => {
    loadData()
    loadCollections()
  }, [])

  // Reload when filter or pagination changes
  useEffect(() => {
    if (data) {  // Only reload if data was already loaded
      loadData()
    }
  }, [excludeSelectedCollections, selectedCollectionIds.length, page, pageSize, sortBy, sortOrder])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const graphTypesArray = Array.from(selectedGraphTypes)
      const response = await apiService.getMissingQuestions({
        graphTypes: graphTypesArray,
        excludeCollectionIds: excludeSelectedCollections ? selectedCollectionIds : undefined,
        page,
        pageSize,
        sortBy,
        sortOrder
      })
      setData(response)
      // Auto-select all missing questions from current page
      const pageQuestionIds = new Set<number>(response.questions.map(q => q.stack_overflow_id))
      setSelectedQuestionIds(prev => {
        // Keep previous selections that are still in the full missing set
        const allMissingIds = new Set<number>()
        Object.values(response.missing_by_graph_type).forEach(info => {
          info.question_ids.forEach(id => allMissingIds.add(id))
        })
        const newSelection = new Set<number>()
        prev.forEach(id => {
          if (allMissingIds.has(id)) newSelection.add(id)
        })
        // Add all from current page
        pageQuestionIds.forEach(id => newSelection.add(id))
        return newSelection
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load missing questions')
    } finally {
      setLoading(false)
    }
  }

  const loadCollections = async () => {
    try {
      const cols = await apiService.getCollectionsList()
      setCollections(cols.filter(c => c.chroma_exists && !c.needs_rebuild))
    } catch (err) {
      console.error('Failed to load collections:', err)
    }
  }

  // Get all missing question IDs (union across selected graph types)
  const allMissingIds = useMemo(() => {
    if (!data) return new Set<number>()

    const unionIds = new Set<number>()
    selectedGraphTypes.forEach(gt => {
      const info = data.missing_by_graph_type[gt]
      if (info) {
        info.question_ids.forEach(id => unionIds.add(id))
      }
    })
    return unionIds
  }, [data, selectedGraphTypes])

  // Current page questions (already filtered by backend)
  const currentPageQuestions = useMemo(() => {
    if (!data) return []
    return data.questions
  }, [data])

  // Toggle graph type selection
  const toggleGraphType = (gt: string) => {
    setSelectedGraphTypes(prev => {
      const next = new Set(prev)
      if (next.has(gt)) {
        next.delete(gt)
      } else {
        next.add(gt)
      }
      return next
    })
  }

  // Toggle question selection
  const toggleQuestion = (questionId: number) => {
    setSelectedQuestionIds(prev => {
      const next = new Set(prev)
      if (next.has(questionId)) {
        next.delete(questionId)
      } else {
        next.add(questionId)
      }
      return next
    })
  }

  // Select/deselect all
  const selectAllQuestions = () => {
    // Select all missing questions across all pages
    setSelectedQuestionIds(new Set(allMissingIds))
  }

  const selectCurrentPage = () => {
    // Add current page questions to selection
    setSelectedQuestionIds(prev => {
      const next = new Set(prev)
      currentPageQuestions.forEach(q => next.add(q.stack_overflow_id))
      return next
    })
  }

  const deselectCurrentPage = () => {
    // Remove current page questions from selection
    setSelectedQuestionIds(prev => {
      const next = new Set(prev)
      currentPageQuestions.forEach(q => next.delete(q.stack_overflow_id))
      return next
    })
  }

  const deselectAllQuestions = () => {
    setSelectedQuestionIds(new Set())
  }

  // Start batch evaluation
  const startBatchEvaluation = async () => {
    if (selectedQuestionIds.size === 0) {
      setError('Please select at least one question')
      return
    }

    if (selectedGraphTypes.size === 0) {
      setError('Please select at least one graph type')
      return
    }

    // For RAG types, require at least one collection
    const ragTypes = ['adaptive_rag', 'simple_rag']
    const hasRagType = ragTypes.some(gt => selectedGraphTypes.has(gt))
    if (hasRagType && selectedCollectionIds.length === 0) {
      setError('Please select at least one collection for RAG graph types')
      return
    }

    setStartingBatch(true)
    setError(null)

    try {
      const response = await apiService.startBatchQuery({
        question_ids: Array.from(selectedQuestionIds),
        session_id: sessionId,
        collection_ids: selectedCollectionIds.length > 0 ? selectedCollectionIds : undefined,
        graph_types: Array.from(selectedGraphTypes) as GraphType[],
        include_graph_trace: true
      })

      // Dispatch event to switch to batch progress view
      window.dispatchEvent(new CustomEvent('batch-started', {
        detail: { jobId: response.job_id }
      }))

      if (onStartBatch) {
        onStartBatch(response.job_id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start batch evaluation')
    } finally {
      setStartingBatch(false)
    }
  }

  // Render loading state
  if (loading) {
    return (
      <div className="query-section" style={{ padding: '40px', textAlign: 'center' }}>
        <div className="spinner" style={{ width: '40px', height: '40px', margin: '0 auto 20px' }} />
        <p>Fehlende Fragen werden geladen...</p>
      </div>
    )
  }

  // Render error state
  if (error && !data) {
    return (
      <div className="query-section" style={{ padding: '40px' }}>
        <div style={{
          background: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '8px',
          padding: '20px',
          color: '#c62828'
        }}>
          <strong>Error:</strong> {error}
          <button
            onClick={loadData}
            className="button"
            style={{ marginLeft: '20px', background: '#f44336' }}
          >
            Erneut versuchen
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const evaluatedCount = data.total_questions - data.total_missing

  return (
    <div className="query-section" style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{
        background: 'white',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <h2 style={{ margin: '0 0 20px 0' }}>Überprüfung fehlender Fragen</h2>

        {/* Current Configuration */}
        <div style={{
          background: '#f5f5f5',
          borderRadius: '8px',
          padding: '15px',
          marginBottom: '20px'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Aktuelle Konfiguration</h4>
          <div style={{ display: 'flex', gap: '30px', flexWrap: 'wrap' }}>
            <div>
              <span style={{ color: '#888', fontSize: '12px' }}>LLM-Modell:</span>
              <br />
              <strong>{data.current_config.llm_model}</strong>
            </div>
            <div>
              <span style={{ color: '#888', fontSize: '12px' }}>Evaluierungs-Modell:</span>
              <br />
              <strong>{data.current_config.llm_correctness_model}</strong>
            </div>
            <div>
              <span style={{ color: '#888', fontSize: '12px' }}>Embedding-Modell:</span>
              <br />
              <strong>{data.current_config.embedding_model}</strong>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div style={{
          display: 'flex',
          gap: '20px',
          flexWrap: 'wrap',
          marginBottom: '20px'
        }}>
          <div style={{
            background: '#e3f2fd',
            borderRadius: '8px',
            padding: '15px 25px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1976d2' }}>
              {data.total_questions}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>Gesamt-Fragen</div>
          </div>
          <div style={{
            background: '#e8f5e9',
            borderRadius: '8px',
            padding: '15px 25px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#388e3c' }}>
              {evaluatedCount}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>Evaluiert</div>
          </div>
          <div style={{
            background: '#fff3e0',
            borderRadius: '8px',
            padding: '15px 25px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f57c00' }}>
              {data.total_missing}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>Fehlend (Union)</div>
          </div>
          <div style={{
            background: '#e8eaf6',
            borderRadius: '8px',
            padding: '15px 25px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3f51b5' }}>
              {selectedQuestionIds.size}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>Ausgewählt</div>
          </div>
        </div>

        {/* Graph Type Selection */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Graph Types</h4>
          <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
            {Object.entries(data.missing_by_graph_type).map(([gt, info]) => (
              <label
                key={gt}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 15px',
                  background: selectedGraphTypes.has(gt) ? '#e3f2fd' : '#f5f5f5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: selectedGraphTypes.has(gt) ? '2px solid #1976d2' : '2px solid transparent'
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedGraphTypes.has(gt)}
                  onChange={() => toggleGraphType(gt)}
                />
                <span style={{ fontWeight: 500 }}>
                  {gt.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <span style={{
                  background: info.count > 0 ? '#ff9800' : '#4caf50',
                  color: 'white',
                  borderRadius: '12px',
                  padding: '2px 10px',
                  fontSize: '12px'
                }}>
                  {info.count}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Collection Selection (for RAG types) */}
        {(selectedGraphTypes.has('adaptive_rag') || selectedGraphTypes.has('simple_rag')) && (
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>
              Collections für RAG
              <span style={{ fontWeight: 'normal', fontSize: '12px', marginLeft: '10px', color: '#888' }}>
                (Erforderlich für adaptive_rag und simple_rag)
              </span>
            </h4>
            {collections.length === 0 ? (
              <div style={{ color: '#f57c00', padding: '10px', background: '#fff3e0', borderRadius: '4px' }}>
                Keine bereiten Collections verfügbar. Bitte erstellen Sie zuerst Collections neu.
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {collections.map(col => (
                    <label
                      key={col.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 12px',
                        background: selectedCollectionIds.includes(col.id) ? '#e8f5e9' : '#f5f5f5',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        border: selectedCollectionIds.includes(col.id) ? '2px solid #388e3c' : '2px solid transparent'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedCollectionIds.includes(col.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedCollectionIds([...selectedCollectionIds, col.id])
                          } else {
                            setSelectedCollectionIds(selectedCollectionIds.filter(id => id !== col.id))
                          }
                        }}
                      />
                      <span>{col.name}</span>
                      <span style={{ fontSize: '11px', color: '#888' }}>
                        ({col.question_count} Q)
                      </span>
                    </label>
                  ))}
                </div>
                {selectedCollectionIds.length > 0 && (
                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginTop: '10px',
                    padding: '8px 12px',
                    background: excludeSelectedCollections ? '#fff3e0' : '#f5f5f5',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    border: excludeSelectedCollections ? '2px solid #f57c00' : '2px solid transparent'
                  }}>
                    <input
                      type="checkbox"
                      checked={excludeSelectedCollections}
                      onChange={(e) => setExcludeSelectedCollections(e.target.checked)}
                    />
                    <span>Fragen in gewaehlten Collections ausschliessen</span>
                  </label>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div style={{
          background: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '8px',
          padding: '15px',
          marginBottom: '20px',
          color: '#c62828'
        }}>
          {error}
        </div>
      )}

      {/* Questions List */}
      <div style={{
        background: 'white',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        {/* Header with controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '15px',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <h3 style={{ margin: 0 }}>
            Fehlende Fragen ({data.total_missing})
          </h3>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={loadData}
              className="button"
              style={{ background: '#6c757d', padding: '8px 16px', fontSize: '13px' }}
            >
              Aktualisieren
            </button>
          </div>
        </div>

        {/* Selection controls */}
        <div style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '15px',
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={selectAllQuestions}
            className="button"
            style={{ background: '#1976d2', padding: '8px 16px', fontSize: '13px' }}
          >
            Alle auswählen ({data.total_missing})
          </button>
          <button
            onClick={selectCurrentPage}
            className="button"
            style={{ background: '#6c757d', padding: '8px 16px', fontSize: '13px' }}
          >
            Seite auswählen
          </button>
          <button
            onClick={deselectCurrentPage}
            className="button"
            style={{ background: '#6c757d', padding: '8px 16px', fontSize: '13px' }}
          >
            Seite abwählen
          </button>
          <button
            onClick={deselectAllQuestions}
            className="button"
            style={{ background: '#dc3545', padding: '8px 16px', fontSize: '13px' }}
          >
            Alle abwählen
          </button>
        </div>

        {/* Questions Table */}
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'white' }}>
              <tr style={{ borderBottom: `2px solid ${TABLE_COLORS.headerBorder}` }}>
                <th style={{ padding: '12px', width: '40px', borderBottom: `2px solid ${TABLE_COLORS.headerBorder}` }}></th>
                <SortableHeader
                  column="stack_overflow_id"
                  label="ID"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={(col) => {
                    if (sortBy === col) {
                      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                    } else {
                      setSortBy(col)
                      setSortOrder('desc')
                    }
                    setPage(1)
                  }}
                  width="100px"
                />
                <SortableHeader
                  column="title"
                  label="Titel"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={(col) => {
                    if (sortBy === col) {
                      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                    } else {
                      setSortBy(col)
                      setSortOrder('asc')
                    }
                    setPage(1)
                  }}
                />
                <HeaderCell width="150px">Tags</HeaderCell>
                <SortableHeader
                  column="score"
                  label="Score"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={(col) => {
                    if (sortBy === col) {
                      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                    } else {
                      setSortBy(col)
                      setSortOrder('desc')
                    }
                    setPage(1)
                  }}
                  align="right"
                  width="80px"
                />
                <HeaderCell width="180px">Collections</HeaderCell>
              </tr>
            </thead>
            <tbody>
              {currentPageQuestions.map(q => (
                <tr
                  key={q.stack_overflow_id}
                  style={{
                    borderBottom: `1px solid ${TABLE_COLORS.rowBorder}`,
                    background: selectedQuestionIds.has(q.stack_overflow_id) ? TABLE_COLORS.selectedRow : 'white'
                  }}
                >
                  <td style={{ padding: '10px' }}>
                    <input
                      type="checkbox"
                      checked={selectedQuestionIds.has(q.stack_overflow_id)}
                      onChange={() => toggleQuestion(q.stack_overflow_id)}
                    />
                  </td>
                  <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: '12px' }}>
                    <StackOverflowLink stackOverflowId={q.stack_overflow_id} />
                  </td>
                  <td style={{ padding: '10px', fontSize: '14px' }}>
                    {q.title.length > 80 ? q.title.substring(0, 80) + '...' : q.title}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <TagList tags={q.tags} maxTags={3} />
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right', fontWeight: 500 }}>
                    {q.score}
                  </td>
                  <td style={{ padding: '10px' }}>
                    {q.collections.length === 0 ? (
                      <span style={{ color: '#999', fontStyle: 'italic', fontSize: '12px' }}>Keine</span>
                    ) : (
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {q.collections.map(c => (
                          <span
                            key={c.collection_id}
                            style={{
                              padding: '2px 6px',
                              borderRadius: '10px',
                              fontSize: '11px',
                              background: TABLE_COLORS.tagBg,
                              color: TABLE_COLORS.tagText
                            }}
                          >
                            {c.collection_name}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        <TablePagination
          page={data.page}
          pageSize={pageSize}
          totalItems={data.total_missing}
          totalPages={data.total_pages}
          hasNext={data.has_next}
          hasPrev={data.has_prev}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
          pageSizeOptions={TABLE_PAGE_SIZES}
        />
      </div>

      {/* Action Bar */}
      <div style={{
        background: 'white',
        borderRadius: '8px',
        padding: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ color: '#666' }}>Session-ID:</span>
          <input
            type="text"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              width: '300px'
            }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ color: '#666' }}>
            Ausgewählt: <strong>{selectedQuestionIds.size}</strong> Fragen x{' '}
            <strong>{selectedGraphTypes.size}</strong> Graph Types ={' '}
            <strong>{selectedQuestionIds.size * selectedGraphTypes.size}</strong> Evaluierungen
          </span>
          <button
            onClick={startBatchEvaluation}
            disabled={startingBatch || selectedQuestionIds.size === 0 || selectedGraphTypes.size === 0}
            className="button"
            style={{
              background: startingBatch ? '#ccc' : '#4caf50',
              padding: '12px 24px',
              fontSize: '16px'
            }}
          >
            {startingBatch ? (
              <>
                <span className="spinner" style={{ width: '14px', height: '14px', marginRight: '8px' }} />
                Starting...
              </>
            ) : (
              'Start Batch Evaluation'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
