# services/batch_query_service.py
"""
Service for batch processing of StackOverflow questions
"""

import logging
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from app.api.schemas.schemas import RetrieverType, GraphType
from app.dependencies import get_graph_service, get_evaluation_service
from app.services.stackoverflow_connector import StackOverflowConnector
from app.database import SessionLocal, RetrievedDocument

logger = logging.getLogger(__name__)


class BatchQueryService:
    """Service for processing batches of StackOverflow questions"""

    def __init__(self):
        self.graph_service = get_graph_service()
        self._db_session = SessionLocal()
        self.so_connector = StackOverflowConnector(db=self._db_session)
        self.evaluation_service = get_evaluation_service()

    def close(self):
        """Close the database session"""
        if self._db_session:
            self._db_session.close()
            self._db_session = None

    def process_batch_sync(
        self,
        job_id: str,
        question_ids: List[int],
        session_id: str,
        collection_ids: Optional[List[int]] = None,
        graph_types: Optional[List[GraphType]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of questions sequentially (synchronous wrapper)

        This method runs in a thread pool to avoid blocking the FastAPI event loop.
        It creates its own event loop to run the async operations.

        Args:
            job_id: Unique job identifier
            question_ids: List of SO question IDs to process
            session_id: Session identifier
            collection_ids: Optional list of collection IDs to use for retrieval
            graph_types: Optional list of graph types to use (default: [ADAPTIVE_RAG])
            llm_config: Optional LLM configuration
            progress_callback: Callback for progress updates

        Returns:
            Dictionary with batch results
        """
        import asyncio
        # Run the async version in a new event loop (for thread pool execution)
        return asyncio.run(self._process_batch_async(
            job_id=job_id,
            question_ids=question_ids,
            session_id=session_id,
            collection_ids=collection_ids,
            graph_types=graph_types,
            llm_config=llm_config,
            progress_callback=progress_callback
        ))

    async def _process_batch_async(
        self,
        job_id: str,
        question_ids: List[int],
        session_id: str,
        collection_ids: Optional[List[int]] = None,
        graph_types: Optional[List[GraphType]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Internal async implementation of batch processing

        Args:
            job_id: Unique job identifier
            question_ids: List of SO question IDs to process
            session_id: Session identifier
            collection_ids: Optional list of collection IDs to use for retrieval
            graph_types: Optional list of graph types to use (default: [ADAPTIVE_RAG])
            llm_config: Optional LLM configuration
            progress_callback: Callback for progress updates

        Returns:
            Dictionary with batch results
        """
        db = SessionLocal()
        results = []

        # Default to ADAPTIVE_RAG if not specified
        if graph_types is None or len(graph_types) == 0:
            graph_types = [GraphType.ADAPTIVE_RAG]

        # Total number of processing runs = questions × graph_types
        total_runs = len(question_ids) * len(graph_types)
        processed_count = 0

        try:
            for question_id in question_ids:
                for graph_type in graph_types:
                    try:
                        # Update progress - processing question with specific graph type
                        if progress_callback:
                            # Get question title for display
                            question_data = self.so_connector.get_question_by_id(question_id)
                            progress_callback({
                                "processed": processed_count,
                                "current_question_id": question_id,
                                "current_question_title": f"{question_data.get('title', 'Unknown') if question_data else 'Unknown'} ({graph_type.value})"
                            })

                        # Process single question with specific graph type
                        result = await self._process_single_question(
                            question_id=question_id,
                            session_id=session_id,
                            collection_ids=collection_ids,
                            graph_type=graph_type,
                            llm_config=llm_config,
                            db=db
                        )

                        results.append(result)
                        processed_count += 1

                        # Update progress and send result for incremental display
                        if progress_callback:
                            progress_callback({
                                "processed": processed_count,
                                "successful": sum(1 for r in results if r["status"] == "success"),
                                "failed": sum(1 for r in results if r["status"] == "failed"),
                                "skipped": sum(1 for r in results if r["status"] == "skipped"),
                                "current_question_id": None,
                                "current_question_title": None,
                                "result": result  # Send completed result immediately
                            })

                    except Exception as e:
                        logger.error(f"Failed to process question {question_id} with graph_type {graph_type.value}: {e}")
                        failed_result = {
                            "question_id": question_id,
                            "question_title": "Unknown",
                            "graph_type": graph_type.value,
                            "status": "failed",
                            "error_message": str(e),
                            "completed_at": datetime.utcnow().isoformat()
                        }
                        results.append(failed_result)
                        processed_count += 1

                        # Update progress and send failed result for incremental display
                        if progress_callback:
                            progress_callback({
                                "processed": processed_count,
                                "successful": sum(1 for r in results if r["status"] == "success"),
                                "failed": sum(1 for r in results if r["status"] == "failed"),
                                "skipped": sum(1 for r in results if r["status"] == "skipped"),
                                "result": failed_result  # Send failed result immediately
                            })

            return {
                "status": "completed",
                "results": results,
                "summary": {
                    "total": total_runs,
                    "successful": sum(1 for r in results if r["status"] == "success"),
                    "failed": sum(1 for r in results if r["status"] == "failed"),
                    "skipped": sum(1 for r in results if r["status"] == "skipped")
                }
            }

        finally:
            db.close()

    async def _process_single_question(
        self,
        question_id: int,
        session_id: str,
        collection_ids: Optional[List[int]],
        graph_type: GraphType,
        llm_config: Optional[Dict[str, Any]],
        db
    ) -> Dict[str, Any]:
        """Process a single question with graph execution and BERT evaluation

        Args:
            question_id: Internal database ID of the question
            session_id: Session identifier
            collection_ids: Optional list of collection IDs to use for retrieval
            graph_type: Graph type to use for processing
            llm_config: Optional LLM configuration
            db: Database session

        Returns:
            Dictionary with processing result
        """

        start_time = time.time()

        # 1. Fetch question from database
        question_data = self.so_connector.get_question_by_id(question_id)
        if not question_data:
            return {
                "question_id": question_id,
                "question_title": "Unknown",
                "question_body": None,
                "stack_overflow_id": None,
                "graph_type": graph_type.value,
                "status": "skipped",
                "error_message": "Question not found in database",
                "completed_at": datetime.utcnow().isoformat()
            }

        question_text = question_data["title"]
        question_body = question_data.get("body", "")
        full_question = f"{question_text}\n\n{question_body}" if question_body else question_text

        # 2. Execute graph to generate answer (MOVED UP - happens FIRST)
        try:
            # Pure LLM: No retrieval, just direct LLM call
            if graph_type == GraphType.PURE_LLM:
                logger.info(f"Using Pure LLM (no retrieval) for question {question_id}")
                graph_result = await self.graph_service.execute_query(
                    question=full_question,
                    session_id=f"{session_id}_batch_{question_id}_{graph_type.value}",
                    graph_type=graph_type,
                    model_config=llm_config
                )
            # RAG modes (Simple RAG or Adaptive RAG): Graph handles retrieval
            else:
                # Graph will retrieve documents from collections or use standard retriever
                if collection_ids:
                    logger.info(f"Using {len(collection_ids)} collections with {graph_type.value} (Graph handles retrieval)")
                else:
                    logger.info(f"Using StackOverflow retriever with {graph_type.value} (Graph handles retrieval)")

                graph_result = await self.graph_service.execute_query(
                    question=full_question,
                    session_id=f"{session_id}_batch_{question_id}_{graph_type.value}",
                    graph_type=graph_type,
                    retriever_type=RetrieverType.STACKOVERFLOW,
                    collection_ids=collection_ids,
                    model_config=llm_config
                )

            generated_answer = graph_result.get("answer", "")
            graph_trace = graph_result.get("graph_trace", [])
            retrieved_documents = graph_result.get("retrieved_documents", [])
            node_timings = graph_result.get("node_timings", {})
            rewritten_question = graph_result.get("rewritten_question")
            iteration_metrics = graph_result.get("iteration_metrics", {})
            graph_execution_id = graph_result.get("graph_execution_id")

        except Exception as e:
            logger.error(f"Graph execution failed for question {question_id}: {e}")
            return {
                "question_id": question_id,
                "question_title": question_text,
                "question_body": question_body,
                "stack_overflow_id": question_data.get("stack_overflow_id"),
                "graph_type": graph_type.value,
                "status": "failed",
                "error_message": f"Graph execution failed: {str(e)}",
                "completed_at": datetime.utcnow().isoformat()
            }

        # 3. OPTIONAL: Try to get reference answer for BERT-Score (AFTER generation)
        reference_answer = self._get_reference_answer(question_data)
        bert_score = None
        evaluation_id = None

        if reference_answer:
            # We have a reference answer - can do BERT evaluation
            try:
                logger.info(f"Reference answer available for question {question_id} - computing BERT score")
                evaluation_result = self.evaluation_service.evaluate_generated_answer(
                    question_text=full_question,
                    generated_answer=generated_answer,
                    reference_answer=reference_answer,
                    session_id=f"{session_id}_batch_{question_id}_{graph_type.value}",
                    stackoverflow_question_id=question_data["stack_overflow_id"],
                    graph_type=graph_type.value,
                    graph_execution_id=graph_execution_id,
                    model_config=llm_config,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )

                bert_score = {
                    "precision": evaluation_result.bert_precision,
                    "recall": evaluation_result.bert_recall,
                    "f1": evaluation_result.bert_f1,
                    "model_type": evaluation_result.bert_model_type
                } if (evaluation_result.bert_precision is not None and
                      evaluation_result.bert_recall is not None and
                      evaluation_result.bert_f1 is not None) else None

                evaluation_id = evaluation_result.id
                logger.info(f"BERT score computed for question {question_id}: F1={bert_score['f1'] if bert_score else 'N/A'}")

                # Save retrieved documents for comparison view
                if evaluation_id and retrieved_documents:
                    self._save_retrieved_documents(db, evaluation_id, retrieved_documents)

            except Exception as e:
                logger.error(f"BERT evaluation failed for question {question_id}: {e}", exc_info=True)
                bert_score = None
                evaluation_id = None
        else:
            # No reference answer - skip BERT evaluation but keep generated answer
            logger.info(f"No reference answer for question {question_id} - skipping BERT evaluation (answer still generated)")

        # 4. Return result (with or without BERT score)
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "question_id": question_id,
            "question_title": question_text,
            "question_body": question_body,
            "stack_overflow_id": question_data.get("stack_overflow_id"),
            "graph_type": graph_type.value,
            "status": "success",  # Always "success" if generation worked
            "generated_answer": generated_answer,
            "reference_answer": reference_answer,  # May be None
            "bert_score": bert_score,  # May be None
            "graph_trace": graph_trace,
            "node_timings": node_timings,
            "rewritten_question": rewritten_question,
            "iteration_metrics": iteration_metrics,
            "retrieved_documents": retrieved_documents,
            "processing_time_ms": processing_time,
            "evaluation_id": evaluation_id,  # May be None
            "completed_at": datetime.utcnow().isoformat()
        }

    def _get_reference_answer(self, question_data: Dict) -> Optional[str]:
        """
        Get reference answer for BERT-Score comparison.
        Uses accepted answer if available, otherwise highest-scored answer.
        """
        answers = question_data.get("answers", [])
        if not answers:
            return None

        # Try accepted answer first
        accepted = next(
            (a for a in answers if a.get("is_accepted")),
            None
        )
        if accepted:
            return accepted["body"]

        # Fallback to highest-scored answer
        sorted_answers = sorted(
            answers,
            key=lambda a: a.get("score", 0),
            reverse=True
        )
        return sorted_answers[0]["body"] if sorted_answers else None

    def _save_retrieved_documents(
        self,
        db,
        evaluation_id: int,
        documents: List[Dict[str, Any]]
    ) -> None:
        """
        Save retrieved documents to database for comparison view display.

        Args:
            db: Database session
            evaluation_id: ID of the associated evaluation
            documents: List of document dictionaries from graph execution
        """
        try:
            for doc in documents:
                retrieved_doc = RetrievedDocument(
                    evaluation_id=evaluation_id,
                    source=doc.get("source", "unknown"),
                    title=doc.get("title"),
                    content_preview=doc.get("content_preview"),
                    full_content=doc.get("full_content"),
                    relevance_score=doc.get("relevance_score"),
                    collection_name=doc.get("metadata", {}).get("collection_name"),
                    document_metadata=doc.get("metadata")
                )
                db.add(retrieved_doc)

            db.commit()
            logger.info(f"Saved {len(documents)} retrieved documents for evaluation {evaluation_id}")

        except Exception as e:
            logger.error(f"Failed to save retrieved documents for evaluation {evaluation_id}: {e}")
            db.rollback()


