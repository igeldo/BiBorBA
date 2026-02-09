import logging
from typing import Dict, Any
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.core.graph.utils import format_docs

logger = logging.getLogger(__name__)

def create_generator_node(model_manager, prompt_manager):
    """Create answer generator node"""

    def generate(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate answer with iteration tracking and temperature variation

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        logger.info("---GENERATE---")
        question = state["question"]
        original_question = state.get("original_question", question)
        documents = state["documents"]
        model_config = state.get("model_config", {})

        generation_attempts = state.get("generation_attempts", 0) + 1
        total_iterations = state.get("total_iterations", 0) + 1

        base_temperature = model_config.get("temperature", 0.0)
        if generation_attempts > 1 and settings.enable_retry_variation:
            retry_temp = base_temperature + ((generation_attempts - 1) * settings.retry_temperature_increment)
            retry_temp = min(retry_temp, 1.0)
            logger.info(f"Retry {generation_attempts}: Temperature {base_temperature} → {retry_temp}")
            model_config = {**model_config, "temperature": retry_temp}

        llm = model_manager.get_chat_model("chat", **model_config)
        prompt = prompt_manager.get_answer_generator_prompt()

        rag_chain = prompt | llm | StrOutputParser()

        generation = rag_chain.invoke({
            "context": format_docs(documents),
            "question": original_question
        })

        logger.info(f"Generation attempt {generation_attempts}/{settings.max_generation_retries}")
        logger.info(f"Generated answer of length: {len(generation)}")
        logger.info(f"Generated answer: {generation[0:100]}")

        return {
            "documents": documents,
            "question": question,
            "original_question": original_question,
            "generation": generation,
            "model_config": model_config,
            "collection_ids": state.get("collection_ids", []),
            "generation_attempts": generation_attempts,
            "transform_attempts": state.get("transform_attempts", 0),
            "total_iterations": total_iterations,
            "max_iterations_reached": False,
            "no_relevant_docs_fallback": False,
            "fallback_type": ""
        }

    return generate