import { useState, useEffect, useCallback, useRef } from 'react'
import { apiService } from '../../services/api'
import type {
  GraphComparisonResponse,
  ComparisonMetricsSummary,
  PaginatedEvaluatedQuestionsResponse,
  Collection,
  BatchQueryJobStatus,
  ExportFormat,
  ExportJobStatus
} from '../../types'
import { DEFAULT_PAGE_SIZE } from '../../theme/tableConstants'
import {
  QuestionFilters,
  QuestionList,
  QuestionHeader,
  ReferenceAnswer,
  MetricsSummary,
  EvaluationTable,
  RerunModal,
  ExportModal,
  GlobalStatistics
} from '../comparison'

type ExportScope = 'all' | 'comparison_filter' | 'custom'

export function ComparisonView() {
  // Question list state
  const [paginatedData, setPaginatedData] = useState<PaginatedEvaluatedQuestionsResponse | null>(null)
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null)
  const [comparisonData, setComparisonData] = useState<GraphComparisonResponse | null>(null)
  const [metricsData, setMetricsData] = useState<ComparisonMetricsSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  // Filter state
  const [tagFilter, setTagFilter] = useState('')
  const [titleSearch, setTitleSearch] = useState('')

  // Sort state
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Rerun Modal state
  const [showRerunModal, setShowRerunModal] = useState(false)
  const [rerunGraphTypes, setRerunGraphTypes] = useState<string[]>(['adaptive_rag'])
  const [rerunCollections, setRerunCollections] = useState<number[]>([])
  const [rerunJobId, setRerunJobId] = useState<string | null>(null)
  const [rerunJobStatus, setRerunJobStatus] = useState<BatchQueryJobStatus | null>(null)
  const [rerunLoading, setRerunLoading] = useState(false)
  const [availableCollections, setAvailableCollections] = useState<Collection[]>([])

  // Export Modal state
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json')
  const [exportType, setExportType] = useState<'full' | 'statistics' | 'comparison'>('statistics')
  const [exportJobId, setExportJobId] = useState<string | null>(null)
  const [exportJobStatus, setExportJobStatus] = useState<ExportJobStatus | null>(null)
  const [exportLoading, setExportLoading] = useState(false)
  const [exportIncludeDocuments, setExportIncludeDocuments] = useState(true)
  const [exportIncludeFullAnswers, setExportIncludeFullAnswers] = useState(true)
  const [exportGroupByGraphType, setExportGroupByGraphType] = useState(true)
  const [exportGroupByLLM, setExportGroupByLLM] = useState(false)
  const [exportGroupByEmbedding, setExportGroupByEmbedding] = useState(false)
  const [exportScope, setExportScope] = useState<ExportScope>('all')
  const [exportLlmModel, setExportLlmModel] = useState<string>('')
  const [exportEmbeddingModel, setExportEmbeddingModel] = useState<string>('')
  const [exportDeduplicateLatest, setExportDeduplicateLatest] = useState(false)

  // Available models for export modal
  const [availableModels, setAvailableModels] = useState<{
    llm_models: string[]
    embedding_models: string[]
  }>({ llm_models: [], embedding_models: [] })

  // Ref for scrolling to comparison section
  const comparisonSectionRef = useRef<HTMLDivElement>(null)

  // Load available models on mount (for export modal)
  useEffect(() => {
    apiService.getAvailableModels()
      .then(setAvailableModels)
      .catch(err => console.error('Failed to load available models:', err))
  }, [])

  // Load evaluated questions
  useEffect(() => {
    loadEvaluatedQuestions()
  }, [currentPage, pageSize, sortBy, sortOrder])

  const loadEvaluatedQuestions = async () => {
    try {
      setLoading(true)
      const result = await apiService.getAllEvaluatedQuestions({
        page: currentPage,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
        tags: tagFilter || undefined,
        title_search: titleSearch || undefined
      })
      setPaginatedData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }

  const handleFilterSearch = () => {
    setCurrentPage(1)
    loadEvaluatedQuestions()
  }

  const handleColumnSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
    setCurrentPage(1)
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

      // Scroll to detail view
      setTimeout(() => {
        comparisonSectionRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        })
      }, 100)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comparison data')
    } finally {
      setLoading(false)
    }
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
        setTimeout(() => pollRerunStatus(jobId), 1000)
      } else if (status.status === 'completed') {
        setRerunLoading(false)
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

  // Export feature functions
  const openExportModal = () => {
    setExportJobId(null)
    setExportJobStatus(null)
    setExportLoading(false)
    setShowExportModal(true)
  }

  const closeExportModal = () => {
    setShowExportModal(false)
    setExportJobId(null)
    setExportJobStatus(null)
    setExportLoading(false)
  }

  const startExport = async () => {
    setExportLoading(true)
    try {
      let filters = undefined

      if (exportScope === 'comparison_filter') {
        filters = {
          tags: tagFilter ? tagFilter.split(',').map(t => t.trim()) : undefined
        }
      } else if (exportScope === 'custom') {
        filters = {
          llm_model: exportLlmModel || undefined,
          embedding_model: exportEmbeddingModel || undefined
        }
      }

      if (exportDeduplicateLatest) {
        filters = { ...filters, deduplicate_latest_only: true }
      }

      const groupByFields: string[] = []
      if (exportGroupByGraphType) groupByFields.push('graph_type')
      if (exportGroupByLLM) groupByFields.push('llm_model')
      if (exportGroupByEmbedding) groupByFields.push('embedding_model')
      if (groupByFields.length === 0) groupByFields.push('graph_type')

      let response
      if (exportType === 'full') {
        response = await apiService.startFullExport({
          format: exportFormat,
          filters,
          include_retrieved_documents: exportIncludeDocuments,
          include_full_answers: exportIncludeFullAnswers,
          include_node_timings: true
        })
      } else if (exportType === 'statistics') {
        response = await apiService.startStatisticsExport({
          format: exportFormat,
          filters,
          group_by: groupByFields,
          include_confidence_intervals: true,
          include_std: true
        })
      } else {
        response = await apiService.startComparisonExport({
          format: exportFormat,
          filters,
          baseline_graph_type: 'pure_llm',
          metric: 'bert_f1'
        })
      }

      setExportJobId(response.job_id)
      pollExportStatus(response.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start export')
      setExportLoading(false)
    }
  }

  const pollExportStatus = async (jobId: string) => {
    try {
      const status = await apiService.getExportJobStatus(jobId)
      setExportJobStatus(status)

      if (status.status === 'running') {
        setTimeout(() => pollExportStatus(jobId), 1000)
      } else if (status.status === 'completed') {
        setExportLoading(false)
      } else if (status.status === 'failed') {
        setExportLoading(false)
        setError(status.error || 'Export failed')
      }
    } catch (err) {
      setExportLoading(false)
      setError(err instanceof Error ? err.message : 'Failed to get export status')
    }
  }

  const downloadExportFile = async () => {
    if (!exportJobId) return

    try {
      const blob = await apiService.downloadExport(exportJobId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      const ext = exportFormat === 'csv' ? 'csv' : exportFormat === 'latex' ? 'tex' : 'json'
      link.download = `export_${exportType}_${new Date().toISOString().slice(0, 10)}.${ext}`

      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download export')
    }
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h1 style={{ margin: 0 }}>Antworten-Vergleich</h1>
        <button
          onClick={openExportModal}
          style={{
            padding: '10px 20px',
            backgroundColor: '#28a745',
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
          Exportieren
        </button>
      </div>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Vergleiche die Performance verschiedener Graph-Typen auf denselben Fragen
      </p>

      {/* Global Statistics Section */}
      <GlobalStatistics defaultExpanded={true} />

      {/* Question List Section */}
      <div style={{ marginBottom: '32px' }}>
        <h2>Evaluierte Fragen</h2>

        <QuestionFilters
          titleSearch={titleSearch}
          setTitleSearch={setTitleSearch}
          tagFilter={tagFilter}
          setTagFilter={setTagFilter}
          onSearch={handleFilterSearch}
        />

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
          </div>
        )}

        {paginatedData && paginatedData.items.length > 0 && (
          <QuestionList
            items={paginatedData.items}
            selectedQuestionId={selectedQuestionId}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleColumnSort}
            onSelectQuestion={loadComparisonData}
            page={paginatedData.page}
            pageSize={pageSize}
            totalItems={paginatedData.total}
            totalPages={paginatedData.total_pages}
            hasNext={paginatedData.has_next}
            hasPrev={paginatedData.has_prev}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size)
              setCurrentPage(1)
            }}
          />
        )}
      </div>

      {/* Comparison Details Section */}
      {comparisonData && (
        <div ref={comparisonSectionRef}>
          <QuestionHeader
            title={comparisonData.question_title}
            body={comparisonData.question_body}
            onRerun={openRerunModal}
          />

          {comparisonData.accepted_answer && (
            <ReferenceAnswer acceptedAnswer={comparisonData.accepted_answer} />
          )}

          <MetricsSummary metricsData={metricsData} />

          {/* New Evaluation Table with Side-by-Side Expansion */}
          <EvaluationTable
            evaluationsByGraphType={comparisonData.evaluations_by_graph_type}
            referenceAnswer={comparisonData.accepted_answer}
          />
        </div>
      )}

      {/* Error Display */}
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
      <RerunModal
        isOpen={showRerunModal}
        onClose={closeRerunModal}
        questionTitle={comparisonData?.question_title || ''}
        selectedGraphTypes={rerunGraphTypes}
        onToggleGraphType={toggleGraphType}
        selectedCollections={rerunCollections}
        onToggleCollection={toggleCollection}
        availableCollections={availableCollections}
        jobId={rerunJobId}
        jobStatus={rerunJobStatus}
        isLoading={rerunLoading}
        onStartRerun={startRerun}
      />

      {/* Export Modal */}
      <ExportModal
        isOpen={showExportModal}
        onClose={closeExportModal}
        exportType={exportType}
        setExportType={setExportType}
        exportFormat={exportFormat}
        setExportFormat={setExportFormat}
        includeDocuments={exportIncludeDocuments}
        setIncludeDocuments={setExportIncludeDocuments}
        includeFullAnswers={exportIncludeFullAnswers}
        setIncludeFullAnswers={setExportIncludeFullAnswers}
        groupByGraphType={exportGroupByGraphType}
        setGroupByGraphType={setExportGroupByGraphType}
        groupByLLM={exportGroupByLLM}
        setGroupByLLM={setExportGroupByLLM}
        groupByEmbedding={exportGroupByEmbedding}
        setGroupByEmbedding={setExportGroupByEmbedding}
        exportScope={exportScope}
        setExportScope={setExportScope}
        exportLlmModel={exportLlmModel}
        setExportLlmModel={setExportLlmModel}
        exportEmbeddingModel={exportEmbeddingModel}
        setExportEmbeddingModel={setExportEmbeddingModel}
        deduplicateLatest={exportDeduplicateLatest}
        setDeduplicateLatest={setExportDeduplicateLatest}
        availableModels={availableModels}
        activeFilters={{
          tagFilter
        }}
        jobId={exportJobId}
        jobStatus={exportJobStatus}
        isLoading={exportLoading}
        onStartExport={startExport}
        onDownload={downloadExportFile}
      />
    </div>
  )
}
