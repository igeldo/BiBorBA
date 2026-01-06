# core/graph/nodes/rewriter.py
from typing import Dict, Any
import time
import logging

from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

from app.config import settings
from app.utils.timing import TimingContext


def create_rewriter_node(model_manager, prompt_manager):
    """Create question rewriter node"""

    def transform_query(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the query to produce a better question with iteration tracking

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """
        logger.info("---TRANSFORM QUERY---")
        question = state["question"]
        documents = state["documents"]
        model_config = state.get("model_config", {})

        transform_attempts = state.get("transform_attempts", 0) + 1
        total_iterations = state.get("total_iterations", 0) + 1

        with TimingContext("Get rewriter model and prompt", logger):
            llm = model_manager.get_chat_model("rewriter", **model_config)
            prompt = prompt_manager.get_question_rewriter_prompt()

        question_rewriter = prompt | llm | StrOutputParser()

        with TimingContext(f"LLM call: Rewrite query (attempt {transform_attempts})", logger):
            better_question = question_rewriter.invoke({"question": question})

        logger.info(f"Transform attempt {transform_attempts}/{settings.max_transform_retries}")
        logger.info(f"Original: {question}")
        logger.info(f"Rewritten: {better_question}")

        return {
            "documents": documents,
            "question": better_question,
            "original_question": state.get("original_question", state["question"]),  # Preserve original
            "generation": state.get("generation", ""),
            "model_config": model_config,
            "collection_ids": state.get("collection_ids", []),
            "generation_attempts": state.get("generation_attempts", 0),
            "transform_attempts": transform_attempts,
            "total_iterations": total_iterations,
            "max_iterations_reached": False,
            "no_relevant_docs_fallback": False,
            "fallback_type": ""
        }

    return transform_query