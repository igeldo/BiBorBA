import { buildSearchParams } from '../utils/urlParams'
import type {
  QueryRequest,
  QueryResponse,
  CollectionQueryRequest,
  StackOverflowQuestion,
  GeneratedAnswerResponse,
  BertScoreResult,
  CollectionsResponse,
  RebuildResponse,
  ScrapeParams,
  ScrapeJobStatus,
  ScraperStats,
  PaginatedQuestionsResponse,
  Collection,
  CreateCollectionRequest,
  AddQuestionsRequest,
  RemoveQuestionsRequest,
  PaginatedCollectionQuestionsResponse,
  CollectionStatistics,
  RebuildCollectionResponse,
  RebuildJobStatus,
  AvailablePDF,
  PaginatedDocumentsResponse,
  AddDocumentsRequest,
  RemoveDocumentsRequest,
  BatchQueryRequest,
  BatchQueryStartResponse,
  BatchQueryJobStatus,
  QuestionWithCollections,
  GraphComparisonResponse,
  ComparisonMetricsSummary,
  PaginatedEvaluatedQuestionsResponse,
  FullExportRequest,
  StatisticsExportRequest,
  ComparisonExportRequest,
  ExportJobStartResponse,
  ExportJobStatus,
  CurrentModels,
  MissingQuestionsResponse,
  AggregatedStatisticsResponse
} from '../types'

export class ApiService {
  private baseUrl: string

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl
  }

  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async getStackOverflowQuestions(limit: number = 50, offset: number = 0): Promise<StackOverflowQuestion[]> {
    // Convert offset-based pagination to page-based
    const page = Math.floor(offset / limit) + 1
    const page_size = limit

    const response = await fetch(
      `${this.baseUrl}/api/v1/stackoverflow/questions?page=${page}&page_size=${page_size}`
    )

    if (!response.ok) {
      throw new Error(`Failed to get StackOverflow questions: ${response.status}`)
    }

    const data = await response.json()
    return data.items || []  // Backend gibt PaginatedQuestionsResponse zurück
  }

  async getStackOverflowQuestionDetails(questionId: number): Promise<StackOverflowQuestion> {
    const response = await fetch(`${this.baseUrl}/api/v1/stackoverflow/questions/${questionId}`)

    if (!response.ok) {
      throw new Error(`Failed to get question details: ${response.status}`)
    }

    const data = await response.json()
    return {
      ...data.question,
      answers: data.answers
    }
  }

  async generateStackOverflowAnswer(questionId: number, sessionId: string, temperature: number = 0.1): Promise<GeneratedAnswerResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/stackoverflow/generate-answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question_id: questionId,
        session_id: sessionId,
        llm_config: {
          temperature: temperature
        }
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to generate answer: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async getBertScore(generatedAnswer: string, referenceAnswer: string): Promise<BertScoreResult> {
    const response = await fetch(`${this.baseUrl}/api/v1/evaluation/bert-score`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        generated_answer: generatedAnswer,
        reference_answer: referenceAnswer
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to compute BERT score: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async submitManualEvaluation(evaluationId: number, rating: number, comment: string = '', evaluatorName: string = ''): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/evaluation/evaluations/${evaluationId}/manual`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        rating: rating,
        comment: comment,
        evaluator_name: evaluatorName
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to submit evaluation: ${response.status} - ${error}`)
    }
  }

  async getCollections(): Promise<CollectionsResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/collections`)
    if (!response.ok) throw new Error('Failed to fetch collections')
    return response.json()
  }

  async rebuildCollection(collectionType: string): Promise<RebuildResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collections/${collectionType}/rebuild`,
      { method: 'POST' }
    )
    if (!response.ok) throw new Error(`Failed to rebuild ${collectionType}`)
    return response.json()
  }

  // Stackoverflow Scraping & Data Management
  async startScraping(params: ScrapeParams): Promise<ScrapeJobStatus> {
    const response = await fetch(`${this.baseUrl}/api/v1/scraper/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    })
    if (!response.ok) throw new Error('Failed to start scraping')
    return response.json()
  }

  async getScrapeJobStatus(jobId: string): Promise<ScrapeJobStatus> {
    const response = await fetch(`${this.baseUrl}/api/v1/scraper/jobs/${jobId}`)
    if (!response.ok) throw new Error('Failed to get job status')
    return response.json()
  }

  async getScraperStats(): Promise<ScraperStats> {
    const response = await fetch(`${this.baseUrl}/api/v1/scraper/stats`)
    if (!response.ok) throw new Error('Failed to get scraper stats')
    return response.json()
  }

  async getQuestionsPaginated(params: {
    page: number
    page_size: number
    tags?: string
    min_score?: number
    sort_by?: string
    sort_order?: string
  }): Promise<PaginatedQuestionsResponse> {
    const searchParams = buildSearchParams(params)
    const response = await fetch(`${this.baseUrl}/api/v1/stackoverflow/questions?${searchParams}`)
    if (!response.ok) throw new Error('Failed to get questions')
    return response.json()
  }

  async testStackoverflowApi(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/scraper/test-api`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to test API')
    return response.json()
  }

  // Collection Management

  async createCollection(request: CreateCollectionRequest): Promise<Collection> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to create collection: ${error}`)
    }
    return response.json()
  }

  async getCollectionsList(): Promise<Collection[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections`)
    if (!response.ok) throw new Error('Failed to get collections')
    return response.json()
  }

  async getCurrentModels(): Promise<CurrentModels> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/current-models`)
    if (!response.ok) throw new Error('Failed to get current models')
    return response.json()
  }

  async getCollection(collectionId: number): Promise<Collection> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections/${collectionId}`)
    if (!response.ok) throw new Error('Failed to get collection')
    return response.json()
  }

  async deleteCollection(collectionId: number): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections/${collectionId}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error('Failed to delete collection')
  }

  async addQuestionsToCollection(collectionId: number, request: AddQuestionsRequest): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) throw new Error('Failed to add questions')
    return response.json()
  }

  async removeQuestionsFromCollection(collectionId: number, request: RemoveQuestionsRequest): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/questions`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) throw new Error('Failed to remove questions')
    return response.json()
  }

  async getCollectionQuestions(
    collectionId: number,
    params: {
      page: number
      page_size: number
      tags?: string
      min_score?: number
      sort_by?: string
      sort_order?: string
    }
  ): Promise<PaginatedCollectionQuestionsResponse> {
    const searchParams = buildSearchParams(params)
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/questions?${searchParams}`
    )
    if (!response.ok) throw new Error('Failed to get collection questions')
    return response.json()
  }

  async getTestQuestions(
    collectionId: number,
    params: {
      page: number
      page_size: number
      tags?: string
      min_score?: number
      sort_by?: string
      sort_order?: string
    }
  ): Promise<PaginatedCollectionQuestionsResponse> {
    const searchParams = buildSearchParams(params)
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/test-questions?${searchParams}`
    )
    if (!response.ok) throw new Error('Failed to get test questions')
    return response.json()
  }

  async getCollectionStatistics(collectionId: number): Promise<CollectionStatistics> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/statistics`
    )
    if (!response.ok) throw new Error('Failed to get collection statistics')
    return response.json()
  }

  async rebuildCustomCollection(collectionId: number): Promise<RebuildCollectionResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/rebuild`,
      { method: 'POST' }
    )
    if (!response.ok) throw new Error('Failed to rebuild collection')
    return response.json()
  }

  async getRebuildJobStatus(jobId: string): Promise<RebuildJobStatus> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/rebuild-jobs/${jobId}`
    )
    if (!response.ok) throw new Error('Failed to get rebuild job status')
    return response.json()
  }

  // Collection-based Query

  async queryCollections(request: CollectionQueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/query/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Collection query failed: ${error}`)
    }
    return response.json()
  }

  // PDF Document Management

  async getAvailablePDFs(): Promise<AvailablePDF[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/collection-management/available-pdfs`)
    if (!response.ok) throw new Error('Failed to get available PDFs')
    return response.json()
  }

  async addPDFsToCollection(collectionId: number, request: AddDocumentsRequest): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/documents`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      }
    )
    if (!response.ok) throw new Error('Failed to add PDFs to collection')
    return response.json()
  }

  async getCollectionDocuments(
    collectionId: number,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedDocumentsResponse> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())

    const url = `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/documents${
      searchParams.toString() ? `?${searchParams}` : ''
    }`

    const response = await fetch(url)
    if (!response.ok) throw new Error('Failed to get collection documents')
    return response.json()
  }

  async removeDocumentsFromCollection(
    collectionId: number,
    request: RemoveDocumentsRequest
  ): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/collection-management/collections/${collectionId}/documents`,
      {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      }
    )
    if (!response.ok) throw new Error('Failed to remove documents from collection')
    return response.json()
  }

  // Batch Query API Methods

  async startBatchQuery(request: BatchQueryRequest): Promise<BatchQueryStartResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/batch-queries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to start batch query: ${response.status} - ${error}`)
    }
    return response.json()
  }

  async getBatchQueryStatus(jobId: string): Promise<BatchQueryJobStatus> {
    const response = await fetch(`${this.baseUrl}/api/v1/batch-queries/${jobId}`)
    if (!response.ok) {
      throw new Error(`Failed to get batch query status: ${response.status}`)
    }
    return response.json()
  }

  async listBatchQueryJobs(
    status?: string,
    limit: number = 20
  ): Promise<BatchQueryJobStatus[]> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())

    const response = await fetch(
      `${this.baseUrl}/api/v1/batch-queries?${params}`
    )
    if (!response.ok) {
      throw new Error(`Failed to list batch query jobs: ${response.status}`)
    }
    return response.json()
  }

  async deleteBatchQueryJob(jobId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/batch-queries/${jobId}`,
      { method: 'DELETE' }
    )
    if (!response.ok) {
      throw new Error(`Failed to delete batch query job: ${response.status}`)
    }
  }

  async cancelBatchQueryJob(jobId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/batch-queries/${jobId}/cancel`,
      { method: 'POST' }
    )
    if (!response.ok) {
      throw new Error(`Failed to cancel batch query job: ${response.status}`)
    }
  }

  // Questions with Collections

  async getQuestionsWithCollections(params: {
    page?: number
    page_size?: number
    tags?: string
    min_score?: number
    sort_by?: 'creation_date' | 'score' | 'view_count'
    sort_order?: 'asc' | 'desc'
    only_without_collections?: boolean
    not_in_collection_ids?: number[]
    only_without_evaluations?: boolean
  }): Promise<{
    items: QuestionWithCollections[]
    total: number
    page: number
    page_size: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }> {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        if (key === 'not_in_collection_ids' && Array.isArray(value)) {
          queryParams.append(key, value.join(','))
        } else {
          queryParams.append(key, value.toString())
        }
      }
    })

    const response = await fetch(
      `${this.baseUrl}/api/v1/stackoverflow/questions-with-collections?${queryParams}`
    )
    if (!response.ok) {
      throw new Error(`Failed to get questions with collections: ${response.status}`)
    }
    return response.json()
  }

  // Graph Comparison API Methods

  async getAvailableModels(): Promise<{
    llm_models: string[]
    embedding_models: string[]
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/comparisons/available-models`)
    if (!response.ok) {
      throw new Error(`Failed to fetch available models: ${response.status}`)
    }
    return response.json()
  }

  async getAggregatedStatistics(params?: {
    group_by?: ('graph_type' | 'llm_model' | 'embedding_model')[]
  }): Promise<AggregatedStatisticsResponse> {
    const queryParams = new URLSearchParams()
    if (params?.group_by && params.group_by.length > 0) {
      queryParams.set('group_by', params.group_by.join(','))
    }

    const url = `${this.baseUrl}/api/v1/comparisons/aggregated-statistics${
      queryParams.toString() ? `?${queryParams}` : ''
    }`

    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to fetch aggregated statistics: ${response.status}`)
    }
    return response.json()
  }

  async getComparisonForQuestion(questionId: number): Promise<GraphComparisonResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/comparisons/questions/${questionId}`
    )
    if (!response.ok) {
      throw new Error(`Failed to get comparison for question: ${response.status}`)
    }
    return response.json()
  }

  async getComparisonMetrics(questionId: number): Promise<ComparisonMetricsSummary[]> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/comparisons/questions/${questionId}/metrics`
    )
    if (!response.ok) {
      throw new Error(`Failed to get comparison metrics: ${response.status}`)
    }
    return response.json()
  }

  async getAllEvaluatedQuestions(params?: {
    page?: number
    page_size?: number
    sort_by?: string
    sort_order?: string
    tags?: string
    title_search?: string
  }): Promise<PaginatedEvaluatedQuestionsResponse> {
    const queryParams = new URLSearchParams()
    if (params?.page !== undefined) queryParams.set('page', params.page.toString())
    if (params?.page_size !== undefined) queryParams.set('page_size', params.page_size.toString())
    if (params?.sort_by) queryParams.set('sort_by', params.sort_by)
    if (params?.sort_order) queryParams.set('sort_order', params.sort_order)
    if (params?.tags) queryParams.set('tags', params.tags)
    if (params?.title_search) queryParams.set('title_search', params.title_search)

    const url = `${this.baseUrl}/api/v1/comparisons/questions${
      queryParams.toString() ? `?${queryParams}` : ''
    }`

    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to get evaluated questions: ${response.status}`)
    }
    return response.json()
  }

  // Rerun Evaluation

  async rerunQuestionEvaluation(
    questionId: number,
    request: { graph_types: string[]; collection_ids?: number[]; session_id: string }
  ): Promise<{ job_id: string; message: string; total_runs: number; question_id: number; question_title: string }> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/comparisons/questions/${questionId}/rerun`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      }
    )
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to start rerun: ${error}`)
    }
    return response.json()
  }

  // Evaluation Rating (for comparison view)

  async rateEvaluation(evaluationId: number, rating: number, comment?: string): Promise<{
    message: string
    evaluation_id: number
    rating: number
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/evaluation/evaluations/${evaluationId}/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rating: rating,
        comment: comment || ''
      })
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to rate evaluation: ${error}`)
    }
    return response.json()
  }

  // Query Rating

  async rateQuery(sessionId: string, rating: number, comment?: string): Promise<{
    message: string
    session_id: string
    rating: number
    query_id: number
  }> {
    const response = await fetch(`${this.baseUrl}/api/v1/query/rate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        rating: rating,
        comment: comment
      })
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to rate query: ${error}`)
    }
    return response.json()
  }

  // Export API Methods

  async startFullExport(request: FullExportRequest): Promise<ExportJobStartResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/full`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to start full export: ${error}`)
    }
    return response.json()
  }

  async startStatisticsExport(request: StatisticsExportRequest): Promise<ExportJobStartResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/statistics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to start statistics export: ${error}`)
    }
    return response.json()
  }

  async startComparisonExport(request: ComparisonExportRequest): Promise<ExportJobStartResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/comparison`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to start comparison export: ${error}`)
    }
    return response.json()
  }

  async getExportJobStatus(jobId: string): Promise<ExportJobStatus> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/jobs/${jobId}`)
    if (!response.ok) {
      throw new Error(`Failed to get export job status: ${response.status}`)
    }
    return response.json()
  }

  async listExportJobs(status?: string, limit: number = 20): Promise<ExportJobStatus[]> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())

    const response = await fetch(`${this.baseUrl}/api/v1/export/jobs?${params}`)
    if (!response.ok) {
      throw new Error(`Failed to list export jobs: ${response.status}`)
    }
    return response.json()
  }

  async downloadExport(jobId: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/jobs/${jobId}/download`)
    if (!response.ok) {
      throw new Error(`Failed to download export: ${response.status}`)
    }
    return response.blob()
  }

  async deleteExportJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/export/jobs/${jobId}`, {
      method: 'DELETE'
    })
    if (!response.ok) {
      throw new Error(`Failed to delete export job: ${response.status}`)
    }
  }

  // Missing Questions Coverage API

  async getMissingQuestions(params?: {
    graphTypes?: string[]
    excludeCollectionIds?: number[]
    page?: number
    pageSize?: number
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
  }): Promise<MissingQuestionsResponse> {
    const queryParams = new URLSearchParams()
    if (params?.graphTypes && params.graphTypes.length > 0) {
      queryParams.append('graph_types', params.graphTypes.join(','))
    }
    if (params?.excludeCollectionIds && params.excludeCollectionIds.length > 0) {
      queryParams.append('exclude_collection_ids', params.excludeCollectionIds.join(','))
    }
    if (params?.page !== undefined) {
      queryParams.append('page', params.page.toString())
    }
    if (params?.pageSize !== undefined) {
      queryParams.append('page_size', params.pageSize.toString())
    }
    if (params?.sortBy) {
      queryParams.append('sort_by', params.sortBy)
    }
    if (params?.sortOrder) {
      queryParams.append('sort_order', params.sortOrder)
    }

    const url = `${this.baseUrl}/api/v1/batch-queries/missing-questions${
      queryParams.toString() ? `?${queryParams}` : ''
    }`

    const response = await fetch(url)
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to get missing questions: ${response.status} - ${error}`)
    }
    return response.json()
  }
}

export const apiService = new ApiService()
