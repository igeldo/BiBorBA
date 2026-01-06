# app/evaluation/evaluation_service.py
"""
Complete evaluation service combining BERT Score and manual evaluation
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.dependencies import get_bert_evaluation_service
from app.evaluation.models import AnswerEvaluation
from app.evaluation.bert_evaluation import BERTScoreResult
from app.services.stackoverflow_connector import StackOverflowConnector

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for managing answer evaluations"""

    def __init__(self):
        self.bert_service = get_bert_evaluation_service()

    def evaluate_generated_answer(
            self,
            session_id: str,
            question_text: str,
            generated_answer: str,
            reference_answer: Optional[str] = None,
            stackoverflow_question_id: Optional[int] = None,
            graph_type: Optional[str] = None,
            graph_execution_id: Optional[int] = None,
            model_config: Optional[Dict] = None,
            processing_time_ms: Optional[int] = None
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
            # Create evaluation record
            evaluation = AnswerEvaluation(
                session_id=session_id,
                question_text=question_text,
                stackoverflow_question_id=stackoverflow_question_id,
                generated_answer=generated_answer,
                reference_answer=reference_answer,
                graph_type=graph_type or "adaptive_rag",
                graph_execution_id=graph_execution_id,
                model_config=model_config or {},
                processing_time_ms=processing_time_ms
            )

            # Compute BERT Score if reference answer available
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
            else:
                logger.info("No reference answer provided - skipping BERT evaluation")

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

                # BERT Score
                "bert_scores": {
                    "precision": evaluation.bert_precision,
                    "recall": evaluation.bert_recall,
                    "f1": evaluation.bert_f1,
                    "model_type": evaluation.bert_model_type,
                    "interpretation": self.bert_service.get_score_interpretation(
                        evaluation.bert_f1) if evaluation.bert_f1 else None
                } if evaluation.bert_f1 else None,

                # Manual evaluation
                "manual_evaluation": {
                    "rating": evaluation.manual_rating,
                    "comment": evaluation.manual_comment,
                    "evaluator_name": evaluation.evaluator_name,
                    "evaluated_at": evaluation.evaluated_at
                } if evaluation.manual_rating else None,

                # Metadata
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

            # Basic counts
            total_evaluations = db.query(AnswerEvaluation).count()
            bert_evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.bert_f1.isnot(None)
            ).count()
            manual_evaluations = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.manual_rating.isnot(None)
            ).count()

            # BERT Score statistics
            bert_stats = db.query(
                func.avg(AnswerEvaluation.bert_f1).label('avg_f1'),
                func.max(AnswerEvaluation.bert_f1).label('max_f1'),
                func.min(AnswerEvaluation.bert_f1).label('min_f1')
            ).filter(AnswerEvaluation.bert_f1.isnot(None)).first()

            # Manual rating statistics
            manual_stats = db.query(
                func.avg(AnswerEvaluation.manual_rating).label('avg_rating'),
                func.count(AnswerEvaluation.manual_rating).label('count')
            ).filter(AnswerEvaluation.manual_rating.isnot(None)).first()

            # Rating distribution
            rating_dist = db.query(
                AnswerEvaluation.manual_rating,
                func.count(AnswerEvaluation.manual_rating)
            ).filter(
                AnswerEvaluation.manual_rating.isnot(None)
            ).group_by(AnswerEvaluation.manual_rating).all()

            return {
                "total_evaluations": total_evaluations,
                "bert_evaluations": bert_evaluations,
                "manual_evaluations": manual_evaluations,
                "bert_scores": {
                    "average_f1": round(bert_stats.avg_f1, 4) if bert_stats.avg_f1 else None,
                    "max_f1": round(bert_stats.max_f1, 4) if bert_stats.max_f1 else None,
                    "min_f1": round(bert_stats.min_f1, 4) if bert_stats.min_f1 else None
                } if bert_stats else None,
                "manual_ratings": {
                    "average_rating": round(manual_stats.avg_rating, 2) if manual_stats.avg_rating else None,
                    "total_rated": manual_stats.count if manual_stats else 0,
                    "distribution": {rating: count for rating, count in rating_dist}
                },
                "bert_available": self.bert_service.is_available()
            }

        except Exception as e:
            logger.error(f"Error getting evaluation statistics: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def evaluate_stackoverflow_answer_with_reference(
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
            # Get StackOverflow question and answers
            so_connector = StackOverflowConnector(db=db)

            question_data = so_connector.get_question_by_id(question_id)
            if not question_data:
                logger.error(f"StackOverflow question {question_id} not found")
                return None

            # Find best reference answer (accepted or highest scored)
            reference_answer = None
            answers = question_data.get('answers', [])

            if answers:
                # Try accepted answer first
                accepted_answers = [a for a in answers if a.get('is_accepted', False)]
                if accepted_answers:
                    reference_answer = accepted_answers[0]['body']
                else:
                    # Use highest scored answer
                    best_answer = max(answers, key=lambda x: x.get('score', 0))
                    reference_answer = best_answer['body']

            # Create evaluation
            evaluation = self.evaluate_generated_answer(
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


