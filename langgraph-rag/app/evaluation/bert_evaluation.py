# app/evaluation/bert_evaluation.py
"""
BERT Score evaluation service for generated answers
"""
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

try:
    from bert_score import BERTScorer

    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    BERTScorer = None

logger = logging.getLogger(__name__)


@dataclass
class BERTScoreResult:
    """Container for BERT Score results"""
    precision: float
    recall: float
    f1: float
    model_type: str


class BERTEvaluationService:
    """Service for evaluating answers using BERT Score"""

    def __init__(self, model_type: str = "bert-base-uncased"):
        if not BERT_AVAILABLE:
            logger.error("BERT Score not available. Install with: pip install bert-score")
            self.scorer = None
            return

        self.model_type = model_type
        self.scorer = BERTScorer(model_type=model_type)
        logger.info(f"BERT Score evaluator initialized with model: {model_type}")

    def is_available(self) -> bool:
        """Check if BERT Score is available"""
        return BERT_AVAILABLE and self.scorer is not None

    def evaluate_answer(
            self,
            generated_answer: str,
            reference_answer: str
    ) -> Optional[BERTScoreResult]:
        """
        Evaluate generated answer against reference using BERT Score

        Args:
            generated_answer: The LLM-generated answer
            reference_answer: The reference/original answer

        Returns:
            BERTScoreResult or None if evaluation fails
        """
        if not self.is_available():
            logger.warning("BERT Score not available - skipping evaluation")
            return None

        if not generated_answer.strip() or not reference_answer.strip():
            logger.warning("Empty answer provided - skipping BERT evaluation")
            return None

        try:
            logger.info("Computing BERT Score...")

            # Compute BERT Score
            P, R, F1 = self.scorer.score([generated_answer], [reference_answer])

            result = BERTScoreResult(
                precision=float(P.mean()),
                recall=float(R.mean()),
                f1=float(F1.mean()),
                model_type=self.model_type
            )

            logger.info(f"BERT Score - P: {result.precision:.4f}, R: {result.recall:.4f}, F1: {result.f1:.4f}")
            return result

        except Exception as e:
            logger.error(f"BERT Score evaluation failed: {e}")
            return None

    def batch_evaluate(
            self,
            generated_answers: List[str],
            reference_answers: List[str]
    ) -> List[Optional[BERTScoreResult]]:
        """
        Batch evaluation of multiple answer pairs

        Args:
            generated_answers: List of generated answers
            reference_answers: List of reference answers

        Returns:
            List of BERTScoreResult or None for each pair
        """
        if not self.is_available():
            return [None] * len(generated_answers)

        if len(generated_answers) != len(reference_answers):
            raise ValueError("Generated and reference answer lists must have same length")

        results = []
        for gen_ans, ref_ans in zip(generated_answers, reference_answers):
            result = self.evaluate_answer(gen_ans, ref_ans)
            results.append(result)

        return results

    def get_score_interpretation(self, f1_score: float) -> str:
        """Get interpretation of F1 score"""
        if f1_score >= 0.9:
            return "Excellent"
        elif f1_score >= 0.8:
            return "Very Good"
        elif f1_score >= 0.7:
            return "Good"
        elif f1_score >= 0.6:
            return "Fair"
        elif f1_score >= 0.5:
            return "Poor"
        else:
            return "Very Poor"