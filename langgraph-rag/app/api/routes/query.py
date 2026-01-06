# app/api/routes/query.py
"""
Query-bezogene Endpoints
- Standard Query
- Collection Query
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.schemas import (
    RetrieverType,
    GraphType,
    StackOverflowQueryRequest,
    CollectionQueryRequest,
    CollectionBreakdown,
    QueryResponse,
    IterationMetrics,
    RetrievedDocument,
    QueryRatingRequest
)
from app.api.middleware import safe_error_handler
from app.database import get_db, QueryLogService, QueryLog
from app.dependencies import get_collection_manager, get_graph_service

router = APIRouter(prefix="/query", tags=["Query"])
logger = logging.getLogger(__name__)


@router.post("", response_model=QueryResponse)
@safe_error_handler
async def query_documents(
        request: StackOverflowQueryRequest,
        db: Session = Depends(get_db),
        graph_service=Depends(get_graph_service)
):
    """
    Standard query endpoint for PDF documents.

    Note: For multi-source queries, use /query/collections with multiple collection IDs.
    """
    start_time = time.time()

    result = await graph_service.execute_query(
        question=request.question,
        session_id=request.session_id,
        graph_type=request.graph_type,
        retriever_type=RetrieverType.PDF,
        model_config=request.llm_config or {}
    )

    processing_time = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time

    QueryLogService.log_query(
        db=db,
        session_id=request.session_id,
        question=request.question,
        answer=result["answer"],
        rewritten_question=result.get("rewritten_question"),
        retriever_type="pdf",
        graph_type=request.graph_type.value,
        documents_retrieved=result.get("documents_retrieved", 0),
        processing_time_ms=processing_time,
        model_config=request.llm_config,
        graph_trace=result.get("graph_trace")
    )

    iteration_metrics = None
    if result.get("iteration_metrics"):
        iteration_metrics = IterationMetrics(**result["iteration_metrics"])

    retrieved_docs = None
    if result.get("retrieved_documents"):
        retrieved_docs = [
            RetrievedDocument(**doc) for doc in result["retrieved_documents"]
        ]

    return QueryResponse(
        answer=result["answer"],
        session_id=request.session_id,
        graph_type=request.graph_type.value,
        documents_retrieved=result.get("documents_retrieved", 0),
        stackoverflow_documents=0,
        processing_time_ms=processing_time,
        rewritten_question=result.get("rewritten_question"),
        graph_trace=result.get("graph_trace"),
        source_breakdown={"pdf": result.get("documents_retrieved", 0)},
        iteration_metrics=iteration_metrics,
        retrieved_documents=retrieved_docs,
        node_timings=result.get("node_timings")
    )


@router.post("/collections", response_model=QueryResponse)
@safe_error_handler
async def query_collections(
        request: CollectionQueryRequest,
        db: Session = Depends(get_db),
        graph_service=Depends(get_graph_service),
        collection_manager=Depends(get_collection_manager)
):
    """
    Query mit Custom Collections

    Kombiniert mehrere Collections (StackOverflow und/oder PDF) für optimale Antworten.
    """
    if not request.collection_ids:
        raise HTTPException(status_code=400, detail="At least one collection_id is required")

    start_time = time.time()
    logger.info(f"Collection query with {len(request.collection_ids)} collections: {request.collection_ids}")

    result = await graph_service.execute_query(
        question=request.question,
        session_id=request.session_id,
        graph_type=request.graph_type,
        retriever_type=RetrieverType.PDF,
        collection_ids=request.collection_ids,
        model_config=request.llm_config or {}
    )

    collection_breakdown = []

    for collection_id in request.collection_ids:
        collection = collection_manager.get_collection(collection_id)
        if collection:
            collection_breakdown.append(CollectionBreakdown(
                collection_name=collection.name,
                collection_type=collection.collection_type,
                document_count=0
            ))

    total_documents = result.get("documents_retrieved", 0)
    processing_time = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time

    QueryLogService.log_query(
        db=db,
        session_id=request.session_id,
        question=request.question,
        answer=result["answer"],
        rewritten_question=result.get("rewritten_question"),
        retriever_type="collections",
        graph_type=request.graph_type.value,
        documents_retrieved=total_documents,
        processing_time_ms=processing_time,
        model_config=request.llm_config or {},
        graph_trace=result.get("graph_trace")
    )

    iteration_metrics = None
    if result.get("iteration_metrics"):
        iteration_metrics = IterationMetrics(**result["iteration_metrics"])

    retrieved_docs = None
    if result.get("retrieved_documents"):
        retrieved_docs = [
            RetrievedDocument(**doc) for doc in result["retrieved_documents"]
        ]

    return QueryResponse(
        answer=result["answer"],
        session_id=request.session_id,
        graph_type=request.graph_type.value,
        documents_retrieved=total_documents,
        stackoverflow_documents=0,
        processing_time_ms=processing_time,
        rewritten_question=result.get("rewritten_question"),
        graph_trace=result.get("graph_trace"),
        source_breakdown={},
        collection_breakdown=collection_breakdown,
        iteration_metrics=iteration_metrics,
        retrieved_documents=retrieved_docs,
        node_timings=result.get("node_timings")
    )


@router.post("/rate")
@safe_error_handler
async def rate_query(
        request: QueryRatingRequest,
        db: Session = Depends(get_db)
):
    """
    Rate a query result with 1-5 stars

    Finds the most recent query for the given session_id and adds a user rating.
    """
    query_log = db.query(QueryLog).filter(
        QueryLog.session_id == request.session_id
    ).order_by(QueryLog.created_at.desc()).first()

    if not query_log:
        raise HTTPException(
            status_code=404,
            detail=f"No query found for session_id: {request.session_id}"
        )

    query_log.user_rating = request.rating
    if request.comment:
        query_log.user_rating_comment = request.comment

    db.commit()
    db.refresh(query_log)

    logger.info(f"Query rated: session={request.session_id}, rating={request.rating}")

    return {
        "message": "Rating saved successfully",
        "session_id": request.session_id,
        "rating": request.rating,
        "query_id": query_log.id
    }