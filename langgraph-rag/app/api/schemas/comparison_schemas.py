"""
Schemas for graph type comparison endpoints
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AcceptedAnswerInfo(BaseModel):
    """Akzeptierte StackOverflow-Antwort"""
    stack_overflow_id: int
    body: str
    score: int
    owner_display_name: Optional[str] = None
    creation_date: Optional[datetime] = None


class RetrievedDocumentSchema(BaseModel):
    """Schema for retrieved documents in comparison view"""
    id: Optional[int] = None
    source: str
    title: Optional[str] = None
    content_preview: str
    full_content: Optional[str] = None
    relevance_score: Optional[float] = None
    collection_name: Optional[str] = None
    metadata: Optional[Dict] = None


class IterationMetricsSchema(BaseModel):
    """Schema for iteration metrics"""
    generation_attempts: int = 0
    transform_attempts: int = 0
    total_iterations: int = 0
    max_iterations_reached: bool = False
    no_relevant_docs_fallback: bool = False
    disclaimer: Optional[str] = None


class EvaluationWithGraphType(BaseModel):
    """Evaluation mit Graph-Type Information"""
    id: int
    graph_type: str
    generated_answer: str
    bert_precision: Optional[float] = None
    bert_recall: Optional[float] = None
    bert_f1: Optional[float] = None
    processing_time_ms: Optional[int] = None
    manual_rating: Optional[int] = None
    created_at: datetime
    graph_trace: Optional[List[str]] = None
    node_timings: Optional[Dict[str, float]] = None
    rewritten_question: Optional[str] = None
    retrieved_documents: Optional[List[RetrievedDocumentSchema]] = None
    iteration_metrics: Optional[IterationMetricsSchema] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    llm_correctness_score: Optional[float] = None
    llm_correctness_model: Optional[str] = None


class GraphComparisonResponse(BaseModel):
    """Vergleich aller Evaluations für eine SO-Frage"""
    question_id: int
    question_title: str
    question_body: str
    accepted_answer: Optional[AcceptedAnswerInfo] = None
    evaluations_by_graph_type: Dict[str, List[EvaluationWithGraphType]]


class ComparisonMetricsSummary(BaseModel):
    """Aggregierte Metriken für Vergleichstabelle"""
    graph_type: str
    avg_bert_f1: Optional[float] = None
    avg_bert_precision: Optional[float] = None
    avg_bert_recall: Optional[float] = None
    avg_processing_time_ms: Optional[float] = None
    avg_llm_correctness: Optional[float] = None
    evaluation_count: int
    latest_evaluation_date: Optional[datetime] = None


class EvaluatedQuestionListItem(BaseModel):
    """Liste evaluierter Fragen"""
    question_id: int
    question_title: str
    available_graph_types: List[str]
    total_evaluations: int
    has_multiple_graph_types: bool
    tags: Optional[List[str]] = None
    score: Optional[int] = None


class PaginatedEvaluatedQuestionsResponse(BaseModel):
    """Paginierte Liste evaluierter Fragen"""
    items: List[EvaluatedQuestionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool



class RerunRequest(BaseModel):
    """Request to rerun evaluation for a question with different graph types/collections"""
    graph_types: List[str] = Field(
        ...,
        min_length=1,
        description="Graph types to use: adaptive_rag, simple_rag, pure_llm"
    )
    collection_ids: Optional[List[int]] = Field(
        default=None,
        description="Collection IDs for retrieval. If not provided, uses StackOverflow retriever."
    )
    session_id: str = Field(..., description="Session identifier for the rerun")


class RerunResponse(BaseModel):
    """Response when starting a rerun job"""
    job_id: str
    message: str
    total_runs: int
    question_id: int
    question_title: str



class ConfigurationStatistics(BaseModel):
    """Statistics for a single configuration (graph_type + optional LLM + optional embedding)"""
    graph_type: str
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    n: int
    bert_f1_mean: Optional[float] = None
    bert_f1_std: Optional[float] = None
    llm_correctness_mean: Optional[float] = None
    llm_correctness_std: Optional[float] = None
    processing_time_ms_mean: Optional[float] = None


class AggregatedStatisticsResponse(BaseModel):
    """Response for aggregated statistics endpoint"""
    statistics: List[ConfigurationStatistics]
    total_evaluations: int
    group_by: List[str]



class ArchitectureMetrics(BaseModel):
    """Average metrics for a single architecture"""
    avg_bert_f1: Optional[float] = None
    avg_llm_correctness: Optional[float] = None


class MetricsByArchitecture(BaseModel):
    """Average metrics grouped by architecture"""
    adaptive_rag: Optional[ArchitectureMetrics] = None
    simple_rag: Optional[ArchitectureMetrics] = None
    pure_llm: Optional[ArchitectureMetrics] = None


class EvaluatedQuestionListItemExtended(BaseModel):
    """Extended version of EvaluatedQuestionListItem with average metrics per architecture"""
    question_id: int
    question_title: str
    available_graph_types: List[str]
    total_evaluations: int
    has_multiple_graph_types: bool
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    metrics_by_architecture: Optional[MetricsByArchitecture] = None


class PaginatedEvaluatedQuestionsExtendedResponse(BaseModel):
    """Paginierte Liste evaluierter Fragen mit erweiterten Metriken"""
    items: List[EvaluatedQuestionListItemExtended]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
