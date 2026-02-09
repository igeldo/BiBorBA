from typing import List, Any, Dict

from typing_extensions import TypedDict


def format_docs(docs: List[Any]) -> str:
    """Concatenate document contents into a single string separated by double newlines."""
    return "\n\n".join(
        doc.page_content if hasattr(doc, 'page_content') else str(doc)
        for doc in docs
    )


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: current question (may be rewritten for retrieval)
        original_question: original user question (never modified, used for answer generation)
        generation: LLM generation
        documents: list of documents
        model_config: optional model configuration overrides
        collection_ids: optional list of collection IDs for retrieval
        generation_attempts: number of generation retry attempts
        transform_attempts: number of query transformation attempts
        total_iterations: total number of graph iterations
        max_iterations_reached: flag indicating if max iterations were reached
        no_relevant_docs_fallback: flag indicating if Pure LLM fallback was used due to no relevant documents
        fallback_type: type of fallback used ("max_iterations", "no_relevant_docs", or "")
    """
    question: str
    original_question: str
    generation: str
    documents: List[Any]
    model_config: Dict[str, Any]
    collection_ids: List[int]

    generation_attempts: int
    transform_attempts: int
    total_iterations: int
    max_iterations_reached: bool

    no_relevant_docs_fallback: bool
    fallback_type: str