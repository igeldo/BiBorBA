"""
Complete evaluation service combining BERT Score, LLM Correctness, and manual evaluation
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

from sqlalchemy.orm import Session

from app.config import get_current_llm_model, get_current_embedding_model
from app.database import SessionLocal
from app.dependencies import get_bert_evaluation_service, get_llm_correctness_service
from app.evaluation.models import AnswerEvaluation
from app.services.stackoverflow_connector import StackOverflowConnector

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for managing answer evaluations"""

    def __init__(self):
        self.bert_service = get_bert_evaluation_service()
        self.llm_correctness_service = get_llm_correctness_service()

    def _resolve_embedding_model(self, db: Session, collection_ids: Optional[List[int]] = None) -> str:
        """
        Resolve the embedding model used for this evaluation.

        Args:
            db: Database session
            collection_ids: Optional list of collection IDs used for retrieval

        Returns:
            Embedding model name
        """
        if collection_ids:
            from app.database import CollectionConfiguration
            result = db.query(CollectionConfiguration.embedding_model).filter(
                CollectionConfiguration.id == collection_ids[0]
            ).first()
            if result and result[0]:
                return result[0]

        return get_current_embedding_model()

    async def evaluate_generated_answer(
            self,
            session_id: str,
            question_text: str,
            generated_answer: str,
            reference_answer: Optional[str] = None,
            stackoverflow_question_id: Optional[int] = None,
            graph_type: Optional[str] = None,
            graph_execution_id: Optional[int] = None,
            model_config: Optional[Dict] = None,
            processing_time_ms: Optional[int] = None,
            collection_ids: Optional[List[int]] = None
    ) -> AnswerEvaluation:
        """
        Evaluate a generated answer and store in database

        Args:
            graph_execution_id: ID of the GraphExecution record for trace linking

        Returns:
            AnswerEvaluation: Complete evaluation record with BERT scores
                             (bert_* fields will be None if no reference answer)
        """
        db = SessionLocal()
        try:
            resolved_embedding_model = self._resolve_embedding_model(db, collection_ids)

            evaluation = AnswerEvaluation(
                session_id=session_id,
                question_text=question_text,
                stackoverflow_question_id=stackoverflow_question_id,
                generated_answer=generated_answer,
                reference_answer=reference_answer,
                graph_type=graph_type or "adaptive_rag",
                graph_execution_id=graph_execution_id,
                model_config=model_config or {},
                processing_time_ms=processing_time_ms,
                llm_model=get_current_llm_model(),
                embedding_model=resolved_embedding_model
            )

            if reference_answer and reference_answer.strip():
                bert_result = self.bert_service.evaluate_answer(generated_answer, reference_answer)

                if bert_result:
                    evaluation.bert_precision = bert_result.precision
                    evaluation.bert_recall = bert_result.recall
                    evaluation.bert_f1 = bert_result.f1
                    evaluation.bert_model_type = bert_result.model_type

                    logger.info(f"BERT Score computed: F1={bert_result.f1:.4f}")
                else:
                    logger.warning("BERT Score computation failed")

                llm_result = await self.llm_correctness_service.evaluate_correctness(
                    question=question_text,
                    generated_answer=generated_answer,
                    reference_answer=reference_answer
                )

                if llm_result:
                    evaluation.llm_correctness_score = llm_result.score
                    evaluation.llm_correctness_model = llm_result.model
                    logger.info(f"LLM Correctness computed: {llm_result.score:.4f}")
                else:
                    logger.warning("LLM Correctness computation failed")
            else:
                logger.info("No reference answer provided - skipping BERT and LLM evaluation")

            db.add(evaluation)
            db.commit()
            db.refresh(evaluation)

            logger.info(f"Answer evaluation created with ID: {evaluation.id}")
            return evaluation

        except Exception as e:
            logger.error(f"Error creating evaluation: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    def add_manual_evaluation(
            self,
            evaluation_id: int,
            rating: int,
            comment: Optional[str] = None,
            evaluator_name: Optional[str] = None
    ) -> bool:
        """
        Add manual evaluation to existing record

        Args:
            evaluation_id: ID of evaluation record
            rating: Rating from 1-5
            comment: Optional comment
            evaluator_name: Name of evaluator

        Returns:
            True if successful
        """
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        db = SessionLocal()
        try:
            evaluation = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.id == evaluation_id
            ).first()

            if not evaluation:
                logger.error(f"Evaluation {evaluation_id} not found")
                return False

            evaluation.manual_rating = rating
            evaluation.manual_comment = comment
            evaluation.evaluator_name = evaluator_name
            evaluation.evaluated_at = datetime.utcnow()

            db.commit()
            logger.info(f"Manual evaluation added: Rating {rating}/5")
            return True

        except Exception as e:
            logger.error(f"Error adding manual evaluation: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_evaluation(self, evaluation_id: int) -> Optional[Dict[str, Any]]:
        """Get evaluation record by ID"""
        db = SessionLocal()
        try:
            evaluation = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.id == evaluation_id
            ).first()

            if not evaluation:
                return None

            result = {
                "id": evaluation.id,
                "session_id": evaluation.session_id,
                "question_text": evaluation.question_text,
                "generated_answer": evaluation.generated_answer,
                "reference_answer": evaluation.reference_answer,
                "stackoverflow_question_id": evaluation.stackoverflow_question_id,

                "bert_scores": {
                    "precision": evaluation.bert_precision,
                    "recall": evaluation.bert_recall,
                    "f1": evaluation.bert_f1,
                    "model_type": evaluation.bert_model_type,
                    "interpretation": self.bert_service.get_score_interpretation(
                        evaluation.bert_f1) if evaluation.bert_f1 else None
                } if evaluation.bert_f1 else None,

                "llm_correctness": {
                    "score": evaluation.llm_correctness_score,
                    "model": evaluation.llm_correctness_model
                } if evaluation.llm_correctness_score is not None else None,

                "manual_evaluation": {
                    "rating": evaluation.manual_rating,
                    "comment": evaluation.manual_comment,
                    "evaluator_name": evaluation.evaluator_name,
                    "evaluated_at": evaluation.evaluated_at
                } if evaluation.manual_rating else None,

                "model_config": evaluation.model_config,
                "processing_time_ms": evaluation.processing_time_ms,
                "created_at": evaluation.created_at
            }

            return result

        except Exception as e:
            logger.error(f"Error getting evaluation: {e}")
            return None
        finally:
            db.close()

    def get_evaluations_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all evaluations for a session"""
        db = SessionLocal()
        try:
            evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.session_id == session_id
            ).order_by(AnswerEvaluation.created_at.desc()).all()

            results = []
            for eval in evaluations:
                result = self.get_evaluation(eval.id)
                if result:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting session evaluations: {e}")
            return []
        finally:
            db.close()

    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        db = SessionLocal()
        try:
            from sqlalchemy import func

            total_evaluations = db.query(AnswerEvaluation).count()
            bert_evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.bert_f1.isnot(None)
            ).count()
            llm_correctness_evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.llm_correctness_score.isnot(None)
            ).count()
            manual_evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.manual_rating.isnot(None)
            ).count()

            bert_stats = db.query(
                func.avg(AnswerEvaluation.bert_f1).label('avg_f1'),
                func.max(AnswerEvaluation.bert_f1).label('max_f1'),
                func.min(AnswerEvaluation.bert_f1).label('min_f1')
            ).filter(AnswerEvaluation.bert_f1.isnot(None)).first()

            llm_stats = db.query(
                func.avg(AnswerEvaluation.llm_correctness_score).label('avg_score'),
                func.max(AnswerEvaluation.llm_correctness_score).label('max_score'),
                func.min(AnswerEvaluation.llm_correctness_score).label('min_score')
            ).filter(AnswerEvaluation.llm_correctness_score.isnot(None)).first()

            manual_stats = db.query(
                func.avg(AnswerEvaluation.manual_rating).label('avg_rating'),
                func.count(AnswerEvaluation.manual_rating).label('count')
            ).filter(AnswerEvaluation.manual_rating.isnot(None)).first()

            rating_dist = db.query(
                AnswerEvaluation.manual_rating,
                func.count(AnswerEvaluation.manual_rating)
            ).filter(
                AnswerEvaluation.manual_rating.isnot(None)
            ).group_by(AnswerEvaluation.manual_rating).all()

            return {
                "total_evaluations": total_evaluations,
                "bert_evaluations": bert_evaluations,
                "llm_correctness_evaluations": llm_correctness_evaluations,
                "manual_evaluations": manual_evaluations,
                "bert_scores": {
                    "average_f1": round(bert_stats.avg_f1, 4) if bert_stats.avg_f1 else None,
                    "max_f1": round(bert_stats.max_f1, 4) if bert_stats.max_f1 else None,
                    "min_f1": round(bert_stats.min_f1, 4) if bert_stats.min_f1 else None
                } if bert_stats else None,
                "llm_correctness": {
                    "average_score": round(llm_stats.avg_score, 4) if llm_stats.avg_score else None,
                    "max_score": round(llm_stats.max_score, 4) if llm_stats.max_score else None,
                    "min_score": round(llm_stats.min_score, 4) if llm_stats.min_score else None
                } if llm_stats else None,
                "manual_ratings": {
                    "average_rating": round(manual_stats.avg_rating, 2) if manual_stats.avg_rating else None,
                    "total_rated": manual_stats.count if manual_stats else 0,
                    "distribution": {rating: count for rating, count in rating_dist}
                },
                "bert_available": self.bert_service.is_available(),
                "llm_correctness_available": self.llm_correctness_service.is_available()
            }

        except Exception as e:
            logger.error(f"Error getting evaluation statistics: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def evaluate_stackoverflow_answer_with_reference(
            self,
            question_id: int,
            generated_answer: str,
            session_id: str,
            model_config: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Evaluate generated answer against accepted StackOverflow answer

        Returns:
            evaluation_id if successful, None otherwise
        """
        db = SessionLocal()
        try:
            so_connector = StackOverflowConnector(db=db)

            question_data = so_connector.get_question_by_id(question_id)
            if not question_data:
                logger.error(f"StackOverflow question {question_id} not found")
                return None

            reference_answer = None
            answers = question_data.get('answers', [])

            if answers:
                accepted_answers = [a for a in answers if a.get('is_accepted', False)]
                if accepted_answers:
                    reference_answer = accepted_answers[0]['body']
                else:
                    best_answer = max(answers, key=lambda x: x.get('score', 0))
                    reference_answer = best_answer['body']

            evaluation = await self.evaluate_generated_answer(
                session_id=session_id,
                question_text=question_data['title'],
                generated_answer=generated_answer,
                reference_answer=reference_answer,
                stackoverflow_question_id=question_id,
                model_config=model_config
            )

            logger.info(f"StackOverflow answer evaluation created: {evaluation.id}")
            return evaluation.id

        except Exception as e:
            logger.error(f"Error evaluating StackOverflow answer: {e}")
            return None
        finally:
            db.close()

    async def backfill_llm_correctness(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        Backfill LLM correctness scores for existing evaluations that have
        a reference_answer but no llm_correctness_score.

        Args:
            batch_size: Number of evaluations to process per batch

        Returns:
            Dict with processing statistics
        """
        db = SessionLocal()
        try:
            pending = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.reference_answer.isnot(None),
                AnswerEvaluation.reference_answer != "",
                AnswerEvaluation.llm_correctness_score.is_(None)
            ).all()

            total = len(pending)
            if total == 0:
                logger.info("No evaluations need LLM correctness backfill")
                return {
                    "status": "complete",
                    "total_found": 0,
                    "processed": 0,
                    "succeeded": 0,
                    "failed": 0
                }

            logger.info(f"Starting LLM correctness backfill for {total} evaluations")

            succeeded = 0
            failed = 0

            for i, evaluation in enumerate(pending):
                try:
                    result = await self.llm_correctness_service.evaluate_correctness(
                        question=evaluation.question_text,
                        generated_answer=evaluation.generated_answer,
                        reference_answer=evaluation.reference_answer
                    )

                    if result:
                        evaluation.llm_correctness_score = result.score
                        evaluation.llm_correctness_model = result.model
                        db.commit()
                        succeeded += 1
                        logger.info(f"Backfilled evaluation {evaluation.id}: score={result.score:.4f}")
                    else:
                        failed += 1
                        logger.warning(f"Failed to compute LLM correctness for evaluation {evaluation.id}")

                except Exception as e:
                    failed += 1
                    logger.error(f"Error backfilling evaluation {evaluation.id}: {e}")
                    db.rollback()

                if (i + 1) % batch_size == 0:
                    logger.info(f"Backfill progress: {i + 1}/{total}")

            logger.info(f"LLM correctness backfill complete: {succeeded} succeeded, {failed} failed")

            return {
                "status": "complete",
                "total_found": total,
                "processed": succeeded + failed,
                "succeeded": succeeded,
                "failed": failed
            }

        except Exception as e:
            logger.error(f"Error during LLM correctness backfill: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            db.close()


