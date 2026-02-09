"""
LLM-as-Judge service for evaluating factual correctness of answers.
Uses a structured prompt to assess how well a generated answer matches
a reference answer on a scale of 1-5.
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.core.model_manager import ModelManager
from app.core.prompts import PromptManager

logger = logging.getLogger(__name__)


class CorrectnessGrade(BaseModel):
    """Structured output for correctness grading"""
    score: int = Field(
        description="Correctness score from 1-5. 1=completely wrong, 5=fully correct"
    )
    reasoning: str = Field(
        description="Brief explanation for the score"
    )


@dataclass
class LLMCorrectnessResult:
    """Result of LLM correctness evaluation"""
    score: float
    raw_score: int
    reasoning: str
    model: str


class LLMCorrectnessService:
    """Service for LLM-based correctness evaluation"""

    def __init__(self, model_manager: ModelManager, prompt_manager: PromptManager):
        self.model_manager = model_manager
        self.prompt_manager = prompt_manager

    async def evaluate_correctness(
            self,
            question: str,
            generated_answer: str,
            reference_answer: str
    ) -> Optional[LLMCorrectnessResult]:
        """
        Evaluate the factual correctness of a generated answer.

        Args:
            question: The original question
            generated_answer: The answer to evaluate
            reference_answer: The ground truth reference answer

        Returns:
            LLMCorrectnessResult with normalized score (0.0-1.0), or None on failure
        """
        if not reference_answer or not reference_answer.strip():
            logger.warning("No reference answer provided for LLM correctness evaluation")
            return None

        if not generated_answer or not generated_answer.strip():
            logger.warning("No generated answer provided for LLM correctness evaluation")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                model = self.model_manager.get_structured_model(
                    "evaluation", CorrectnessGrade, temperature=0.0
                )
                prompt = self.prompt_manager.get_correctness_evaluation_prompt()
                chain = prompt | model

                result: CorrectnessGrade = await chain.ainvoke({
                    "question": question,
                    "reference_answer": reference_answer,
                    "generated_answer": generated_answer
                })

                raw_score = max(1, min(5, result.score))

                normalized_score = (raw_score - 1) / 4.0

                logger.info(
                    f"LLM Correctness: {raw_score}/5 ({normalized_score:.2f}) - {result.reasoning[:100]}..."
                )

                return LLMCorrectnessResult(
                    score=normalized_score,
                    raw_score=raw_score,
                    reasoning=result.reasoning,
                    model=self.get_model_name()
                )

            except RuntimeError as e:
                error_msg = str(e).lower()
                is_tcp_error = "tcptransport" in error_msg and "closed" in error_msg

                if is_tcp_error and attempt < max_retries - 1:
                    logger.warning(f"TCPTransport error, retry {attempt + 1}/{max_retries}")
                    self.model_manager.reset_chat_model("evaluation")
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    logger.error(f"LLM Correctness evaluation failed: {e}")
                    return None

            except Exception as e:
                logger.error(f"LLM Correctness evaluation failed: {e}")
                return None

        return None

    def get_model_name(self) -> str:
        """Get the configured evaluation model name"""
        return self.model_manager.list_available_models().get("evaluation", "unknown")

    def is_available(self) -> bool:
        """Check if the evaluation model is available"""
        try:
            self.model_manager.get_structured_model(
                "evaluation", CorrectnessGrade, temperature=0.0
            )
            return True
        except Exception as e:
            logger.error(f"LLM Correctness service not available: {e}")
            return False
