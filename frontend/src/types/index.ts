// Type Definitions

export enum GraphType {
  ADAPTIVE_RAG = 'adaptive_rag',
  SIMPLE_RAG = 'simple_rag',
  PURE_LLM = 'pure_llm'
}

export interface QueryRequest {
  question: string
  session_id: string
  include_stackoverflow: boolean
  graph_type?: GraphType
  retriever_type?: 'pdf' | 'stackoverflow'
  llm_config?: {
    temperature?: number
  }
}

export interface CollectionBreakdown {
  collection_name: string
  collection_type: string
  document_count: number
}

export interface IterationMetrics {
  generation_attempts: number
  transform_attempts: number
  total_iterations: number
  max_iterations_reached: boolean
  no_relevant_docs_fallback: boolean
  disclaimer?: string | null
}

export interface RetrievedDocument {
  id?: number
  source: string
  title?: string
  content_preview: string
  full_content?: string
  relevance_score?: number
  collection_name?: string
  metadata?: Record<string, any>
}

export interface QueryResponse {
  answer: string
  session_id: string
  graph_type?: string
  documents_retrieved: number
  stackoverflow_documents?: number
  processing_time_ms: number
  rewritten_question?: string
  source_breakdown?: Record<string, number>
  graph_trace?: string[]
  collection_breakdown?: CollectionBreakdown[]
  iteration_metrics?: IterationMetrics
  retrieved_documents?: RetrievedDocument[]
  node_timings?: Record<string, number>
}

export interface CollectionQueryRequest {
  question: string
  session_id: string
  collection_ids: number[]
  graph_type?: GraphType
  llm_config?: {
    temperature?: number
  }
}

export interface StackOverflowQuestion {
  id: number
  stack_overflow_id: number
  title: string
  body: string
  tags: string[] | string
  score: number
  view_count: number
  answers: StackOverflowAnswer[]
}

export interface StackOverflowAnswer {
  id: number
  stack_overflow_id: number
  body: string
  score: number
  is_accepted: boolean
}

export interface GeneratedAnswerResponse {
  question_id: number
  question_title: string
  question_body: string
  question_tags: string[] | string
  generated_answer: string
  processing_time_ms: number
  documents_retrieved: number
  stackoverflow_documents: number
  evaluation_id?: number
  existing_answers_count: number
}

export interface BertScoreResult {
  precision: number
  recall: number
  f1: number
  model_type: string
  interpretation: string
}

export interface CollectionStats {
  collection_name: string
  exists: boolean
  document_count: number
  embedding_model?: string
  created_at?: string
  last_used?: string
  total_questions?: number
  total_answers?: number
  accepted_answers?: number
  avg_question_score?: number
  avg_answer_score?: number
  vector_store_size?: number
}

export interface CollectionsResponse {
  collections: {
    pdf?: CollectionStats
    stackoverflow?: CollectionStats
  }
}

export interface RebuildResponse {
  message: string
  status: string
}

export interface ScrapeParams {
  count: number
  days_back: number
  tags: string[]
  min_score: number
  only_accepted_answers: boolean
  start_page?: number
}

export interface ScrapeJobStatus {
  job_id: string
  status: string
  started_at: string
  completed_at?: string
  progress?: {
    questions_fetched: number
    questions_stored: number
    answers_fetched: number
    answers_stored: number
    errors: number
  }
  result?: ScrapeJobResult
  error?: string
}

export interface ScrapeJobResult {
  questions_stored: number
  answers_stored: number
  questions_fetched?: number
  answers_fetched?: number
  errors?: number
}

export interface ScraperStats {
  total_questions: number
  total_answers: number
  accepted_answers: number
  recent_questions_7d: number
  avg_question_score: number
  avg_answer_score: number
  top_tags: Array<{tag: string, count: number}>
  database_url: string
}

export interface PaginatedQuestionsResponse {
  items: Array<{
    id: number
    stack_overflow_id: number
    title: string
    tags: string[]
    score: number
    view_count: number
    is_answered: boolean
    answer_count: number
    creation_date: string
    owner_display_name?: string
  }>
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export type ViewType = 'query' | 'data' | 'collection-management' | 'batch-queries' | 'batch-progress' | 'comparison'

// Collection Management Types

export interface Collection {
  id: number
  name: string
  description?: string
  collection_type: string
  question_count: number
  created_at: string
  last_rebuilt_at?: string
  // Health Status
  chroma_exists?: boolean
  needs_rebuild?: boolean
  last_health_check?: string
}

export interface CreateCollectionRequest {
  name: string
  description?: string
  collection_type?: string
}

export interface AddQuestionsRequest {
  question_ids: number[]
  added_by?: string
}

export interface RemoveQuestionsRequest {
  question_ids: number[]
}

export interface QuestionResponse {
  id: number
  stack_overflow_id: number
  title: string
  tags?: string
  score: number
  view_count: number
  is_answered: boolean
  creation_date?: string
}

export interface PaginatedCollectionQuestionsResponse {
  questions: QuestionResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CollectionStatistics {
  collection_id: number
  name: string
  description?: string
  question_count: number
  created_at?: string
  last_rebuilt_at?: string
  avg_score: number
  avg_views: number
  // Health Status
  chroma_exists?: boolean
  needs_rebuild?: boolean
  chroma_document_count?: number
  last_health_check?: string
  // Rebuild Error
  rebuild_error?: string
}

export interface RebuildCollectionResponse {
  message: string
  job_id: string
  collection_id: number
  collection_name: string
  question_count: number
  status: string
}

export interface RebuildJobProgress {
  total_documents: number
  processed_documents: number
  current_batch: number
  total_batches: number
  phase: string
}

export interface RebuildJobStatus {
  job_id: string
  status: 'running' | 'completed' | 'failed'
  progress: RebuildJobProgress
  parameters: {
    collection_id: number
    collection_name: string
  }
  started_at: string
  completed_at?: string
  error?: string
}

// PDF Document Management Types

export interface AvailablePDF {
  path: string
  name: string
  size: number
  modified: string
}

export interface DocumentResponse {
  id: number
  document_path: string
  document_name: string
  document_hash?: string
  added_at: string
  added_by?: string
}

export interface PaginatedDocumentsResponse {
  documents: DocumentResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AddDocumentsRequest {
  document_paths: string[]
  added_by?: string
}

export interface RemoveDocumentsRequest {
  document_ids: number[]
}

// Batch Query Processing Types

export interface BatchQueryRequest {
  question_ids: number[]
  session_id: string
  collection_ids?: number[]
  graph_types?: GraphType[]
  llm_config?: Record<string, any>
  include_graph_trace?: boolean
}

export interface BatchQueryResult {
  question_id: number
  question_title: string
  question_body?: string
  stack_overflow_id?: number
  graph_type: string
  status: 'success' | 'failed' | 'skipped'
  generated_answer?: string
  reference_answer?: string
  bert_score?: {
    precision: number
    recall: number
    f1: number
  }
  graph_trace?: string[]
  iteration_metrics?: IterationMetrics
  node_timings?: Record<string, number>
  processing_time_ms?: number
  error_message?: string
  evaluation_id?: number
  completed_at?: string
}

export interface BatchQueryProgress {
  total_questions: number
  processed: number
  successful: number
  failed: number
  skipped: number
  current_question_id?: number
  current_question_title?: string
}

export interface BatchQueryJobStatus {
  job_id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  started_at: string
  completed_at?: string
  progress: BatchQueryProgress
  parameters: Record<string, any>
  results: BatchQueryResult[]
  error?: string
}

export interface BatchQueryStartResponse {
  job_id: string
  message: string
  total_questions: number
}

// Rerun Feature Types

export interface RerunRequest {
  graph_types: string[]
  collection_ids?: number[]
  session_id: string
}

export interface RerunResponse {
  job_id: string
  message: string
  total_runs: number
  question_id: number
  question_title: string
}

// Question with Collections

export interface QuestionCollectionInfo {
  collection_id: number
  collection_name: string
  collection_type: string
  added_at: string
}

export interface QuestionWithCollections {
  id: number
  stack_overflow_id: number
  title: string
  tags: string[]
  score: number
  view_count: number
  is_answered: boolean
  creation_date: string
  collections: QuestionCollectionInfo[]
}

// Graph Comparison Types

export interface AcceptedAnswerInfo {
  stack_overflow_id: number
  body: string
  score: number
  owner_display_name?: string
  creation_date?: string
}

export interface EvaluationWithGraphType {
  id: number
  graph_type: string
  generated_answer: string
  bert_precision?: number
  bert_recall?: number
  bert_f1?: number
  processing_time_ms?: number
  manual_rating?: number
  created_at: string
  // New fields for detailed comparison view
  graph_trace?: string[]
  node_timings?: Record<string, number>
  rewritten_question?: string
  retrieved_documents?: RetrievedDocument[]
  iteration_metrics?: IterationMetrics
}

export interface GraphComparisonResponse {
  question_id: number
  question_title: string
  question_body: string
  accepted_answer?: AcceptedAnswerInfo
  evaluations_by_graph_type: Record<string, EvaluationWithGraphType[]>
}

export interface ComparisonMetricsSummary {
  graph_type: string
  avg_bert_f1?: number
  avg_bert_precision?: number
  avg_bert_recall?: number
  avg_processing_time_ms?: number
  evaluation_count: number
  latest_evaluation_date?: string
}

export interface EvaluatedQuestionListItem {
  question_id: number
  question_title: string
  available_graph_types: string[]
  total_evaluations: number
  has_multiple_graph_types: boolean
  tags: string[]
  score: number
}

export interface PaginatedEvaluatedQuestionsResponse {
  items: EvaluatedQuestionListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}
