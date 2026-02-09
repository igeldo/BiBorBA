import React, { useState, useEffect } from 'react'
import { apiService } from '../../services/api'
import type {
  Collection,
  QuestionResponse,
  CollectionStatistics,
  AvailablePDF,
  DocumentResponse,
  RebuildJobProgress,
  CurrentModels
} from '../../types'
import { SortableHeader, HeaderCell, TablePagination, StackOverflowLink, TagList } from '../table'
import { TABLE_PAGE_SIZES, DEFAULT_PAGE_SIZE, TABLE_COLORS, getScoreDisplayColor } from '../../theme/tableConstants'

type TabType = 'questions' | 'add-questions' | 'documents' | 'add-documents'

export const CollectionManagementView: React.FC = () => {
  // State
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('questions')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Collection Questions State
  const [collectionQuestions, setCollectionQuestions] = useState<QuestionResponse[]>([])
  const [collectionPage, setCollectionPage] = useState(1)
  const [collectionTotal, setCollectionTotal] = useState(0)

  // Available Questions State (for adding)
  const [availableQuestions, setAvailableQuestions] = useState<QuestionResponse[]>([])
  const [availablePage, setAvailablePage] = useState(1)
  const [availableTotal, setAvailableTotal] = useState(0)
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<Set<number>>(new Set())

  // Filters
  const [tagFilter, setTagFilter] = useState('')
  const [minScore, setMinScore] = useState<number | undefined>(undefined)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  // Sorting
  const [sortBy, setSortBy] = useState<string>('score')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Rebuild Status
  const [rebuildStatus, setRebuildStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle')
  const [rebuildErrorMessage, setRebuildErrorMessage] = useState<string | null>(null)
  const [rebuildProgress, setRebuildProgress] = useState<RebuildJobProgress | null>(null)

  // Statistics
  const [statistics, setStatistics] = useState<CollectionStatistics | null>(null)

  // Current Models
  const [currentModels, setCurrentModels] = useState<CurrentModels | null>(null)

  // Create Collection Dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newCollectionName, setNewCollectionName] = useState('')
  const [newCollectionDescription, setNewCollectionDescription] = useState('')
  const [newCollectionType, setNewCollectionType] = useState<'stackoverflow' | 'pdf'>('stackoverflow')

  // PDF Documents State
  const [collectionDocuments, setCollectionDocuments] = useState<DocumentResponse[]>([])
  const [documentsPage, setDocumentsPage] = useState(1)
  const [documentsTotal, setDocumentsTotal] = useState(0)

  // Available PDFs State (for adding)
  const [availablePDFs, setAvailablePDFs] = useState<AvailablePDF[]>([])
  const [selectedPDFPaths, setSelectedPDFPaths] = useState<Set<string>>(new Set())

  // Load collections and current models on mount
  useEffect(() => {
    loadCollections()
    loadCurrentModels()
  }, [])

  const loadCurrentModels = async () => {
    try {
      const models = await apiService.getCurrentModels()
      setCurrentModels(models)
    } catch (err) {
      console.error('Failed to load current models:', err)
    }
  }

  // Auto-switch to correct tab when collection type changes
  useEffect(() => {
    if (selectedCollection) {
      if (selectedCollection.collection_type === 'pdf') {
        // For PDF collections, switch to 'documents' tab if currently on a question tab
        if (activeTab === 'questions' || activeTab === 'add-questions') {
          setActiveTab('documents')
        }
      } else if (selectedCollection.collection_type === 'stackoverflow') {
        // For StackOverflow collections, switch to 'questions' tab if currently on a document tab
        if (activeTab === 'documents' || activeTab === 'add-documents') {
          setActiveTab('questions')
        }
      }
    }
  }, [selectedCollection])

  // Load collection questions/documents when selection changes
  useEffect(() => {
    if (selectedCollection) {
      if (activeTab === 'questions') {
        loadCollectionQuestions()
        loadStatistics()
      } else if (activeTab === 'add-questions') {
        loadAvailableQuestions()
      } else if (activeTab === 'documents') {
        loadCollectionDocuments()
      } else if (activeTab === 'add-documents') {
        loadAvailablePDFs()
      }
    }
  }, [selectedCollection, activeTab, collectionPage, availablePage, documentsPage, pageSize, sortBy, sortOrder])

  const loadCollections = async () => {
    try {
      setLoading(true)
      const data = await apiService.getCollectionsList()
      setCollections(data)
      if (data.length > 0 && !selectedCollection) {
        setSelectedCollection(data[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collections')
    } finally {
      setLoading(false)
    }
  }

  const loadCollectionQuestions = async () => {
    if (!selectedCollection) return

    try {
      setLoading(true)
      const data = await apiService.getCollectionQuestions(selectedCollection.id, {
        page: collectionPage,
        page_size: pageSize,
        tags: tagFilter || undefined,
        min_score: minScore,
        sort_by: sortBy,
        sort_order: sortOrder
      })
      setCollectionQuestions(data.questions)
      setCollectionTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableQuestions = async () => {
    if (!selectedCollection) return

    try {
      setLoading(true)
      const data = await apiService.getTestQuestions(selectedCollection.id, {
        page: availablePage,
        page_size: pageSize,
        tags: tagFilter || undefined,
        min_score: minScore,
        sort_by: sortBy,
        sort_order: sortOrder
      })
      setAvailableQuestions(data.questions)
      setAvailableTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load available questions')
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    if (!selectedCollection) return

    try {
      const stats = await apiService.getCollectionStatistics(selectedCollection.id)
      setStatistics(stats)
    } catch (err) {
      console.error('Failed to load statistics:', err)
    }
  }

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) {
      setError('Collection name is required')
      return
    }

    try {
      setLoading(true)
      await apiService.createCollection({
        name: newCollectionName,
        description: newCollectionDescription || undefined,
        collection_type: newCollectionType
      })
      setNewCollectionName('')
      setNewCollectionDescription('')
      setNewCollectionType('stackoverflow')
      setShowCreateDialog(false)
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteCollection = async (collectionId: number) => {
    if (!confirm('Sind Sie sicher, dass Sie diese Collection löschen möchten?')) return

    try {
      setLoading(true)
      await apiService.deleteCollection(collectionId)
      if (selectedCollection?.id === collectionId) {
        setSelectedCollection(null)
      }
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete collection')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleQuestion = (questionId: number) => {
    const newSelection = new Set(selectedQuestionIds)
    if (newSelection.has(questionId)) {
      newSelection.delete(questionId)
    } else {
      newSelection.add(questionId)
    }
    setSelectedQuestionIds(newSelection)
  }

  const handleSelectAll = () => {
    const allIds = new Set(availableQuestions.map(q => q.id))
    setSelectedQuestionIds(allIds)
  }

  const handleDeselectAll = () => {
    setSelectedQuestionIds(new Set())
  }

  const handleAddQuestions = async () => {
    if (!selectedCollection || selectedQuestionIds.size === 0) return

    try {
      setLoading(true)
      await apiService.addQuestionsToCollection(selectedCollection.id, {
        question_ids: Array.from(selectedQuestionIds)
      })
      setSelectedQuestionIds(new Set())
      await loadAvailableQuestions()

      // Refresh collection
      const updated = await apiService.getCollection(selectedCollection.id)
      setSelectedCollection(updated)

      // Refresh collections list
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add questions')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveQuestion = async (questionId: number) => {
    if (!selectedCollection) return

    try {
      setLoading(true)
      await apiService.removeQuestionsFromCollection(selectedCollection.id, {
        question_ids: [questionId]
      })
      await loadCollectionQuestions()

      // Refresh collection
      const updated = await apiService.getCollection(selectedCollection.id)
      setSelectedCollection(updated)

      // Refresh collections list
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove question')
    } finally {
      setLoading(false)
    }
  }

  const handleRebuildCollection = async () => {
    if (!selectedCollection) return

    if (!confirm('Rebuild the ChromaDB collection? This may take a while for large documents.')) return

    try {
      setLoading(true)
      setRebuildStatus('running')
      setRebuildErrorMessage(null)
      setRebuildProgress(null)

      // Start the rebuild and get job_id for tracking
      const response = await apiService.rebuildCustomCollection(selectedCollection.id)
      const jobId = response.job_id

      // Poll job status for real progress - no timeout, wait for actual completion
      const pollInterval = setInterval(async () => {
        try {
          const jobStatus = await apiService.getRebuildJobStatus(jobId)

          // Update progress display
          setRebuildProgress(jobStatus.progress)

          if (jobStatus.status === 'completed') {
            clearInterval(pollInterval)
            setLoading(false)
            setRebuildStatus('completed')

            // Refresh collection data
            const updated = await apiService.getCollection(selectedCollection.id)
            setSelectedCollection(updated)
            await loadStatistics()
          } else if (jobStatus.status === 'failed') {
            clearInterval(pollInterval)
            setLoading(false)
            setRebuildStatus('error')
            setRebuildErrorMessage(jobStatus.error || 'Rebuild failed')
          }
          // If still running, continue polling
        } catch (err) {
          // Job endpoint error - might be temporary, keep polling
          console.error('Error polling job status:', err)
        }
      }, 2000)

    } catch (err) {
      setLoading(false)
      setRebuildStatus('error')
      setRebuildErrorMessage(err instanceof Error ? err.message : 'Failed to rebuild collection')
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  // PDF Document Management Functions
  const loadCollectionDocuments = async () => {
    if (!selectedCollection) return

    try {
      setLoading(true)
      const data = await apiService.getCollectionDocuments(selectedCollection.id, {
        page: documentsPage,
        page_size: pageSize
      })
      setCollectionDocuments(data.documents)
      setDocumentsTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  const loadAvailablePDFs = async () => {
    try {
      setLoading(true)
      const pdfs = await apiService.getAvailablePDFs()
      setAvailablePDFs(pdfs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load available PDFs')
    } finally {
      setLoading(false)
    }
  }

  const handleTogglePDF = (pdfPath: string) => {
    const newSelection = new Set(selectedPDFPaths)
    if (newSelection.has(pdfPath)) {
      newSelection.delete(pdfPath)
    } else {
      newSelection.add(pdfPath)
    }
    setSelectedPDFPaths(newSelection)
  }

  const handleSelectAllPDFs = () => {
    const allPaths = new Set(availablePDFs.map(pdf => pdf.path))
    setSelectedPDFPaths(allPaths)
  }

  const handleDeselectAllPDFs = () => {
    setSelectedPDFPaths(new Set())
  }

  const handleAddPDFs = async () => {
    if (!selectedCollection || selectedPDFPaths.size === 0) return

    try {
      setLoading(true)
      await apiService.addPDFsToCollection(selectedCollection.id, {
        document_paths: Array.from(selectedPDFPaths)
      })
      setSelectedPDFPaths(new Set())
      await loadAvailablePDFs()

      // Refresh collection
      const updated = await apiService.getCollection(selectedCollection.id)
      setSelectedCollection(updated)
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add PDFs')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveDocument = async (documentId: number) => {
    if (!selectedCollection) return

    try {
      setLoading(true)
      await apiService.removeDocumentsFromCollection(selectedCollection.id, {
        document_ids: [documentId]
      })
      await loadCollectionDocuments()

      // Refresh collection
      const updated = await apiService.getCollection(selectedCollection.id)
      setSelectedCollection(updated)
      await loadCollections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove document')
    } finally {
      setLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div style={{ display: 'flex', height: '100%', gap: '20px' }}>
      {/* Sidebar - Collection List */}
      <div style={{ width: '250px', borderRight: '1px solid #ccc', paddingRight: '20px' }}>
        <div style={{ marginBottom: '20px' }}>
          <h2>Collections</h2>
          <button
            onClick={() => setShowCreateDialog(true)}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            + Neue Collection
          </button>
        </div>

        <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
          {collections.map(collection => (
            <div
              key={collection.id}
              onClick={() => setSelectedCollection(collection)}
              style={{
                padding: '10px',
                marginBottom: '10px',
                backgroundColor: selectedCollection?.id === collection.id ? '#e3f2fd' : '#f5f5f5',
                borderRadius: '4px',
                cursor: 'pointer',
                border: selectedCollection?.id === collection.id ? '2px solid #2196F3' : '1px solid #ddd'
              }}
            >
              <div style={{ fontWeight: 'bold' }}>{collection.name}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                <span style={{ fontSize: '0.9em', color: '#666' }}>
                  {collection.question_count} Elemente
                </span>
                <span style={{
                  fontSize: '0.75em',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  backgroundColor: collection.collection_type === 'pdf' ? '#e3f2fd' : '#f3e5f5',
                  color: collection.collection_type === 'pdf' ? '#1976d2' : '#7b1fa2'
                }}>
                  {collection.collection_type}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1 }}>
        {error && (
          <div style={{
            padding: '10px',
            backgroundColor: '#f44336',
            color: 'white',
            marginBottom: '20px',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        )}

        {selectedCollection ? (
          <>
            {/* Collection Header */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h2>{selectedCollection.name}</h2>
                  {selectedCollection.description && (
                    <p style={{ color: '#666', margin: '5px 0' }}>{selectedCollection.description}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDeleteCollection(selectedCollection.id)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#f44336',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Collection löschen
                </button>
              </div>

              {/* Statistics */}
              <div style={{ display: 'flex', gap: '20px', marginTop: '15px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px', flexWrap: 'wrap', alignItems: 'center' }}>
                <div>
                  <strong>Fragen:</strong> {selectedCollection.question_count}
                </div>
                {statistics && (
                  <>
                    <div>
                      <strong>Durchschn. Score:</strong> {statistics.avg_score.toFixed(1)}
                    </div>
                    <div>
                      <strong>Durchschn. Ansichten:</strong> {statistics.avg_views.toFixed(0)}
                    </div>
                  </>
                )}
                <div>
                  <strong>Zuletzt neu erstellt:</strong> {formatDate(selectedCollection.last_rebuilt_at)}
                </div>
                <button
                  onClick={handleRebuildCollection}
                  disabled={loading}
                  style={{
                    padding: '5px 15px',
                    backgroundColor: '#FF9800',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    marginLeft: 'auto'
                  }}
                >
                  Rebuild ChromaDB
                </button>
              </div>

              {/* Model Information */}
              <div style={{ display: 'flex', gap: '20px', marginTop: '10px', padding: '12px 15px', backgroundColor: '#e8f4fd', borderRadius: '4px', alignItems: 'center' }}>
                <div>
                  <strong>Embedding Model:</strong>{' '}
                  <span style={{ fontFamily: 'monospace', backgroundColor: '#fff', padding: '2px 6px', borderRadius: '3px' }}>
                    {selectedCollection.embedding_model || 'N/A'}
                  </span>
                </div>
                {currentModels && (
                  <div>
                    <strong>LLM Model (aktiv):</strong>{' '}
                    <span style={{ fontFamily: 'monospace', backgroundColor: '#fff', padding: '2px 6px', borderRadius: '3px' }}>
                      {currentModels.llm_model}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Rebuild Status Banner */}
            {rebuildStatus === 'running' && (
              <div style={{
                padding: '12px 16px',
                backgroundColor: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '4px',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: rebuildProgress ? '8px' : '0' }}>
                  <span style={{ fontSize: '18px' }}>⏳</span>
                  <span>
                    Rebuild läuft...
                    {rebuildProgress && rebuildProgress.total_documents > 0 && (
                      <> Batch {rebuildProgress.current_batch}/{rebuildProgress.total_batches} ({Math.round((rebuildProgress.processed_documents / rebuildProgress.total_documents) * 100)}%)</>
                    )}
                    {rebuildProgress && rebuildProgress.phase === 'loading_documents' && ' (Lade Dokumente...)'}
                    {rebuildProgress && rebuildProgress.phase === 'documents_loaded' && ` (${rebuildProgress.total_documents} Dokumente geladen)`}
                  </span>
                </div>
                {rebuildProgress && rebuildProgress.total_documents > 0 && (
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#e9ecef',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${Math.round((rebuildProgress.processed_documents / rebuildProgress.total_documents) * 100)}%`,
                      height: '100%',
                      backgroundColor: '#ffc107',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                )}
              </div>
            )}
            {rebuildStatus === 'completed' && (
              <div style={{
                padding: '12px 16px',
                backgroundColor: '#d4edda',
                border: '1px solid #28a745',
                borderRadius: '4px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>✅</span>
                  <span>Rebuild abgeschlossen!</span>
                </div>
                <button
                  onClick={() => setRebuildStatus('idle')}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '18px',
                    cursor: 'pointer',
                    padding: '0 4px'
                  }}
                >
                  ✕
                </button>
              </div>
            )}
            {rebuildStatus === 'error' && (
              <div style={{
                padding: '12px 16px',
                backgroundColor: '#f8d7da',
                border: '1px solid #dc3545',
                borderRadius: '4px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>❌</span>
                  <span>Rebuild fehlgeschlagen: {rebuildErrorMessage || 'Unbekannter Fehler'}</span>
                </div>
                <button
                  onClick={() => {
                    setRebuildStatus('idle')
                    setRebuildErrorMessage(null)
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '18px',
                    cursor: 'pointer',
                    padding: '0 4px'
                  }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* Tabs - Conditional based on collection type */}
            <div style={{ borderBottom: '1px solid #ccc', marginBottom: '20px' }}>
              {selectedCollection.collection_type === 'stackoverflow' ? (
                <>
                  <button
                    onClick={() => setActiveTab('questions')}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: activeTab === 'questions' ? '#2196F3' : 'transparent',
                      color: activeTab === 'questions' ? 'white' : 'black',
                      border: 'none',
                      borderBottom: activeTab === 'questions' ? '2px solid #2196F3' : 'none',
                      cursor: 'pointer',
                      marginRight: '10px'
                    }}
                  >
                    Fragen in Collection ({selectedCollection.question_count})
                  </button>
                  <button
                    onClick={() => setActiveTab('add-questions')}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: activeTab === 'add-questions' ? '#2196F3' : 'transparent',
                      color: activeTab === 'add-questions' ? 'white' : 'black',
                      border: 'none',
                      borderBottom: activeTab === 'add-questions' ? '2px solid #2196F3' : 'none',
                      cursor: 'pointer'
                    }}
                  >
                    Fragen hinzufügen
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setActiveTab('documents')}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: activeTab === 'documents' ? '#2196F3' : 'transparent',
                      color: activeTab === 'documents' ? 'white' : 'black',
                      border: 'none',
                      borderBottom: activeTab === 'documents' ? '2px solid #2196F3' : 'none',
                      cursor: 'pointer',
                      marginRight: '10px'
                    }}
                  >
                    Dokumente in Collection ({selectedCollection.question_count})
                  </button>
                  <button
                    onClick={() => setActiveTab('add-documents')}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: activeTab === 'add-documents' ? '#2196F3' : 'transparent',
                      color: activeTab === 'add-documents' ? 'white' : 'black',
                      border: 'none',
                      borderBottom: activeTab === 'add-documents' ? '2px solid #2196F3' : 'none',
                      cursor: 'pointer'
                    }}
                  >
                    Dokumente hinzufügen
                  </button>
                </>
              )}
            </div>

            {/* Filters */}
            <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Nach Tags filtern (kommagetrennt)"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                style={{ padding: '8px', flex: 1, minWidth: '200px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
              <input
                type="number"
                placeholder="Min Score"
                value={minScore || ''}
                onChange={(e) => setMinScore(e.target.value ? parseInt(e.target.value) : undefined)}
                style={{ padding: '8px', width: '100px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(parseInt(e.target.value))
                  setCollectionPage(1)
                  setAvailablePage(1)
                }}
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                {TABLE_PAGE_SIZES.map(size => (
                  <option key={size} value={size}>{size} pro Seite</option>
                ))}
              </select>
              <button
                onClick={() => activeTab === 'questions' ? loadCollectionQuestions() : loadAvailableQuestions()}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Filter anwenden
              </button>
            </div>

            {/* Tab Content - Conditional based on collection type */}
            {selectedCollection.collection_type === 'stackoverflow' ? (
              // StackOverflow Collection Tabs
              activeTab === 'questions' ? (
              // Questions in Collection Tab
              <div>
                <div style={{ marginBottom: '10px' }}>
                  <strong>Gesamt: {collectionTotal} Fragen</strong>
                </div>

                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
                      <HeaderCell>Titel</HeaderCell>
                      <HeaderCell>Tags</HeaderCell>
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
                          setCollectionPage(1)
                        }}
                        align="center"
                      />
                      <SortableHeader
                        column="view_count"
                        label="Ansichten"
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                        onSort={(col) => {
                          if (sortBy === col) {
                            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                          } else {
                            setSortBy(col)
                            setSortOrder('desc')
                          }
                          setCollectionPage(1)
                        }}
                        align="center"
                      />
                      <SortableHeader
                        column="creation_date"
                        label="Datum"
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                        onSort={(col) => {
                          if (sortBy === col) {
                            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                          } else {
                            setSortBy(col)
                            setSortOrder('desc')
                          }
                          setCollectionPage(1)
                        }}
                        align="center"
                      />
                      <HeaderCell align="center">Aktionen</HeaderCell>
                    </tr>
                  </thead>
                  <tbody>
                    {collectionQuestions.map(question => (
                      <tr key={question.id} style={{ borderBottom: `1px solid ${TABLE_COLORS.rowBorder}` }}>
                        <td style={{ padding: '10px' }}>
                          <StackOverflowLink
                            stackOverflowId={question.stack_overflow_id}
                            title={question.title}
                          />
                        </td>
                        <td style={{ padding: '10px' }}>
                          <TagList tags={question.tags} maxTags={3} />
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          <span style={{ color: getScoreDisplayColor(question.score) }}>
                            {question.score}
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>{question.view_count}</td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          {question.creation_date ? new Date(question.creation_date).toLocaleDateString('de-DE') : '-'}
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemoveQuestion(question.id)}
                            style={{
                              padding: '5px 10px',
                              backgroundColor: '#f44336',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '0.85em'
                            }}
                          >
                            Entfernen
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination */}
                <TablePagination
                  page={collectionPage}
                  pageSize={pageSize}
                  totalItems={collectionTotal}
                  totalPages={Math.ceil(collectionTotal / pageSize)}
                  hasNext={collectionPage < Math.ceil(collectionTotal / pageSize)}
                  hasPrev={collectionPage > 1}
                  onPageChange={setCollectionPage}
                  onPageSizeChange={(size) => {
                    setPageSize(size)
                    setCollectionPage(1)
                  }}
                  pageSizeOptions={TABLE_PAGE_SIZES}
                />
              </div>
            ) : (
              // Add Questions Tab
              <div>
                <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>Verfügbare Fragen: {availableTotal}</strong>
                    {selectedQuestionIds.size > 0 && (
                      <span style={{ marginLeft: '20px', color: '#2196F3' }}>
                        {selectedQuestionIds.size} ausgewählt
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      onClick={handleSelectAll}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#9C27B0',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Alle auswählen
                    </button>
                    <button
                      onClick={handleDeselectAll}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#757575',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Auswahl aufheben
                    </button>
                    <button
                      onClick={handleAddQuestions}
                      disabled={selectedQuestionIds.size === 0}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: selectedQuestionIds.size === 0 ? '#ccc' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: selectedQuestionIds.size === 0 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      Ausgewählte hinzufügen ({selectedQuestionIds.size})
                    </button>
                  </div>
                </div>

                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
                      <HeaderCell align="center" width="40px">
                        <input
                          type="checkbox"
                          checked={availableQuestions.length > 0 && availableQuestions.every(q => selectedQuestionIds.has(q.id))}
                          onChange={(e) => {
                            if (e.target.checked) {
                              handleSelectAll()
                            } else {
                              handleDeselectAll()
                            }
                          }}
                        />
                      </HeaderCell>
                      <HeaderCell>Titel</HeaderCell>
                      <HeaderCell>Tags</HeaderCell>
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
                          setAvailablePage(1)
                        }}
                        align="center"
                      />
                      <SortableHeader
                        column="view_count"
                        label="Ansichten"
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                        onSort={(col) => {
                          if (sortBy === col) {
                            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                          } else {
                            setSortBy(col)
                            setSortOrder('desc')
                          }
                          setAvailablePage(1)
                        }}
                        align="center"
                      />
                      <SortableHeader
                        column="creation_date"
                        label="Datum"
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                        onSort={(col) => {
                          if (sortBy === col) {
                            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                          } else {
                            setSortBy(col)
                            setSortOrder('desc')
                          }
                          setAvailablePage(1)
                        }}
                        align="center"
                      />
                    </tr>
                  </thead>
                  <tbody>
                    {availableQuestions.map(question => (
                      <tr
                        key={question.id}
                        style={{
                          borderBottom: `1px solid ${TABLE_COLORS.rowBorder}`,
                          backgroundColor: selectedQuestionIds.has(question.id) ? TABLE_COLORS.selectedRow : 'transparent'
                        }}
                      >
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={selectedQuestionIds.has(question.id)}
                            onChange={() => handleToggleQuestion(question.id)}
                          />
                        </td>
                        <td style={{ padding: '10px' }}>
                          <StackOverflowLink
                            stackOverflowId={question.stack_overflow_id}
                            title={question.title}
                          />
                        </td>
                        <td style={{ padding: '10px' }}>
                          <TagList tags={question.tags} maxTags={3} />
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          <span style={{ color: getScoreDisplayColor(question.score) }}>
                            {question.score}
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>{question.view_count}</td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          {question.creation_date ? new Date(question.creation_date).toLocaleDateString('de-DE') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination */}
                <TablePagination
                  page={availablePage}
                  pageSize={pageSize}
                  totalItems={availableTotal}
                  totalPages={Math.ceil(availableTotal / pageSize)}
                  hasNext={availablePage < Math.ceil(availableTotal / pageSize)}
                  hasPrev={availablePage > 1}
                  onPageChange={setAvailablePage}
                  onPageSizeChange={(size) => {
                    setPageSize(size)
                    setAvailablePage(1)
                  }}
                  pageSizeOptions={TABLE_PAGE_SIZES}
                />
              </div>
              )
            ) : (
              // PDF Collection Tabs
              activeTab === 'documents' ? (
                // Documents in Collection Tab
                <div>
                  <div style={{ marginBottom: '10px' }}>
                    <strong>Gesamt: {documentsTotal} Dokumente</strong>
                  </div>

                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
                        <HeaderCell>Dokumentname</HeaderCell>
                        <HeaderCell>Pfad</HeaderCell>
                        <HeaderCell align="center">Hinzugefügt</HeaderCell>
                        <HeaderCell align="center">Aktionen</HeaderCell>
                      </tr>
                    </thead>
                    <tbody>
                      {collectionDocuments.map(doc => (
                        <tr key={doc.id} style={{ borderBottom: `1px solid ${TABLE_COLORS.rowBorder}` }}>
                          <td style={{ padding: '10px' }}>{doc.document_name}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em', color: '#666' }}>{doc.document_path}</td>
                          <td style={{ padding: '10px', textAlign: 'center', fontSize: '0.9em' }}>
                            {formatDate(doc.added_at)}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'center' }}>
                            <button
                              onClick={() => handleRemoveDocument(doc.id)}
                              style={{
                                padding: '5px 10px',
                                backgroundColor: '#f44336',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '0.85em'
                              }}
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Pagination */}
                  <TablePagination
                    page={documentsPage}
                    pageSize={pageSize}
                    totalItems={documentsTotal}
                    totalPages={Math.ceil(documentsTotal / pageSize)}
                    hasNext={documentsPage < Math.ceil(documentsTotal / pageSize)}
                    hasPrev={documentsPage > 1}
                    onPageChange={setDocumentsPage}
                    onPageSizeChange={(size) => {
                      setPageSize(size)
                      setDocumentsPage(1)
                    }}
                    pageSizeOptions={TABLE_PAGE_SIZES}
                  />
                </div>
              ) : (
                // Add Documents Tab
                <div>
                  <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>Verfügbare PDFs: {availablePDFs.length}</strong>
                      {selectedPDFPaths.size > 0 && (
                        <span style={{ marginLeft: '20px', color: '#2196F3' }}>
                          {selectedPDFPaths.size} ausgewählt
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button
                        onClick={handleSelectAllPDFs}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: '#9C27B0',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Select All
                      </button>
                      <button
                        onClick={handleDeselectAllPDFs}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: '#757575',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Deselect All
                      </button>
                      <button
                        onClick={handleAddPDFs}
                        disabled={selectedPDFPaths.size === 0}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: selectedPDFPaths.size === 0 ? '#ccc' : '#4CAF50',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: selectedPDFPaths.size === 0 ? 'not-allowed' : 'pointer'
                        }}
                      >
                        Ausgewählte hinzufügen ({selectedPDFPaths.size})
                      </button>
                    </div>
                  </div>

                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
                        <HeaderCell align="center" width="40px">
                          <input
                            type="checkbox"
                            checked={availablePDFs.length > 0 && availablePDFs.every(pdf => selectedPDFPaths.has(pdf.path))}
                            onChange={(e) => {
                              if (e.target.checked) {
                                handleSelectAllPDFs()
                              } else {
                                handleDeselectAllPDFs()
                              }
                            }}
                          />
                        </HeaderCell>
                        <HeaderCell>Dateiname</HeaderCell>
                        <HeaderCell>Pfad</HeaderCell>
                        <HeaderCell align="center">Größe</HeaderCell>
                        <HeaderCell align="center">Geändert</HeaderCell>
                      </tr>
                    </thead>
                    <tbody>
                      {availablePDFs.map(pdf => (
                        <tr
                          key={pdf.path}
                          style={{
                            borderBottom: `1px solid ${TABLE_COLORS.rowBorder}`,
                            backgroundColor: selectedPDFPaths.has(pdf.path) ? TABLE_COLORS.selectedRow : 'transparent'
                          }}
                        >
                          <td style={{ padding: '10px', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={selectedPDFPaths.has(pdf.path)}
                              onChange={() => handleTogglePDF(pdf.path)}
                            />
                          </td>
                          <td style={{ padding: '10px' }}>{pdf.name}</td>
                          <td style={{ padding: '10px', fontSize: '0.9em', color: '#666' }}>{pdf.path}</td>
                          <td style={{ padding: '10px', textAlign: 'center', fontSize: '0.9em' }}>
                            {formatFileSize(pdf.size)}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'center', fontSize: '0.9em' }}>
                            {formatDate(pdf.modified)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '50px', color: '#666' }}>
            <p>Keine Collection ausgewählt. Erstellen oder wählen Sie eine Collection, um zu beginnen.</p>
          </div>
        )}
      </div>

      {/* Create Collection Dialog */}
      {showCreateDialog && (
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
            padding: '30px',
            borderRadius: '8px',
            width: '500px',
            maxWidth: '90%'
          }}>
            <h3>Neue Collection erstellen</h3>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Collection-Name *
              </label>
              <input
                type="text"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #ccc'
                }}
                placeholder="e.g., MySQL High Quality"
              />
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Beschreibung (optional)
              </label>
              <textarea
                value={newCollectionDescription}
                onChange={(e) => setNewCollectionDescription(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                  minHeight: '80px'
                }}
                placeholder="Beschreibung dieser Collection..."
              />
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Collection-Typ *
              </label>
              <select
                value={newCollectionType}
                onChange={(e) => setNewCollectionType(e.target.value as 'stackoverflow' | 'pdf')}
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #ccc'
                }}
              >
                <option value="stackoverflow">StackOverflow-Fragen</option>
                <option value="pdf">PDF-Dokumente</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowCreateDialog(false)
                  setNewCollectionName('')
                  setNewCollectionDescription('')
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#757575',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Abbrechen
              </button>
              <button
                onClick={handleCreateCollection}
                disabled={!newCollectionName.trim() || loading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: !newCollectionName.trim() || loading ? '#ccc' : '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: !newCollectionName.trim() || loading ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Wird erstellt...' : 'Erstellen'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
