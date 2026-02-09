"""
Export service for scientific data exports of RAG experiment results.

Provides export functionality in CSV, JSON, and LaTeX formats
for use in scientific papers and data analysis.
"""

import logging
import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas.export_schemas import (
    ExportFilterRequest,
    ExportFormat,
    ExportType,
    ExportMetadata,
    ExportQuestion,
    ExportEvaluation,
    ExportBertScores,
    ExportIterationMetrics,
    ExportRetrievedDocument,
    FullExportData,
    GraphTypeStatistics,
    StatisticsExportData,
    QuestionComparison,
    ComparisonExportData,
    GraphTypeMetrics,
)
from app.database import SOQuestion, SOAnswer, GraphExecution, RetrievedDocument, CollectionConfiguration
from app.evaluation.models import AnswerEvaluation

logger = logging.getLogger(__name__)


class ExportService:
    """Export service for scientific data exports"""

    def __init__(self, db: Session):
        self.db = db


    def fetch_full_export_data(
        self,
        filters: Optional[ExportFilterRequest],
        include_retrieved_documents: bool = True,
        include_full_answers: bool = True,
        include_node_timings: bool = True,
        progress_callback: Optional[callable] = None
    ) -> FullExportData:
        """
        Fetch all data like in comparison view.

        Args:
            filters: Optional filters to apply
            include_retrieved_documents: Include document details
            include_full_answers: Include full answer texts
            include_node_timings: Include per-node timing data
            progress_callback: Optional callback for progress updates

        Returns:
            FullExportData with all questions and evaluations
        """
        logger.info("Fetching full export data")

        query = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.stackoverflow_question_id.isnot(None),
            AnswerEvaluation.reference_answer.isnot(None),
            AnswerEvaluation.reference_answer != "",
        )

        query = self._apply_evaluation_filters(query, filters)

        evaluations = query.order_by(
            AnswerEvaluation.stackoverflow_question_id,
            AnswerEvaluation.graph_type,
            AnswerEvaluation.created_at.desc()
        ).all()

        if filters and filters.deduplicate_latest_only:
            evaluations = self._deduplicate_evaluations(evaluations)

        total_evaluations = len(evaluations)
        logger.info(f"Found {total_evaluations} evaluations to export")

        if progress_callback:
            progress_callback({
                "phase": "fetching",
                "processed": 0,
                "total": total_evaluations
            })

        evaluations_by_question: Dict[int, List[AnswerEvaluation]] = defaultdict(list)
        for eval in evaluations:
            evaluations_by_question[eval.stackoverflow_question_id].append(eval)

        question_ids = list(evaluations_by_question.keys())
        questions_dict = {}
        if question_ids:
            questions = self.db.query(SOQuestion).filter(
                SOQuestion.stack_overflow_id.in_(question_ids)
            ).all()
            questions_dict = {q.stack_overflow_id: q for q in questions}

        accepted_answers = self._get_accepted_answers(question_ids)

        export_questions = []
        processed = 0

        for question_id, evals in evaluations_by_question.items():
            question = questions_dict.get(question_id)
            if not question:
                continue

            tags = question.tags.split(',') if question.tags else []
            tags = [t.strip() for t in tags if t.strip()]

            reference_answer = None
            if question_id in accepted_answers:
                reference_answer = accepted_answers[question_id].body if include_full_answers else "[omitted]"

            export_evals = []
            for eval in evals:
                export_eval = self._build_export_evaluation(
                    eval,
                    include_retrieved_documents=include_retrieved_documents,
                    include_full_answers=include_full_answers,
                    include_node_timings=include_node_timings
                )
                export_evals.append(export_eval)
                processed += 1

                if progress_callback and processed % 10 == 0:
                    progress_callback({
                        "phase": "processing",
                        "processed": processed,
                        "total": total_evaluations
                    })

            export_question = ExportQuestion(
                question_id=question_id,
                title=question.title,
                body=question.body if include_full_answers else None,
                tags=tags,
                score=question.score,
                reference_answer=reference_answer,
                evaluations=export_evals
            )
            export_questions.append(export_question)

        metadata = ExportMetadata(
            export_date=datetime.utcnow().isoformat() + "Z",
            export_type=ExportType.FULL,
            format=ExportFormat.JSON,
            total_questions=len(export_questions),
            total_evaluations=sum(len(q.evaluations) for q in export_questions),
            filters_applied=filters.model_dump() if filters else None
        )

        if progress_callback:
            progress_callback({
                "phase": "completed",
                "processed": total_evaluations,
                "total": total_evaluations
            })

        return FullExportData(
            export_metadata=metadata,
            questions=export_questions
        )

    def fetch_statistics(
        self,
        filters: Optional[ExportFilterRequest],
        group_by: List[str],
        include_ci: bool = True,
        include_std: bool = True,
        progress_callback: Optional[callable] = None
    ) -> StatisticsExportData:
        """
        Fetch aggregated statistics with mean, std, and confidence intervals.

        Args:
            filters: Optional filters to apply
            group_by: Fields to group by (supports 'graph_type', 'llm_model', 'embedding_model')
            include_ci: Include 95% confidence intervals
            include_std: Include standard deviation
            progress_callback: Optional callback for progress updates

        Returns:
            StatisticsExportData with aggregated statistics
        """
        logger.info(f"Fetching statistics grouped by {group_by}")

        if progress_callback:
            progress_callback({"phase": "fetching", "processed": 0, "total": 100})

        query = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.stackoverflow_question_id.isnot(None),
            AnswerEvaluation.reference_answer.isnot(None),
            AnswerEvaluation.reference_answer != "",
        )

        query = self._apply_evaluation_filters(query, filters)

        evaluations = query.all()

        if filters and filters.deduplicate_latest_only:
            evaluations = self._deduplicate_evaluations(evaluations)

        if progress_callback:
            progress_callback({"phase": "processing", "processed": 30, "total": 100})

        embedding_model_cache: Dict[int, Optional[str]] = {}
        if 'embedding_model' in group_by:
            for eval in evaluations:
                if eval.id not in embedding_model_cache:
                    embedding_model_cache[eval.id] = eval.embedding_model or self._get_embedding_model_for_evaluation(eval.id)

        if progress_callback:
            progress_callback({"phase": "processing", "processed": 50, "total": 100})

        grouped: Dict[tuple, List[AnswerEvaluation]] = defaultdict(list)
        for eval in evaluations:
            key_parts = []
            for field in group_by:
                if field == 'graph_type':
                    key_parts.append(('graph_type', eval.graph_type or "adaptive_rag"))
                elif field == 'llm_model':
                    key_parts.append(('llm_model', eval.llm_model or "unknown"))
                elif field == 'embedding_model':
                    emb_model = embedding_model_cache.get(eval.id, None) or "unknown"
                    key_parts.append(('embedding_model', emb_model))
            grouped[tuple(key_parts)].append(eval)

        statistics = []
        for group_key, evals in sorted(grouped.items()):
            group_dict = dict(group_key)
            graph_type = group_dict.get('graph_type', 'all')
            llm_model = group_dict.get('llm_model')
            embedding_model = group_dict.get('embedding_model')

            stats = self._calculate_group_statistics(
                graph_type, evals, include_ci, include_std,
                llm_model=llm_model, embedding_model=embedding_model
            )
            statistics.append(stats)

        if filters:
            for stat in statistics:
                if filters.llm_model and not stat.llm_model:
                    stat.llm_model = filters.llm_model
                if filters.embedding_model and not stat.embedding_model:
                    stat.embedding_model = filters.embedding_model

        if progress_callback:
            progress_callback({"phase": "completed", "processed": 100, "total": 100})

        metadata = ExportMetadata(
            export_date=datetime.utcnow().isoformat() + "Z",
            export_type=ExportType.STATISTICS,
            format=ExportFormat.LATEX,
            total_questions=len(set(e.stackoverflow_question_id for e in evaluations)),
            total_evaluations=len(evaluations),
            filters_applied=filters.model_dump() if filters else None
        )

        return StatisticsExportData(
            export_metadata=metadata,
            statistics=statistics
        )

    def fetch_comparison_table(
        self,
        filters: Optional[ExportFilterRequest],
        baseline_graph_type: str,
        metric: str,
        progress_callback: Optional[callable] = None
    ) -> ComparisonExportData:
        """
        Fetch side-by-side comparison with improvement calculation.
        Includes all metrics (BERT + LLM Correctness) in a nested structure.

        Args:
            filters: Optional filters to apply
            baseline_graph_type: Baseline for improvement calculation
            metric: Primary metric for best_graph_type and improvement calculation
            progress_callback: Optional callback for progress updates

        Returns:
            ComparisonExportData with per-question comparisons including all metrics
        """
        logger.info(f"Fetching comparison table with baseline {baseline_graph_type}")

        if progress_callback:
            progress_callback({"phase": "fetching", "processed": 0, "total": 100})

        query = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.stackoverflow_question_id.isnot(None),
            AnswerEvaluation.reference_answer.isnot(None),
            AnswerEvaluation.reference_answer != "",
        )

        query = self._apply_evaluation_filters(query, filters)

        evaluations = query.all()

        if filters and filters.deduplicate_latest_only:
            evaluations = self._deduplicate_evaluations(evaluations)

        if progress_callback:
            progress_callback({"phase": "processing", "processed": 30, "total": 100})

        by_question: Dict[int, Dict[str, Dict[str, List[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        question_titles: Dict[int, str] = {}

        for eval in evaluations:
            qid = eval.stackoverflow_question_id
            graph_type = eval.graph_type or "adaptive_rag"

            if eval.bert_f1 is not None:
                by_question[qid][graph_type]["bert_f1"].append(eval.bert_f1)
            if eval.bert_precision is not None:
                by_question[qid][graph_type]["bert_precision"].append(eval.bert_precision)
            if eval.bert_recall is not None:
                by_question[qid][graph_type]["bert_recall"].append(eval.bert_recall)
            if eval.llm_correctness_score is not None:
                by_question[qid][graph_type]["llm_correctness"].append(eval.llm_correctness_score)

            if qid not in question_titles:
                question = self.db.query(SOQuestion).filter(
                    SOQuestion.stack_overflow_id == qid
                ).first()
                if question:
                    question_titles[qid] = question.title

        if progress_callback:
            progress_callback({"phase": "processing", "processed": 60, "total": 100})

        def avg(values: List[float]) -> Optional[float]:
            return sum(values) / len(values) if values else None

        comparisons = []
        for qid, metrics_by_type in sorted(by_question.items()):
            avg_metrics: Dict[str, GraphTypeMetrics] = {}
            for graph_type, metric_values in metrics_by_type.items():
                avg_metrics[graph_type] = GraphTypeMetrics(
                    bert_f1=avg(metric_values.get("bert_f1", [])),
                    bert_precision=avg(metric_values.get("bert_precision", [])),
                    bert_recall=avg(metric_values.get("bert_recall", [])),
                    llm_correctness=avg(metric_values.get("llm_correctness", []))
                )

            best_type = ""
            if avg_metrics:
                best_val = None
                for graph_type, metrics_obj in avg_metrics.items():
                    if metric == "bert_f1":
                        val = metrics_obj.bert_f1
                    elif metric == "bert_precision":
                        val = metrics_obj.bert_precision
                    elif metric == "bert_recall":
                        val = metrics_obj.bert_recall
                    elif metric == "llm_correctness":
                        val = metrics_obj.llm_correctness
                    else:
                        val = metrics_obj.bert_f1

                    if val is not None and (best_val is None or val > best_val):
                        best_val = val
                        best_type = graph_type

            improvement = None
            if baseline_graph_type in avg_metrics and best_type in avg_metrics:
                baseline_metrics = avg_metrics[baseline_graph_type]
                best_metrics = avg_metrics[best_type]

                if metric == "bert_f1":
                    baseline_val = baseline_metrics.bert_f1
                    best_val = best_metrics.bert_f1
                elif metric == "bert_precision":
                    baseline_val = baseline_metrics.bert_precision
                    best_val = best_metrics.bert_precision
                elif metric == "bert_recall":
                    baseline_val = baseline_metrics.bert_recall
                    best_val = best_metrics.bert_recall
                elif metric == "llm_correctness":
                    baseline_val = baseline_metrics.llm_correctness
                    best_val = best_metrics.llm_correctness
                else:
                    baseline_val = baseline_metrics.bert_f1
                    best_val = best_metrics.bert_f1

                if baseline_val is not None and best_val is not None and baseline_val > 0:
                    improvement = ((best_val - baseline_val) / baseline_val) * 100

            comparison = QuestionComparison(
                question_id=qid,
                title=question_titles.get(qid, f"Question {qid}"),
                metrics_by_graph_type=avg_metrics,
                best_graph_type=best_type,
                improvement_vs_baseline=improvement
            )
            comparisons.append(comparison)

        if progress_callback:
            progress_callback({"phase": "completed", "processed": 100, "total": 100})

        metadata = ExportMetadata(
            export_date=datetime.utcnow().isoformat() + "Z",
            export_type=ExportType.COMPARISON,
            format=ExportFormat.LATEX,
            total_questions=len(comparisons),
            total_evaluations=len(evaluations),
            filters_applied=filters.model_dump() if filters else None
        )

        return ComparisonExportData(
            export_metadata=metadata,
            baseline_graph_type=baseline_graph_type,
            metric=metric,
            comparisons=comparisons
        )


    def to_csv(self, data: FullExportData) -> str:
        """
        Convert full export data to flat CSV format.

        Args:
            data: FullExportData to convert

        Returns:
            CSV string
        """
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        headers = [
            "question_id", "question_title", "tags", "score", "graph_type",
            "evaluation_id", "generated_answer", "reference_answer",
            "bert_f1", "bert_precision", "bert_recall",
            "processing_time_ms", "manual_rating", "rewritten_question",
            "graph_trace", "generation_attempts", "transform_attempts",
            "total_iterations", "max_iterations_reached",
            "retrieved_doc_count", "created_at",
            "llm_correctness_score", "llm_correctness_model",
            "llm_model", "embedding_model"
        ]
        writer.writerow(headers)

        for question in data.questions:
            for eval in question.evaluations:
                trace_str = "→".join(eval.graph_trace) if eval.graph_trace else ""

                gen_attempts = eval.iteration_metrics.generation_attempts if eval.iteration_metrics else 0
                transform_attempts = eval.iteration_metrics.transform_attempts if eval.iteration_metrics else 0
                total_iter = eval.iteration_metrics.total_iterations if eval.iteration_metrics else 0
                max_reached = eval.iteration_metrics.max_iterations_reached if eval.iteration_metrics else False

                row = [
                    question.question_id,
                    question.title,
                    ",".join(question.tags),
                    "" if question.score is None else question.score,
                    eval.graph_type,
                    eval.evaluation_id,
                    eval.generated_answer or "",
                    question.reference_answer or "",
                    "" if eval.bert_scores.f1 is None else eval.bert_scores.f1,
                    "" if eval.bert_scores.precision is None else eval.bert_scores.precision,
                    "" if eval.bert_scores.recall is None else eval.bert_scores.recall,
                    "" if eval.processing_time_ms is None else eval.processing_time_ms,
                    "" if eval.manual_rating is None else eval.manual_rating,
                    eval.rewritten_question or "",
                    trace_str,
                    gen_attempts,
                    transform_attempts,
                    total_iter,
                    max_reached,
                    len(eval.retrieved_documents) if eval.retrieved_documents else 0,
                    eval.created_at,
                    "" if eval.llm_correctness_score is None else eval.llm_correctness_score,
                    eval.llm_correctness_model or "",
                    eval.llm_model or "",
                    eval.embedding_model or ""
                ]
                writer.writerow(row)

        return output.getvalue()

    def to_json(self, data: FullExportData) -> str:
        """
        Convert full export data to JSON format.

        Args:
            data: FullExportData to convert

        Returns:
            JSON string
        """
        return data.model_dump_json(indent=2)

    def statistics_to_csv(self, data: StatisticsExportData) -> str:
        """Convert statistics to CSV format."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        headers = [
            "graph_type", "llm_model", "embedding_model", "n",
            "bert_f1_mean", "bert_f1_std",
            "bert_f1_ci_lower", "bert_f1_ci_upper",
            "bert_precision_mean", "bert_recall_mean",
            "processing_time_ms_mean", "processing_time_ms_std",
            "llm_correctness_mean", "llm_correctness_std"
        ]
        writer.writerow(headers)

        for stats in data.statistics:
            row = [
                stats.graph_type,
                stats.llm_model or "",
                stats.embedding_model or "",
                stats.n,
                f"{stats.bert_f1_mean:.4f}" if stats.bert_f1_mean else "",
                f"{stats.bert_f1_std:.4f}" if stats.bert_f1_std else "",
                f"{stats.bert_f1_ci_lower:.4f}" if stats.bert_f1_ci_lower else "",
                f"{stats.bert_f1_ci_upper:.4f}" if stats.bert_f1_ci_upper else "",
                f"{stats.bert_precision_mean:.4f}" if stats.bert_precision_mean else "",
                f"{stats.bert_recall_mean:.4f}" if stats.bert_recall_mean else "",
                f"{stats.processing_time_ms_mean:.1f}" if stats.processing_time_ms_mean else "",
                f"{stats.processing_time_ms_std:.1f}" if stats.processing_time_ms_std else "",
                f"{stats.llm_correctness_mean:.4f}" if stats.llm_correctness_mean else "",
                f"{stats.llm_correctness_std:.4f}" if stats.llm_correctness_std else ""
            ]
            writer.writerow(row)

        return output.getvalue()

    def statistics_to_json(self, data: StatisticsExportData) -> str:
        """Convert statistics to JSON format."""
        return data.model_dump_json(indent=2)

    def to_latex_statistics(self, data: StatisticsExportData, caption: str = "RAG System Performance Comparison") -> str:
        """
        Convert statistics to LaTeX table with booktabs styling.

        Args:
            data: StatisticsExportData to convert
            caption: Table caption

        Returns:
            LaTeX table string
        """
        n_total = sum(s.n for s in data.statistics)

        has_llm_model = any(s.llm_model for s in data.statistics)
        has_embedding_model = any(s.embedding_model for s in data.statistics)

        col_spec = "l"
        if has_llm_model:
            col_spec += "l"
        if has_embedding_model:
            col_spec += "l"
        col_spec += "ccccccc"

        header_parts = [r"\textbf{Graph Type}"]
        if has_llm_model:
            header_parts.append(r"\textbf{LLM Model}")
        if has_embedding_model:
            header_parts.append(r"\textbf{Embedding}")
        header_parts.extend([
            r"\textbf{n}",
            r"\textbf{BERT-F1}",
            r"\textbf{95\% CI}",
            r"\textbf{Precision}",
            r"\textbf{Recall}",
            r"\textbf{LLM Corr.}",
            r"\textbf{Time (ms)}"
        ])

        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            f"\\caption{{{caption} (n={n_total} evaluations)}}",
            r"\label{tab:rag-comparison}",
            f"\\begin{{tabular}}{{{col_spec}}}",
            r"\toprule",
            " & ".join(header_parts) + r" \\",
            r"\midrule"
        ]

        for stats in data.statistics:
            name = stats.graph_type.replace("_", " ").title()

            if stats.bert_f1_mean is not None and stats.bert_f1_std is not None:
                f1_str = f"${stats.bert_f1_mean:.3f} \\pm {stats.bert_f1_std:.2f}$"
            elif stats.bert_f1_mean is not None:
                f1_str = f"${stats.bert_f1_mean:.3f}$"
            else:
                f1_str = "--"

            if stats.bert_f1_ci_lower is not None and stats.bert_f1_ci_upper is not None:
                ci_str = f"[{stats.bert_f1_ci_lower:.2f}, {stats.bert_f1_ci_upper:.2f}]"
            else:
                ci_str = "--"

            prec_str = f"{stats.bert_precision_mean:.3f}" if stats.bert_precision_mean else "--"
            rec_str = f"{stats.bert_recall_mean:.3f}" if stats.bert_recall_mean else "--"
            llm_corr_str = f"{stats.llm_correctness_mean:.3f}" if stats.llm_correctness_mean else "--"
            time_str = f"{stats.processing_time_ms_mean:.0f}" if stats.processing_time_ms_mean else "--"

            row_parts = [name]
            if has_llm_model:
                llm_model_str = stats.llm_model.replace("_", "\\_") if stats.llm_model else "--"
                row_parts.append(llm_model_str)
            if has_embedding_model:
                emb_model_str = stats.embedding_model.replace("_", "\\_") if stats.embedding_model else "--"
                row_parts.append(emb_model_str)
            row_parts.extend([str(stats.n), f1_str, ci_str, prec_str, rec_str, llm_corr_str, time_str])

            line = " & ".join(row_parts) + r" \\"
            lines.append(line)

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}"
        ])

        return "\n".join(lines)

    def comparison_to_csv(self, data: ComparisonExportData) -> str:
        """Convert comparison to CSV format with all metrics per graph type."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        all_graph_types = set()
        for comp in data.comparisons:
            all_graph_types.update(comp.metrics_by_graph_type.keys())
        graph_types = sorted(all_graph_types)

        metric_names = ["bert_f1", "bert_precision", "bert_recall", "llm_correctness"]

        headers = ["question_id", "title"]
        for gt in graph_types:
            for metric_name in metric_names:
                headers.append(f"{gt}_{metric_name}")
        headers.extend(["best", "improvement_pct"])
        writer.writerow(headers)

        for comp in data.comparisons:
            row = [comp.question_id, comp.title]
            for gt in graph_types:
                metrics = comp.metrics_by_graph_type.get(gt)
                if metrics:
                    row.append(f"{metrics.bert_f1:.4f}" if metrics.bert_f1 is not None else "")
                    row.append(f"{metrics.bert_precision:.4f}" if metrics.bert_precision is not None else "")
                    row.append(f"{metrics.bert_recall:.4f}" if metrics.bert_recall is not None else "")
                    row.append(f"{metrics.llm_correctness:.4f}" if metrics.llm_correctness is not None else "")
                else:
                    row.extend(["", "", "", ""])
            row.append(comp.best_graph_type)
            row.append(f"{comp.improvement_vs_baseline:.1f}" if comp.improvement_vs_baseline is not None else "")
            writer.writerow(row)

        return output.getvalue()

    def comparison_to_json(self, data: ComparisonExportData) -> str:
        """Convert comparison to JSON format."""
        return data.model_dump_json(indent=2)

    def to_latex_comparison(
        self,
        data: ComparisonExportData,
        caption: str = "Per-Question Performance Comparison",
        max_rows: int = 20
    ) -> str:
        """
        Convert comparison to LaTeX table with all metrics per graph type.

        Args:
            data: ComparisonExportData to convert
            caption: Table caption
            max_rows: Maximum rows to include (for paper-friendly size)

        Returns:
            LaTeX table string
        """
        all_graph_types = set()
        for comp in data.comparisons:
            all_graph_types.update(comp.metrics_by_graph_type.keys())
        graph_types = sorted(all_graph_types)

        metric_abbrevs = ["F1", "P", "R", "LLM"]

        num_metric_cols = len(graph_types) * 4
        col_spec = "l" + "c" * num_metric_cols + "c"

        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\small",
            f"\\caption{{{caption} (primary metric: {data.metric.replace('_', ' ')})}}",
            r"\label{tab:per-question}",
            f"\\begin{{tabular}}{{{col_spec}}}",
            r"\toprule"
        ]

        header1_parts = [r"\textbf{Question}"]
        for gt in graph_types:
            header1_parts.append(f"\\multicolumn{{4}}{{c}}{{\\textbf{{{gt.replace('_', ' ').title()}}}}}")
        header1_parts.append(r"\textbf{$\Delta$}")
        lines.append(" & ".join(header1_parts) + r" \\")

        header2_parts = [""]
        for _ in graph_types:
            header2_parts.extend(metric_abbrevs)
        header2_parts.append("")
        lines.append(" & ".join(header2_parts) + r" \\")
        lines.append(r"\midrule")

        for comp in data.comparisons[:max_rows]:
            title = comp.title[:25] + "..." if len(comp.title) > 25 else comp.title
            title = title.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")

            parts = [f"Q{comp.question_id}"]
            for gt in graph_types:
                metrics = comp.metrics_by_graph_type.get(gt)
                if metrics:
                    parts.append(f"{metrics.bert_f1:.2f}" if metrics.bert_f1 is not None else "--")
                    parts.append(f"{metrics.bert_precision:.2f}" if metrics.bert_precision is not None else "--")
                    parts.append(f"{metrics.bert_recall:.2f}" if metrics.bert_recall is not None else "--")
                    parts.append(f"{metrics.llm_correctness:.2f}" if metrics.llm_correctness is not None else "--")
                else:
                    parts.extend(["--", "--", "--", "--"])

            if comp.improvement_vs_baseline is not None:
                sign = "+" if comp.improvement_vs_baseline >= 0 else ""
                parts.append(f"{sign}{comp.improvement_vs_baseline:.1f}\\%")
            else:
                parts.append("--")

            lines.append(" & ".join(parts) + r" \\")

        if len(data.comparisons) > max_rows:
            total_cols = 1 + num_metric_cols + 1
            lines.append(f"\\multicolumn{{{total_cols}}}{{c}}{{... and {len(data.comparisons) - max_rows} more questions}} \\\\")

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}"
        ])

        return "\n".join(lines)


    def _deduplicate_evaluations(self, evaluations: List[AnswerEvaluation]) -> List[AnswerEvaluation]:
        """Keep only the newest evaluation per (question, llm_model, embedding_model, graph_type, llm_correctness_model)."""
        seen = {}
        for eval in evaluations:
            key = (
                eval.stackoverflow_question_id,
                eval.llm_model,
                eval.embedding_model or self._get_embedding_model_for_evaluation(eval.id),
                eval.graph_type,
                eval.llm_correctness_model,
            )
            if key not in seen or eval.created_at > seen[key].created_at:
                seen[key] = eval
        return list(seen.values())

    def _get_embedding_model_for_evaluation(self, evaluation_id: int) -> Optional[str]:
        """Get embedding model: prefer direct column, fall back to JOIN through retrieved documents."""
        direct = self.db.query(AnswerEvaluation.embedding_model).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()
        if direct and direct[0]:
            return direct[0]

        result = (
            self.db.query(CollectionConfiguration.embedding_model)
            .join(RetrievedDocument,
                  RetrievedDocument.collection_name == CollectionConfiguration.name)
            .filter(RetrievedDocument.evaluation_id == evaluation_id)
            .first()
        )
        return result[0] if result else None

    def _apply_evaluation_filters(
        self,
        query,
        filters: Optional[ExportFilterRequest]
    ):
        """Apply filters to evaluation query."""
        if not filters:
            return query

        if filters.start_date:
            query = query.filter(AnswerEvaluation.created_at >= filters.start_date)

        if filters.end_date:
            query = query.filter(AnswerEvaluation.created_at <= filters.end_date)

        if filters.graph_types:
            query = query.filter(AnswerEvaluation.graph_type.in_(filters.graph_types))

        if filters.question_ids:
            query = query.filter(
                AnswerEvaluation.stackoverflow_question_id.in_(filters.question_ids)
            )

        if filters.min_bert_f1 is not None:
            query = query.filter(AnswerEvaluation.bert_f1 >= filters.min_bert_f1)

        if filters.llm_model:
            query = query.filter(AnswerEvaluation.llm_model == filters.llm_model)

        if filters.embedding_model:
            subquery = (
                self.db.query(RetrievedDocument.evaluation_id)
                .join(CollectionConfiguration,
                      RetrievedDocument.collection_name == CollectionConfiguration.name)
                .filter(CollectionConfiguration.embedding_model == filters.embedding_model)
                .distinct()
                .subquery()
            )
            query = query.filter(
                (AnswerEvaluation.embedding_model == filters.embedding_model) |
                (AnswerEvaluation.embedding_model.is_(None) & AnswerEvaluation.id.in_(subquery))
            )

        if filters.tags:
            query = query.join(
                SOQuestion,
                SOQuestion.stack_overflow_id == AnswerEvaluation.stackoverflow_question_id
            )

            for tag in filters.tags:
                query = query.filter(
                    func.lower(SOQuestion.tags).contains(tag.lower())
                )

        return query

    def _get_accepted_answers(self, question_ids: List[int]) -> Dict[int, SOAnswer]:
        """Get accepted answers for questions."""
        if not question_ids:
            return {}

        answers = self.db.query(SOAnswer).filter(
            SOAnswer.question_stack_overflow_id.in_(question_ids),
            SOAnswer.is_accepted == True
        ).all()

        return {a.question_stack_overflow_id: a for a in answers}

    def _build_export_evaluation(
        self,
        eval: AnswerEvaluation,
        include_retrieved_documents: bool,
        include_full_answers: bool,
        include_node_timings: bool
    ) -> ExportEvaluation:
        """Build ExportEvaluation from database model."""
        graph_trace = None
        node_timings = None
        rewritten_question = None

        if eval.graph_execution_id:
            graph_exec = self.db.query(GraphExecution).filter(
                GraphExecution.id == eval.graph_execution_id
            ).first()
            if graph_exec:
                graph_trace = graph_exec.execution_path
                if include_node_timings:
                    node_timings = graph_exec.node_timings
        elif eval.session_id:
            graph_exec = self.db.query(GraphExecution).filter(
                GraphExecution.session_id == eval.session_id
            ).order_by(GraphExecution.started_at.desc()).first()
            if graph_exec:
                graph_trace = graph_exec.execution_path
                if include_node_timings:
                    node_timings = graph_exec.node_timings

        iteration_metrics = None
        if eval.model_config:
            config = eval.model_config
            iteration_metrics = ExportIterationMetrics(
                generation_attempts=config.get("generation_attempts", 0),
                transform_attempts=config.get("transform_attempts", 0),
                total_iterations=config.get("total_iterations", 0),
                max_iterations_reached=config.get("max_iterations_reached", False)
            )

        retrieved_docs = None
        if include_retrieved_documents:
            docs = self.db.query(RetrievedDocument).filter(
                RetrievedDocument.evaluation_id == eval.id
            ).all()
            if docs:
                retrieved_docs = [
                    ExportRetrievedDocument(
                        source=doc.source,
                        title=doc.title,
                        content_preview=doc.content_preview[:200] if doc.content_preview else None,
                        relevance_score=doc.relevance_score,
                        collection_name=doc.collection_name
                    )
                    for doc in docs
                ]

        embedding_model = eval.embedding_model or self._get_embedding_model_for_evaluation(eval.id)

        return ExportEvaluation(
            evaluation_id=eval.id,
            graph_type=eval.graph_type or "adaptive_rag",
            generated_answer=eval.generated_answer if include_full_answers else None,
            bert_scores=ExportBertScores(
                f1=eval.bert_f1,
                precision=eval.bert_precision,
                recall=eval.bert_recall
            ),
            processing_time_ms=eval.processing_time_ms,
            manual_rating=eval.manual_rating,
            rewritten_question=rewritten_question,
            graph_trace=graph_trace,
            node_timings=node_timings,
            iteration_metrics=iteration_metrics,
            retrieved_documents=retrieved_docs,
            created_at=eval.created_at.isoformat() if eval.created_at else "",
            llm_correctness_score=eval.llm_correctness_score,
            llm_correctness_model=eval.llm_correctness_model,
            llm_model=eval.llm_model,
            embedding_model=embedding_model
        )

    def _calculate_group_statistics(
        self,
        graph_type: str,
        evaluations: List[AnswerEvaluation],
        include_ci: bool,
        include_std: bool,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> GraphTypeStatistics:
        """Calculate statistics for a group of evaluations."""
        n = len(evaluations)

        f1_values = [e.bert_f1 for e in evaluations if e.bert_f1 is not None]
        prec_values = [e.bert_precision for e in evaluations if e.bert_precision is not None]
        rec_values = [e.bert_recall for e in evaluations if e.bert_recall is not None]
        time_values = [e.processing_time_ms for e in evaluations if e.processing_time_ms is not None]
        llm_corr_values = [e.llm_correctness_score for e in evaluations if e.llm_correctness_score is not None]

        f1_mean = sum(f1_values) / len(f1_values) if f1_values else None
        prec_mean = sum(prec_values) / len(prec_values) if prec_values else None
        rec_mean = sum(rec_values) / len(rec_values) if rec_values else None
        time_mean = sum(time_values) / len(time_values) if time_values else None
        llm_corr_mean = sum(llm_corr_values) / len(llm_corr_values) if llm_corr_values else None

        f1_std = None
        time_std = None
        llm_corr_std = None
        if include_std and f1_values and len(f1_values) > 1:
            f1_std = self._calculate_std(f1_values)
        if include_std and time_values and len(time_values) > 1:
            time_std = self._calculate_std(time_values)
        if include_std and llm_corr_values and len(llm_corr_values) > 1:
            llm_corr_std = self._calculate_std(llm_corr_values)

        ci_lower = None
        ci_upper = None
        if include_ci and f1_values and len(f1_values) > 1:
            ci_lower, ci_upper = self._calculate_confidence_interval(f1_values)

        return GraphTypeStatistics(
            graph_type=graph_type,
            n=n,
            bert_f1_mean=f1_mean,
            bert_f1_std=f1_std,
            bert_f1_ci_lower=ci_lower,
            bert_f1_ci_upper=ci_upper,
            bert_precision_mean=prec_mean,
            bert_recall_mean=rec_mean,
            processing_time_ms_mean=time_mean,
            processing_time_ms_std=time_std,
            llm_correctness_mean=llm_corr_mean,
            llm_correctness_std=llm_corr_std,
            llm_model=llm_model,
            embedding_model=embedding_model
        )

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _calculate_confidence_interval(
        self,
        values: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval using t-distribution.

        Args:
            values: List of values
            confidence: Confidence level (default 0.95)

        Returns:
            Tuple of (lower, upper) bounds
        """
        n = len(values)
        if n < 2:
            mean = values[0] if values else 0
            return (mean, mean)

        mean = sum(values) / n
        std = self._calculate_std(values)
        se = std / math.sqrt(n)

        if n > 30:
            t_value = 1.96
        else:
            t_values = {
                2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57,
                7: 2.45, 8: 2.37, 9: 2.31, 10: 2.26,
                15: 2.14, 20: 2.09, 25: 2.06, 30: 2.04
            }
            t_value = t_values.get(n, 2.0)

        margin = t_value * se
        return (mean - margin, mean + margin)

    def _get_metric_value(self, eval: AnswerEvaluation, metric: str) -> Optional[float]:
        """Get specific metric value from evaluation."""
        if metric == "bert_f1":
            return eval.bert_f1
        elif metric == "bert_precision":
            return eval.bert_precision
        elif metric == "bert_recall":
            return eval.bert_recall
        elif metric == "processing_time_ms":
            return float(eval.processing_time_ms) if eval.processing_time_ms else None
        return None

    def calculate_improvement(self, value: float, baseline: float) -> float:
        """Calculate percentage improvement over baseline."""
        if baseline == 0:
            return 0.0
        return ((value - baseline) / baseline) * 100


def get_export_service(db: Session) -> ExportService:
    """Get ExportService instance with database session."""
    return ExportService(db)
