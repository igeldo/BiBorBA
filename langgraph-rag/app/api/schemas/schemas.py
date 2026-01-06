# api/schemas.py

from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RetrieverType(str, Enum):
    """Types of document retrievers available"""
    PDF = "pdf"
    STACKOVERFLOW = "stackoverflow"


class GraphType(str, Enum):
    """Types of RAG graphs available for comparison"""
    ADAPTIVE_RAG = "adaptive_rag"
    SIMPLE_RAG = "simple_rag"
    PURE_LLM = "pure_llm"


class SortField(str, Enum):
    """Valid sort fields for question listings"""
    CREATION_DATE = "creation_date"
    SCORE = "score"
    VIEW_COUNT = "view_count"


class SortOrder(str, Enum):
    """Sort order for listings"""
    ASC = "asc"
    DESC = "desc"


class StackOverflowQueryRequest(BaseModel):
    """Request schema for StackOverflow queries"""
    question: str = Field(..., description="The question to ask")
    session_id: str = Field(..., description="Session identifier")
    graph_type: GraphType = Field(default=GraphType.ADAPTIVE_RAG, description="Type of graph to use for processing")
    include_stackoverflow: bool = Field(default=True, description="Include StackOverflow data in search")
    stackoverflow_filters: Optional[Dict[str, Any]] = Field(
        default={
            "min_score": 0,
            "tags": [],
            "only_accepted_answers": False,
            "limit": 50
        },
        description="Filters for StackOverflow data"
    )
    llm_config: Optional[Dict[str, Any]] = Field(default={}, description="LLM configuration")


class CollectionQueryRequest(BaseModel):
    """Request schema for collection-based queries"""
    question: str = Field(..., description="The question to ask")
    session_id: str = Field(..., description="Session identifier")
    graph_type: GraphType = Field(default=GraphType.ADAPTIVE_RAG, description="Type of graph to use for processing")
    collection_ids: List[int] = Field(..., description="List of collection IDs to search")
    llm_config: Optional[Dict[str, Any]] = Field(default={}, description="LLM configuration")


class GenerateAnswerRequest(BaseModel):
    """Request to generate new answer for StackOverflow question"""
    question_id: int = Field(..., description="StackOverflow question ID")
    session_id: str = Field(..., description="Session identifier")
    llm_config: Optional[Dict[str, Any]] = Field(default={}, description="LLM configuration")


class StackOverflowStats(BaseModel):
    """Statistics about StackOverflow data usage"""
    total_questions: int
    total_answers: int
    avg_question_score: float
    avg_answer_score: float
    most_common_tags: List[str]
    collection_size: int
    last_updated: Optional[datetime]


class CollectionBreakdown(BaseModel):
    """Collection breakdown in query response"""
    collection_name: str = Field(..., description="Name of the collection")
    collection_type: str = Field(..., description="Type of collection (stackoverflow, pdf)")
    document_count: int = Field(..., description="Number of documents retrieved from this collection")


class IterationMetrics(BaseModel):
    """Metrics about graph iteration behavior"""
    generation_attempts: int = Field(default=0, description="Anzahl Generation-Versuche")
    transform_attempts: int = Field(default=0, description="Anzahl Query-Transformationen")
    total_iterations: int = Field(default=0, description="Gesamtanzahl Graph-Iterationen")
    max_iterations_reached: bool = Field(default=False, description="Max Iterations erreicht")
    no_relevant_docs_fallback: bool = Field(default=False, description="Pure LLM Fallback verwendet")
    disclaimer: Optional[str] = Field(default=None, description="Disclaimer-Text falls vorhanden")


class RetrievedDocument(BaseModel):
    """Details of a retrieved document for display"""
    source: str = Field(..., description="Source type: 'pdf' or 'stackoverflow'")
    title: Optional[str] = Field(default=None, description="Document title if available")
    content_preview: str = Field(..., description="First 200 characters of content")
    full_content: Optional[str] = Field(default=None, description="Full document content for expandable view")
    relevance_score: Optional[float] = Field(default=None, description="Relevance/similarity score if available")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class QueryRatingRequest(BaseModel):
    """Request to rate a query result"""
    session_id: str = Field(..., description="Session identifier of the query to rate")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    comment: Optional[str] = Field(default=None, description="Optional comment for the rating")


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    graph_type: str = Field(default="adaptive_rag", description="Type of graph used (adaptive_rag, simple_rag, pure_llm)")
    documents_retrieved: int
    stackoverflow_documents: int = Field(default=0, description="Number of StackOverflow documents used")
    processing_time_ms: int
    rewritten_question: Optional[str] = None
    graph_trace: Optional[List[str]] = None
    source_breakdown: Optional[Dict[str, int]] = Field(
        default={},
        description="Breakdown of sources used (pdf, stackoverflow, etc.)"
    )
    collection_breakdown: Optional[List[CollectionBreakdown]] = Field(
        default=None,
        description="Breakdown of collections used in the query"
    )
    iteration_metrics: Optional[IterationMetrics] = Field(
        default=None,
        description="Iteration metrics for loop prevention tracking"
    )
    retrieved_documents: Optional[List[RetrievedDocument]] = Field(
        default=None,
        description="Details of retrieved documents"
    )
    node_timings: Optional[Dict[str, float]] = Field(
        default=None,
        description="Execution time in ms for each graph node"
    )


class ScrapeRequest(BaseModel):
    """Request to start scraping job"""
    count: int = Field(100, ge=1, le=1000, description="Number of questions to fetch (max 1000)")
    days_back: int = Field(365, ge=1, le=3650, description="Look back this many days (max 10 years)")
    tags: Optional[List[str]] = Field(["sql"], description="Tags to filter by")
    min_score: int = Field(1, ge=0, description="Minimum score for questions")
    only_accepted_answers: bool = Field(True, description="Only fetch questions with accepted answers")
    start_page: int = Field(1, ge=1, description="Start from this API page (for continuation)")


class ScrapeJobStatus(BaseModel):
    """Status of a scraping job"""
    job_id: str
    status: str  # running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    progress: Dict[str, Any]
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScrapeJobResult(BaseModel):
    """Result of completed scraping job"""
    questions_fetched: int
    questions_stored: int
    questions_skipped: int
    answers_fetched: int
    answers_stored: int
    answers_skipped: int
    errors: int
    started_at: str
    completed_at: str


class ScrapeStats(BaseModel):
    """Statistics about scraped data"""
    total_questions: int
    total_answers: int
    accepted_answers: int
    recent_questions_7d: int
    avg_question_score: float
    avg_answer_score: float
    top_tags: List[Dict[str, Any]]
    database_url: str


class QuestionListItem(BaseModel):
    """List view of a Stackoverflow question"""
    id: int
    stack_overflow_id: int
    title: str
    tags: List[str]
    score: int
    view_count: int
    is_answered: bool
    answer_count: int
    creation_date: datetime
    owner_display_name: Optional[str] = None


class PaginatedQuestionsResponse(BaseModel):
    """Paginated response for questions list"""
    items: List[QuestionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class BatchQueryRequest(BaseModel):
    """Request to start batch query processing"""
    question_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of StackOverflow question IDs to process (max 50)"
    )
    session_id: str = Field(..., description="Session identifier")
    collection_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of collection IDs to use for retrieval. If not provided, uses StackOverflow retriever."
    )
    graph_types: Optional[List[GraphType]] = Field(
        default=[GraphType.ADAPTIVE_RAG],
        description="List of graph types to use for processing. Each question will be processed with each graph type."
    )
    llm_config: Optional[Dict[str, Any]] = Field(
        default={},
        description="Optional LLM configuration overrides"
    )
    include_graph_trace: bool = Field(
        default=True,
        description="Include graph execution trace in results"
    )


class BertScoreResult(BaseModel):
    """BERT Score evaluation results"""
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    model_type: Optional[str] = None  # e.g., "bert-base-uncased"


class BatchQueryResult(BaseModel):
    """Result for a single question in batch"""
    question_id: int
    question_title: str
    question_body: Optional[str] = None  # NEU: Vollständiger Fragentext
    stack_overflow_id: Optional[int] = None  # NEU: Für Link zu SO
    graph_type: str = Field(default="adaptive_rag", description="Graph type used for this evaluation")
    status: str  # success, failed, skipped
    generated_answer: Optional[str] = None
    reference_answer: Optional[str] = None
    bert_score: Optional[BertScoreResult] = None
    graph_trace: Optional[List[str]] = None
    iteration_metrics: Optional[IterationMetrics] = None
    node_timings: Optional[Dict[str, float]] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    evaluation_id: Optional[int] = None
    completed_at: Optional[str] = None


class BatchQueryProgress(BaseModel):
    """Progress tracking for batch job"""
    total_questions: int
    processed: int
    successful: int
    failed: int
    skipped: int
    current_question_id: Optional[int] = None
    current_question_title: Optional[str] = None


class BatchQueryJobStatus(BaseModel):
    """Complete batch job status"""
    job_id: str
    status: str  # running, completed, failed, cancelled
    started_at: str
    completed_at: Optional[str] = None
    progress: BatchQueryProgress
    parameters: Dict[str, Any]
    results: List[BatchQueryResult]
    error: Optional[str] = None


class BatchQueryStartResponse(BaseModel):
    """Response when starting batch query"""
    job_id: str
    message: str
    total_questions: int

class QuestionCollectionInfo(BaseModel):
    """Collection membership info for a question"""
    collection_id: int
    collection_name: str
    collection_type: str
    added_at: str


class QuestionWithCollections(BaseModel):
    """Question with collection membership info"""
    id: int
    stack_overflow_id: int
    title: str
    tags: List[str]
    score: int
    view_count: int
    is_answered: bool
    creation_date: datetime
    collections: List[QuestionCollectionInfo] = Field(
        default_factory=list,
        description="Collections this question belongs to"
    )