# core/graph/adaptive_graph.py
import logging
from typing import Dict, Any

from langgraph.graph import END, StateGraph, START
from langgraph.graph.state import CompiledStateGraph

from app.api.schemas.schemas import RetrieverType
from app.config import settings
from app.core.graph.nodes.answer_grader import create_answer_grader_node
from app.core.graph.nodes.document_grader import create_document_grader_node
from app.core.graph.nodes.generator import create_generator_node
from app.core.graph.nodes.hallucination_grader import create_hallucination_grader_node
from app.core.graph.nodes.retriever import create_retriever_node
from app.core.graph.nodes.rewriter import create_rewriter_node
from app.core.graph.utils import GraphState
from app.core.model_manager import get_model_manager
from app.core.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


def create_adaptive_graph(retriever_type: RetrieverType = RetrieverType.PDF) -> CompiledStateGraph:
    """Create and compile the adaptive RAG graph"""

    model_manager = get_model_manager()
    prompt_manager = get_prompt_manager()

    retrieve_node = create_retriever_node(retriever_type)
    grade_documents_node = create_document_grader_node(model_manager, prompt_manager)
    generate_node = create_generator_node(model_manager, prompt_manager)
    transform_query_node = create_rewriter_node(model_manager, prompt_manager)
    answer_grader_node = create_answer_grader_node(model_manager, prompt_manager)
    hallucination_grader_node = create_hallucination_grader_node(model_manager, prompt_manager)

    def check_iteration_limits(state: GraphState) -> bool:
        """Check if any iteration limit has been reached"""
        generation_attempts = state.get("generation_attempts", 0)
        transform_attempts = state.get("transform_attempts", 0)
        total_iterations = state.get("total_iterations", 0)

        if generation_attempts >= settings.max_generation_retries:
            logger.warning(f"Max generation retries reached: {generation_attempts}/{settings.max_generation_retries}")
            return True

        if transform_attempts >= settings.max_transform_retries:
            logger.warning(f"Max transform retries reached: {transform_attempts}/{settings.max_transform_retries}")
            return True

        if total_iterations >= settings.max_total_iterations:
            logger.warning(f"Max total iterations reached: {total_iterations}/{settings.max_total_iterations}")
            return True

        return False

    def decide_to_generate(state: GraphState) -> str:
        """
        Determines whether to generate an answer, re-generate a question,
        or fall back to pure LLM if no relevant documents found after max retries.

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call ("generate", "transform_query", or "no_docs_fallback")
        """
        logger.info("---ASSESS GRADED DOCUMENTS---")
        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            # Check if we've exceeded transform retry limit
            if transform_attempts >= settings.max_transform_retries:
                logger.warning(
                    f"---NO RELEVANT DOCUMENTS AFTER {transform_attempts} ATTEMPTS, "
                    f"FALLING BACK TO PURE LLM---"
                )
                return "no_docs_fallback"

            # Still have retries left, try transforming query
            logger.info(
                f"---DOCUMENTS NOT RELEVANT (attempt {transform_attempts + 1}/{settings.max_transform_retries}), "
                f"TRANSFORM QUERY---"
            )
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            logger.info("---DECISION: GENERATE---")
            return "generate"

    def grade_generation_v_documents_and_question(state: GraphState) -> str:
        """
        Determines whether the generation is grounded in the document and answers question.
        INCLUDES LOOP-GUARD CHECKS!

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call
        """
        logger.info("---CHECK HALLUCINATIONS---")

        if check_iteration_limits(state):
            logger.warning("---MAX ITERATIONS REACHED, RETURNING BEST-EFFORT ANSWER---")
            return "max_iterations"

        # Check if generation is grounded in documents
        hallucination_score = hallucination_grader_node(state)

        if hallucination_score.get("is_grounded", False):
            logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")

            # Check question-answering
            logger.info("---GRADE GENERATION vs QUESTION---")
            answer_score = answer_grader_node(state)

            if answer_score.get("addresses_question", False):
                logger.info("---DECISION: GENERATION ADDRESSES QUESTION---")
                return "useful"
            else:
                logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")

                if state.get("transform_attempts", 0) >= settings.max_transform_retries:
                    logger.warning("---MAX TRANSFORM RETRIES, ACCEPTING ANSWER AS-IS---")
                    return "useful"

                return "not useful"
        else:
            logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")

            if state.get("generation_attempts", 0) >= settings.max_generation_retries:
                logger.warning("---MAX GENERATION RETRIES, ACCEPTING BEST EFFORT---")
                return "max_iterations"

            return "not supported"

    def create_no_docs_fallback_node(model_manager, prompt_manager):
        """Create fallback node for when no relevant documents are found after max retries"""
        from langchain_core.output_parsers import StrOutputParser

        def generate_no_docs_fallback(state: Dict[str, Any]) -> Dict[str, Any]:
            """Generate answer using pure LLM when no relevant documents found"""
            logger.info("---GENERATE (NO DOCS FALLBACK - PURE LLM)---")

            question = state["question"]
            model_config = state.get("model_config", {})

            # Get chat model and pure LLM prompt
            llm = model_manager.get_chat_model("chat", **model_config)
            prompt = prompt_manager.get_pure_llm_prompt()

            # Create chain (no document context)
            llm_chain = prompt | llm | StrOutputParser()

            # Generate answer
            generation = llm_chain.invoke({"question": question})

            return {
                "documents": [],
                "question": question,
                "original_question": state.get("original_question", question),  # Preserve original
                "generation": generation,
                "model_config": model_config,
                "collection_ids": state.get("collection_ids", []),
                "generation_attempts": 1,
                "transform_attempts": state.get("transform_attempts", 0),
                "total_iterations": state.get("total_iterations", 0) + 1,
                "max_iterations_reached": True,
                "no_relevant_docs_fallback": True,
                "fallback_type": "no_relevant_docs"
            }

        return generate_no_docs_fallback

    def create_fallback_node():
        """Create node that marks max iterations reached (disclaimer is passed separately)"""
        def mark_max_iterations(state: Dict[str, Any]) -> Dict[str, Any]:
            logger.info("---MAX ITERATIONS REACHED---")

            return {
                **state,
                "max_iterations_reached": True,
                "no_relevant_docs_fallback": False,
                "fallback_type": "max_iterations"
            }

        return mark_max_iterations

    # Create fallback nodes
    fallback_node = create_fallback_node()
    no_docs_fallback_node = create_no_docs_fallback_node(model_manager, prompt_manager)

    # Create the workflow
    workflow = StateGraph(GraphState)

    # Define the nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("transform_query", transform_query_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("no_docs_fallback", no_docs_fallback_node)

    # Build graph
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "transform_query": "transform_query",
            "generate": "generate",
            "no_docs_fallback": "no_docs_fallback",
        },
    )

    workflow.add_edge("no_docs_fallback", END)

    workflow.add_edge("transform_query", "retrieve")

    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "not supported": "generate",
            "useful": END,
            "not useful": "transform_query",
            "max_iterations": "fallback",
        },
    )

    workflow.add_edge("fallback", END)

    return workflow.compile()