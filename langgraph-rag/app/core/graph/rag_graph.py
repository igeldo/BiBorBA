# core/graph/adaptive_graph.py
import logging

from langgraph.constants import END
from langgraph.graph import StateGraph, START
from langgraph.graph.state import CompiledStateGraph

from app.api.schemas.schemas import RetrieverType
from app.core.graph.nodes.generator import create_generator_node
from app.core.graph.nodes.retriever import create_retriever_node
from app.core.graph.utils import GraphState
from app.core.model_manager import get_model_manager
from app.core.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


def create_rag_graph(retriever_type: RetrieverType = RetrieverType.PDF) -> CompiledStateGraph:
    """Create and compile the  RAG graph.

    This is smple RAG Implementation without any agentic Features. It can be used as reference for agentic answers.
    """

    model_manager = get_model_manager()
    prompt_manager = get_prompt_manager()

    retrieve_node = create_retriever_node(retriever_type)
    generate_node = create_generator_node(model_manager, prompt_manager)

    workflow = StateGraph(GraphState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()