from typing import Dict, Any
from pydantic import BaseModel, Field
import logging
import time
import asyncio

from app.config import settings
from app.utils.timing import TimingContext
from app.core.graph.utils import format_docs

logger = logging.getLogger(__name__)

class GradeDocuments(BaseModel):
    """Extended grading with confidence and reasoning for retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")
    confidence: float = Field(
        description="Confidence level from 0.0 (not confident) to 1.0 (very confident)",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation why the document is/isn't relevant (max 2 sentences)"
    )


def create_document_grader_node(model_manager, prompt_manager):
    """Create document grader node"""

    def grade_documents(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines whether the retrieved documents are relevant to the question with iteration tracking
        """
        logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        question = state["question"]
        documents = state["documents"]

        total_iterations = state.get("total_iterations", 0) + 1

        if isinstance(documents, str):
            from langchain_core.documents import Document
            documents = [Document(page_content=documents, metadata={"source": "string_input"})]
        elif not isinstance(documents, list):
            documents = [documents] if documents else []

        normalized_docs = []
        for doc in documents:
            if hasattr(doc, 'page_content'):
                normalized_docs.append(doc)
            elif isinstance(doc, str):
                from langchain_core.documents import Document
                normalized_docs.append(Document(page_content=doc, metadata={"source": "string_conversion"}))
            else:
                from langchain_core.documents import Document
                normalized_docs.append(Document(page_content=str(doc), metadata={"source": "unknown_type"}))

        logger.info(f"Normalized to {len(normalized_docs)} Document objects")

        with TimingContext("Get grader model and prompt", logger):
            llm = model_manager.get_structured_model("grader", GradeDocuments, format="json")
            prompt = prompt_manager.get_document_grader_prompt()
            grader = prompt | llm

        async def grade_single_doc(doc, doc_index):
            """Grade a single document asynchronously"""
            try:
                content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                logger.info(f"Grading document {doc_index + 1}: {content[:100]}...")

                doc_start = time.perf_counter()

                max_retries = settings.document_grading_retry_attempts
                score = None

                for attempt in range(max_retries):
                    try:
                        score = await grader.ainvoke({
                            "question": question,
                            "document": content
                        })
                        break  # Success
                    except RuntimeError as e:
                        error_msg = str(e).lower()
                        # httpcore raises RuntimeError if TCPTransport closure, but no specific exception
                        is_tcp_error = "tcptransport" in error_msg and "closed" in error_msg

                        if is_tcp_error and attempt < max_retries - 1:
                            logger.warning(f"TCPTransport error on doc {doc_index + 1}, retry {attempt + 1}/{max_retries}")
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            raise
                    except Exception as e:
                        logger.error(f"Non-retryable error on doc {doc_index + 1}: {type(e).__name__}: {e}")
                        raise

                doc_duration = (time.perf_counter() - doc_start) * 1000
                logger.debug(f"✅ LLM call for document {doc_index + 1} grading: {doc_duration:.1f}ms")

                grade = score.binary_score
                confidence = score.confidence
                reasoning = score.reasoning

                logger.info(f"Grade - Document {doc_index + 1}: {grade} (confidence: {confidence:.2f})")
                logger.debug(f"Reasoning: {reasoning}")

                confidence_threshold = settings.document_grading_confidence_threshold
                is_relevant = (grade == "yes" and confidence >= confidence_threshold)

                if is_relevant:
                    logger.info(f"---GRADE: DOCUMENT {doc_index + 1} ACCEPTED (confidence: {confidence:.2f})---")
                    return (doc, True, None, confidence, reasoning)
                else:
                    if grade == "yes":
                        logger.info(f"---GRADE: DOCUMENT {doc_index + 1} REJECTED (low confidence: {confidence:.2f} < {confidence_threshold})---")
                    else:
                        logger.info(f"---GRADE: DOCUMENT {doc_index + 1} NOT RELEVANT---")
                    return (doc, False, None, confidence, reasoning)

            except Exception as e:
                logger.error(f"Error grading document {doc_index + 1}: {e}")
                logger.info(f"---GRADE: DOCUMENT {doc_index + 1} ERROR (SKIPPING)---")
                return (doc, False, e, 0.0, f"Error: {str(e)}")

        async def grade_all_docs():
            """Grade all documents in batches to avoid TCP connection pool exhaustion"""
            batch_size = settings.document_grading_batch_size  # Default: 4
            all_results = []

            for batch_start in range(0, len(normalized_docs), batch_size):
                batch_end = min(batch_start + batch_size, len(normalized_docs))
                batch_docs = normalized_docs[batch_start:batch_end]

                logger.debug(f"Grading batch {batch_start//batch_size + 1}: documents {batch_start+1}-{batch_end}")

                tasks = [grade_single_doc(doc, batch_start + i) for i, doc in enumerate(batch_docs)]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        doc_index = batch_start + i
                        logger.error(f"Uncaught exception grading document {doc_index + 1}: {result}")
                        all_results.append((normalized_docs[doc_index], False, result, 0.0, f"Error: {str(result)}"))
                    else:
                        all_results.append(result)

            return all_results

        grading_start = time.perf_counter()
        logger.debug(f"START: Grading {len(normalized_docs)} documents in batches of {settings.document_grading_batch_size}")

        # This avoids conflicts with existing event loops (e.g., uvloop in FastAPI)
        from concurrent.futures import ThreadPoolExecutor

        def run_async_grading():
            """Run async grading in a new event loop"""
            return asyncio.run(grade_all_docs())

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_grading)
            grading_results = future.result()

        filtered_docs = []
        document_grades = []

        for doc, is_relevant, error, confidence, reasoning in grading_results:
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)

            # Store grading details for debugging
            document_grades.append({
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "is_relevant": is_relevant,
                "confidence": confidence,
                "reasoning": reasoning,
                "error": str(error) if error else None
            })

            if is_relevant and error is None:
                filtered_docs.append(doc)

        total_grading_time = (time.perf_counter() - grading_start) * 1000
        avg_time = total_grading_time / len(normalized_docs) if normalized_docs else 0
        num_batches = (len(normalized_docs) + settings.document_grading_batch_size - 1) // settings.document_grading_batch_size
        logger.debug(f"DONE: Graded {len(normalized_docs)} documents in {num_batches} batches - Total: {total_grading_time:.1f}ms, Avg: {avg_time:.1f}ms/doc")
        logger.debug(f"Batch processing completed - {len(normalized_docs)} documents graded in batches of {settings.document_grading_batch_size}")
        logger.info(f"Filtered to {len(filtered_docs)} relevant documents (confidence threshold: {settings.document_grading_confidence_threshold})")

        return {
            "documents": filtered_docs,
            "question": question,
            "original_question": state.get("original_question", question),  # Preserve original
            "generation": state.get("generation", ""),
            "model_config": state.get("model_config", {}),
            "collection_ids": state.get("collection_ids", []),
            "generation_attempts": state.get("generation_attempts", 0),
            "transform_attempts": state.get("transform_attempts", 0),
            "total_iterations": total_iterations,
            "max_iterations_reached": False,
            "no_relevant_docs_fallback": False,
            "fallback_type": ""
        }

    return grade_documents
