# services/graph_service.py
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from langchain_core.documents import Document
from langgraph.graph.state import CompiledStateGraph

from app.api.schemas.schemas import RetrieverType, GraphType
from app.config import settings
from app.core.graph.adaptive_graph import GraphState, create_adaptive_graph
from app.core.graph.rag_graph import create_rag_graph
from app.core.graph.pure_llm_graph import create_pure_llm_graph
from app.core.model_manager import get_model_manager
from app.database import SessionLocal, GraphExecution
from app.utils.timing import TimingContext

logger = logging.getLogger(__name__)


class GraphService:
    """Service for managing and executing LangGraph workflows"""

    def __init__(self):
        self._graphs: Dict[str, CompiledStateGraph] = {}
        self.model_manager = get_model_manager()

    def get_graph(
        self,
        graph_type: GraphType = GraphType.ADAPTIVE_RAG,
        retriever_type: RetrieverType = RetrieverType.PDF
    ) -> CompiledStateGraph:
        """Get or create a compiled graph for the specified graph type and retriever type"""
        graph_key = f"{graph_type.value}_{retriever_type.value}"

        if graph_key not in self._graphs:
            logger.info(f"Creating new graph - type: {graph_type.value}, retriever: {retriever_type.value}")

            if graph_type == GraphType.ADAPTIVE_RAG:
                self._graphs[graph_key] = create_adaptive_graph(retriever_type)
            elif graph_type == GraphType.SIMPLE_RAG:
                self._graphs[graph_key] = create_rag_graph(retriever_type)
            elif graph_type == GraphType.PURE_LLM:
                # Pure LLM doesn't use retriever, but we keep the key for caching
                self._graphs[graph_key] = create_pure_llm_graph()
            else:
                raise ValueError(f"Unknown graph type: {graph_type}")

        return self._graphs[graph_key]

    def rebuild_graph(
        self,
        graph_type: GraphType = GraphType.ADAPTIVE_RAG,
        retriever_type: RetrieverType = RetrieverType.PDF
    ):
        """Force rebuild of graph (useful for development)"""
        graph_key = f"{graph_type.value}_{retriever_type.value}"
        logger.info(f"Rebuilding graph - type: {graph_type.value}, retriever: {retriever_type.value}")

        if graph_type == GraphType.ADAPTIVE_RAG:
            self._graphs[graph_key] = create_adaptive_graph(retriever_type)
        elif graph_type == GraphType.SIMPLE_RAG:
            self._graphs[graph_key] = create_rag_graph(retriever_type)
        elif graph_type == GraphType.PURE_LLM:
            self._graphs[graph_key] = create_pure_llm_graph()
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")

        return self._graphs[graph_key]

    async def execute_query(
            self,
            question: str,
            session_id: str,
            graph_type: GraphType = GraphType.ADAPTIVE_RAG,
            retriever_type: RetrieverType = RetrieverType.PDF,
            model_config: Optional[Dict[str, Any]] = None,
            collection_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Execute a query through the graph workflow - always fresh execution"""

        start_time = time.time()
        execution_trace = []
        node_timings = {}

        logger.debug(f"⏱️  START: Graph execution for query: '{question[:50]}...' with graph type: {graph_type.value}")

        try:
            # Get the appropriate graph
            with TimingContext("Get/create graph", logger):
                graph = self.get_graph(graph_type, retriever_type)

            # Prepare initial state with iteration tracking
            initial_state = GraphState(
                question=question,
                original_question=question,  # Preserve original for generation after rewrites
                generation="",
                documents=[],
                model_config=model_config or {},
                collection_ids=collection_ids or [],
                generation_attempts=0,
                transform_attempts=0,
                total_iterations=0,
                max_iterations_reached=False,
                no_relevant_docs_fallback=False,
                fallback_type=""
            )

            # Execute graph with tracing and recursion limit
            final_state = None
            logger.debug("⏱️  START: Graph streaming execution")
            stream_start = time.time()
            last_step_time = stream_start  # Track time between stream outputs

            for step_output in graph.stream(
                initial_state,
                {"recursion_limit": settings.graph_recursion_limit}
            ):
                current_time = time.time()
                # Measure time since last output (= actual node execution time)
                step_duration = (current_time - last_step_time) * 1000

                for node_name, node_output in step_output.items():
                    execution_trace.append(node_name)
                    node_timings[node_name] = step_duration

                    logger.info(f"Executed node '{node_name}' in {step_duration:.2f}ms")
                    logger.debug(f"✅ Node '{node_name}' completed: {step_duration:.1f}ms")
                    final_state = node_output

                last_step_time = current_time  # Update for next iteration

            stream_duration = (time.time() - stream_start) * 1000
            logger.debug(f"✅ DONE: Graph streaming execution - {stream_duration:.1f}ms")

            total_duration = int((time.time() - start_time) * 1000)

            # Extract document details for frontend display
            documents = final_state.get("documents", [])
            retrieved_documents = []
            for doc in documents:
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                    metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                else:
                    content = str(doc)
                    metadata = {}

                # Determine source type from metadata
                source = metadata.get('source_type', 'unknown')
                if 'stackoverflow' in str(metadata).lower() or 'so_question_id' in metadata:
                    source = 'stackoverflow'
                elif 'pdf' in str(metadata).lower() or metadata.get('file_path', '').endswith('.pdf'):
                    source = 'pdf'

                # Build document info
                doc_info = {
                    "source": source,
                    "title": metadata.get('title') or metadata.get('question_title') or metadata.get('file_path', 'Unknown'),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "full_content": content,
                    "relevance_score": metadata.get('relevance_score') or metadata.get('score'),
                    "metadata": {
                        k: v for k, v in metadata.items()
                        if k not in ['page_content', 'full_content'] and isinstance(v, (str, int, float, bool, list))
                    }
                }
                retrieved_documents.append(doc_info)

            # Extract results
            result = {
                "answer": final_state.get("generation", "No answer generated"),
                "documents_retrieved": len(documents),
                "graph_trace": execution_trace,
                "rewritten_question": final_state.get("question") if final_state.get("question") != question else None,
                "processing_time_ms": total_duration,
                "iteration_metrics": {
                    "generation_attempts": final_state.get("generation_attempts", 0),
                    "transform_attempts": final_state.get("transform_attempts", 0),
                    "total_iterations": final_state.get("total_iterations", 0),
                    "max_iterations_reached": final_state.get("max_iterations_reached", False),
                    "no_relevant_docs_fallback": final_state.get("no_relevant_docs_fallback", False),
                    "disclaimer": self._get_disclaimer_text(final_state)
                },
                "retrieved_documents": retrieved_documents,
                "node_timings": node_timings
            }

            # Store execution details for monitoring (sync call)
            with TimingContext("Store execution details in database", logger):
                graph_execution_id = self._store_execution_details(
                    session_id=session_id,
                    graph_type=graph_type.value,
                    execution_path=execution_trace,
                    node_timings=node_timings,
                    total_duration=total_duration,
                    success=True
                )

            # Add graph_execution_id to result for linking with evaluations
            result["graph_execution_id"] = graph_execution_id

            logger.info(f"Query executed successfully in {total_duration}ms: {question[:50]}...")
            logger.debug(f"✅ DONE: Full graph execution - {total_duration}ms")

            # Log execution summary
            logger.debug("=" * 70)
            logger.debug(f"EXECUTION SUMMARY for '{question[:50]}...'")
            logger.debug(f"Total Duration: {total_duration}ms")
            logger.debug(f"Execution Path: {' → '.join(execution_trace)}")
            logger.debug(f"Total Iterations: {result['iteration_metrics']['total_iterations']}")
            logger.debug(f"Generation Attempts: {result['iteration_metrics']['generation_attempts']}")
            logger.debug(f"Transform Attempts: {result['iteration_metrics']['transform_attempts']}")
            logger.debug("Node Timings:")
            for node, timing in node_timings.items():
                logger.debug(f"  - {node}: {timing:.1f}ms")
            logger.debug("=" * 70)

            return result

        except Exception as e:
            total_duration = int((time.time() - start_time) * 1000)
            logger.error(f"Graph execution failed: {e}")

            # Store failed execution (sync call)
            self._store_execution_details(
                session_id=session_id,
                graph_type=graph_type.value,
                execution_path=execution_trace,
                node_timings=node_timings,
                total_duration=total_duration,
                success=False,
                error_message=str(e)
            )

            raise e

    def _get_disclaimer_text(self, final_state: Dict[str, Any]) -> Optional[str]:
        """Get disclaimer text based on fallback state flags"""
        if final_state.get("no_relevant_docs_fallback", False):
            return "Diese Antwort basiert auf allgemeinem Wissen, nicht auf Dokumenten aus der Wissensbasis."
        elif final_state.get("max_iterations_reached", False):
            return "Diese Antwort konnte nicht vollständig verifiziert werden."
        return None

    def _store_execution_details(
            self,
            session_id: str,
            graph_type: str,
            execution_path: List[str],
            node_timings: Dict[str, float],
            total_duration: int,
            success: bool,
            error_message: Optional[str] = None
    ) -> Optional[int]:
        """Store detailed execution information in the database and return the execution ID"""
        db = SessionLocal()
        try:
            execution = GraphExecution(
                session_id=session_id,
                graph_type=graph_type,
                execution_path=execution_path,
                node_timings=node_timings,
                total_duration_ms=total_duration,
                success=success,
                error_message=error_message,
                completed_at=datetime.utcnow()
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            return execution.id

        except Exception as e:
            logger.error(f"Failed to store execution details: {e}")
            return None
        finally:
            db.close()

    def get_execution_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics for monitoring"""
        db = SessionLocal()
        try:
            query = db.query(GraphExecution)

            if session_id:
                query = query.filter(GraphExecution.session_id == session_id)

            executions = query.all()

            if not executions:
                return {"total_executions": 0}

            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.success)
            avg_duration = sum(e.total_duration_ms for e in executions) / total_executions

            # Most common execution paths
            path_counts = {}
            for execution in executions:
                path_key = " -> ".join(execution.execution_path or [])
                path_counts[path_key] = path_counts.get(path_key, 0) + 1

            most_common_path = max(path_counts.items(), key=lambda x: x[1]) if path_counts else ("", 0)

            return {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "success_rate": successful_executions / total_executions * 100,
                "average_duration_ms": round(avg_duration, 2),
                "most_common_execution_path": most_common_path[0],
                "path_frequency": most_common_path[1],
                "execution_paths": path_counts
            }

        finally:
            db.close()