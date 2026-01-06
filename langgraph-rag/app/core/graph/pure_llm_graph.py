# core/graph/pure_llm_graph.py
"""
Pure LLM Graph - Direct question-answering without retrieval

This graph serves as a baseline for comparing RAG approaches.
It directly asks the LLM to answer questions without any document retrieval.
"""
import logging
from typing import Dict, Any

from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.core.graph.utils import GraphState
from app.core.model_manager import get_model_manager
from app.core.prompts import get_prompt_manager
from app.utils.timing import TimingContext

logger = logging.getLogger(__name__)


def create_pure_llm_graph() -> CompiledStateGraph:
    """
    Create and compile the Pure LLM graph.

    This is a simple baseline implementation that directly answers questions
    using an LLM without any retrieval or RAG components.

    Flow:
        START → generate → END

    Returns:
        CompiledStateGraph: The compiled graph ready for execution
    """
    model_manager = get_model_manager()
    prompt_manager = get_prompt_manager()

    def pure_llm_generate(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate answer directly from LLM without document context

        Args:
            state (dict): The current graph state containing question and config

        Returns:
            state (dict): Updated state with generated answer
        """
        logger.info("---PURE LLM GENERATE---")
        question = state["question"]
        model_config = state.get("model_config", {})

        generation_attempts = 1
        total_iterations = 1

        with TimingContext("Get chat model and pure LLM prompt", logger):
            llm = model_manager.get_chat_model("chat", **model_config)
            prompt = prompt_manager.get_pure_llm_prompt()

        llm_chain = prompt | llm | StrOutputParser()

        with TimingContext("LLM call: Generate answer (pure LLM - no RAG)", logger):
            generation = llm_chain.invoke({
                "question": question
            })

        logger.info(f"Generated answer of length: {len(generation)}")
        logger.info(f"Generated answer: {generation[0:100]}...")

        return {
            "question": question,
            "generation": generation,
            "documents": [],  # No documents in pure LLM mode
            "model_config": model_config,
            "generation_attempts": generation_attempts,
            "transform_attempts": 0,  # No query transformation
            "total_iterations": total_iterations,
            "max_iterations_reached": False
        }

    workflow = StateGraph(GraphState)

    workflow.add_node("generate", pure_llm_generate)

    workflow.add_edge(START, "generate")
    workflow.add_edge("generate", END)

    logger.info("Pure LLM graph compiled successfully")
    return workflow.compile()


create_llm_graph = create_pure_llm_graph
