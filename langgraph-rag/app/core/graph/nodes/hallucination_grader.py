from typing import Dict, Any
from pydantic import BaseModel, Field
import logging

from app.config import settings
from app.utils.timing import TimingContext
from app.core.graph.utils import format_docs

logger = logging.getLogger(__name__)


class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""
    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")


def create_hallucination_grader_node(model_manager, prompt_manager):
    """Create hallucination grader node with iterative batch checking"""

    def grade_hallucination(state: Dict[str, Any]) -> Dict[str, bool]:
        """
        Grade whether generation is grounded in documents using iterative batch checking.

        Checks documents in batches of settings.hallucination_batch_size.
        If any batch confirms grounding → answer is accepted.
        Only if ALL batches fail → answer is considered not grounded.

        This approach:
        - Reduces context per LLM call for better accuracy
        - Allows early exit on success (faster)
        - Ensures all documents get checked before regenerating
        """
        documents = state["documents"]
        generation = state["generation"]

        if not documents:
            logger.warning("No documents to check hallucination against")
            return {"is_grounded": False}

        with TimingContext("Get hallucination grader model", logger):
            llm = model_manager.get_structured_model("grader", GradeHallucinations, format="json")
            prompt = prompt_manager.get_hallucination_grader_prompt()
            grader = prompt | llm

        total_docs = len(documents)
        batch_num = 0

        for batch_start in range(0, total_docs, settings.hallucination_batch_size):
            batch_end = min(batch_start + settings.hallucination_batch_size, total_docs)
            doc_batch = documents[batch_start:batch_end]
            batch_num += 1

            if not doc_batch:
                continue

            formatted_batch = format_docs(doc_batch)

            logger.info(f"Hallucination check batch {batch_num}: docs {batch_start + 1}-{batch_end} of {total_docs}")

            with TimingContext(f"LLM call: Hallucination grading batch {batch_num}", logger):
                try:
                    score = grader.invoke({
                        "documents": formatted_batch,
                        "generation": generation
                    })
                except Exception as e:
                    logger.error(f"Hallucination grading batch {batch_num} failed: {e}")
                    continue

            logger.debug(f"Batch {batch_num} result: {score.binary_score}")

            if score.binary_score.lower() == "yes":
                logger.info(f"---GROUNDED IN BATCH {batch_num} (docs {batch_start + 1}-{batch_end})---")
                return {"is_grounded": True}

            logger.debug(f"Not grounded in batch {batch_num}, checking next batch...")

        logger.info(f"---NOT GROUNDED IN ANY OF {batch_num} BATCHES ({total_docs} documents)---")
        return {"is_grounded": False}

    return grade_hallucination