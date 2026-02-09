"""
Schemas for export endpoints - scientific data export for RAG experiments
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ExportFormat(str, Enum):
    """Supported export formats"""
    CSV = "csv"
    JSON = "json"
    LATEX = "latex"


class ExportType(str, Enum):
    """Types of export"""
    FULL = "full"
    STATISTICS = "statistics"
    COMPARISON = "comparison"


class ExportFilterRequest(BaseModel):
    """Filter options for export queries"""
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter evaluations from this date onwards"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter evaluations until this date"
    )
    graph_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by graph types: adaptive_rag, simple_rag, pure_llm"
    )
    question_ids: Optional[List[int]] = Field(
        default=None,
        description="Filter by specific question IDs"
    )
    min_bert_f1: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum BERT-F1 score filter"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Filter by StackOverflow tags"
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Filter by LLM model used (e.g., 'gemma3:12b', 'gemma3:4b')"
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="Filter by embedding model used (via collection)"
    )
    deduplicate_latest_only: bool = Field(
        default=False,
        description="Nur die neueste Evaluation pro (Frage, LLM, Embedding, Graph-Typ, LLM-Evaluator) Kombination"
    )


class FullExportRequest(BaseModel):
    """Request for full export - equivalent to comparison view"""
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Export format: csv, json, or latex"
    )
    filters: Optional[ExportFilterRequest] = Field(
        default=None,
        description="Optional filters to apply"
    )
    include_retrieved_documents: bool = Field(
        default=True,
        description="Include retrieved document details"
    )
    include_full_answers: bool = Field(
        default=True,
        description="Include full answer texts (can be large)"
    )
    include_node_timings: bool = Field(
        default=True,
        description="Include per-node timing information"
    )


class StatisticsExportRequest(BaseModel):
    """Request for aggregated statistics export"""
    format: ExportFormat = Field(
        default=ExportFormat.LATEX,
        description="Export format: csv, json, or latex"
    )
    filters: Optional[ExportFilterRequest] = Field(
        default=None,
        description="Optional filters to apply"
    )
    group_by: List[str] = Field(
        default=["graph_type"],
        description="Fields to group by"
    )
    include_confidence_intervals: bool = Field(
        default=True,
        description="Include 95% confidence intervals"
    )
    include_std: bool = Field(
        default=True,
        description="Include standard deviation"
    )


class ComparisonExportRequest(BaseModel):
    """Request for side-by-side comparison export"""
    format: ExportFormat = Field(
        default=ExportFormat.LATEX,
        description="Export format: csv, json, or latex"
    )
    filters: Optional[ExportFilterRequest] = Field(
        default=None,
        description="Optional filters to apply"
    )
    baseline_graph_type: str = Field(
        default="pure_llm",
        description="Baseline graph type for improvement calculation"
    )
    metric: str = Field(
        default="bert_f1",
        description="Primary metric for comparison: bert_f1, bert_precision, bert_recall, llm_correctness"
    )



class ExportProgress(BaseModel):
    """Progress information for export job"""
    phase: str = Field(description="Current phase: fetching, processing, formatting")
    processed: int = Field(default=0, description="Number of records processed")
    total: int = Field(default=0, description="Total records to process")
    percent: float = Field(default=0.0, description="Completion percentage")


class ExportJobStartResponse(BaseModel):
    """Response when starting an export job"""
    job_id: str
    message: str
    export_type: ExportType
    format: ExportFormat


class ExportJobStatus(BaseModel):
    """Status of an export job"""
    job_id: str
    status: str
    export_type: ExportType
    format: ExportFormat
    progress: ExportProgress
    started_at: str
    completed_at: Optional[str] = None
    file_size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)



class ExportBertScores(BaseModel):
    """BERT score metrics"""
    f1: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None


class ExportIterationMetrics(BaseModel):
    """Iteration metrics from graph execution"""
    generation_attempts: int = 0
    transform_attempts: int = 0
    total_iterations: int = 0
    max_iterations_reached: bool = False


class ExportRetrievedDocument(BaseModel):
    """Retrieved document information"""
    source: str
    title: Optional[str] = None
    content_preview: Optional[str] = None
    relevance_score: Optional[float] = None
    collection_name: Optional[str] = None


class ExportEvaluation(BaseModel):
    """Single evaluation data for export"""
    evaluation_id: int
    graph_type: str
    generated_answer: Optional[str] = None
    bert_scores: ExportBertScores
    processing_time_ms: Optional[int] = None
    manual_rating: Optional[int] = None
    rewritten_question: Optional[str] = None
    graph_trace: Optional[List[str]] = None
    node_timings: Optional[Dict[str, float]] = None
    iteration_metrics: Optional[ExportIterationMetrics] = None
    retrieved_documents: Optional[List[ExportRetrievedDocument]] = None
    created_at: str
    llm_correctness_score: Optional[float] = None
    llm_correctness_model: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None


class ExportQuestion(BaseModel):
    """Question with all evaluations for export"""
    question_id: int
    title: str
    body: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    score: Optional[int] = None
    reference_answer: Optional[str] = None
    evaluations: List[ExportEvaluation] = Field(default_factory=list)


class ExportMetadata(BaseModel):
    """Metadata about the export"""
    export_date: str
    export_type: ExportType
    format: ExportFormat
    total_questions: int
    total_evaluations: int
    filters_applied: Optional[Dict[str, Any]] = None


class FullExportData(BaseModel):
    """Complete export data structure for JSON format"""
    export_metadata: ExportMetadata
    questions: List[ExportQuestion]



class GraphTypeStatistics(BaseModel):
    """Statistics for a single graph type (or grouping)"""
    graph_type: str
    n: int
    bert_f1_mean: Optional[float] = None
    bert_f1_std: Optional[float] = None
    bert_f1_ci_lower: Optional[float] = None
    bert_f1_ci_upper: Optional[float] = None
    bert_precision_mean: Optional[float] = None
    bert_recall_mean: Optional[float] = None
    processing_time_ms_mean: Optional[float] = None
    processing_time_ms_std: Optional[float] = None
    llm_correctness_mean: Optional[float] = None
    llm_correctness_std: Optional[float] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None


class StatisticsExportData(BaseModel):
    """Statistics export data structure"""
    export_metadata: ExportMetadata
    statistics: List[GraphTypeStatistics]



class GraphTypeMetrics(BaseModel):
    """All metrics for a single graph type"""
    bert_f1: Optional[float] = None
    bert_precision: Optional[float] = None
    bert_recall: Optional[float] = None
    llm_correctness: Optional[float] = None


class QuestionComparison(BaseModel):
    """Per-question comparison across graph types"""
    question_id: int
    title: str
    metrics_by_graph_type: Dict[str, GraphTypeMetrics]
    best_graph_type: str
    improvement_vs_baseline: Optional[float] = None


class ComparisonExportData(BaseModel):
    """Comparison export data structure"""
    export_metadata: ExportMetadata
    baseline_graph_type: str
    metric: str
    comparisons: List[QuestionComparison]
