# app/api/routes/stackoverflow.py
"""
StackOverflow-spezifische Endpoints
- Answer Generation
- Statistics
- Search
- Question Details
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.api.schemas.schemas import (
    GenerateAnswerRequest,
    StackOverflowStats,
    StackOverflowQueryRequest,
    RetrieverType,
    PaginatedQuestionsResponse,
    SortField,
    SortOrder,
    QueryResponse,
    IterationMetrics,
    RetrievedDocument
)
from app.config import settings
from app.database import get_db
from app.dependencies import (
    get_stackoverflow_connector,
    get_vector_store_service,
    get_evaluation_service,
    get_graph_service
)

router = APIRouter(prefix="/stackoverflow", tags=["StackOverflow"])
logger = logging.getLogger(__name__)


async def query_multi_source(
    request: StackOverflowQueryRequest,
    db: Session,
    graph_service
) -> QueryResponse:
    """
    Execute a multi-source query using StackOverflow data.

    This is a helper function used by generate_stackoverflow_answer.
    """
    start_time = time.time()

    result = await graph_service.execute_query(
        question=request.question,
        session_id=request.session_id,
        graph_type=request.graph_type,
        retriever_type=RetrieverType.STACKOVERFLOW,
        model_config=request.llm_config or {}
    )

    processing_time = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time

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
        stackoverflow_documents=result.get("documents_retrieved", 0),
        processing_time_ms=processing_time,
        confidence_score=result.get("confidence_score"),
        rewritten_question=result.get("rewritten_question"),
        graph_trace=result.get("graph_trace"),
        source_breakdown={"stackoverflow": result.get("documents_retrieved", 0)},
        iteration_metrics=iteration_metrics,
        retrieved_documents=retrieved_docs,
        node_timings=result.get("node_timings")
    )


@router.post("/generate-answer")
async def generate_stackoverflow_answer(
        request: GenerateAnswerRequest,
        db: Session = Depends(get_db),
        graph_service=Depends(get_graph_service),
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    Generate new answer for StackOverflow question

    Verwendet Multi-Source Retrieval und führt automatische Evaluation durch.
    """
    try:
        question_data = so_connector.get_question_by_id(request.question_id)
        if not question_data:
            raise HTTPException(status_code=404, detail=f"Question {request.question_id} not found")

        # Build query from question only (no existing answers)
        query_parts = [question_data['title']]

        if question_data.get('body'):
            query_parts.append(question_data['body'])

        query_text = " ".join(query_parts).strip()

        logger.info(f"Generating answer for SO question {request.question_id}: '{question_data['title']}'")

        multi_source_request = StackOverflowQueryRequest(
            question=query_text,
            session_id=request.session_id,
            include_stackoverflow=True,
            stackoverflow_filters={
                "min_score": 1,
                "tags": question_data.get('tags', []),
                "only_accepted_answers": False,
                "limit": 100
            },
            llm_config=request.llm_config or {}
        )

        result = await query_multi_source(multi_source_request, db, graph_service)

        evaluation_service = get_evaluation_service()
        evaluation_id = None

        try:
            evaluation_id = evaluation_service.evaluate_stackoverflow_answer_with_reference(
                question_id=request.question_id,
                generated_answer=result.answer,
                session_id=request.session_id,
                model_config=request.llm_config
            )

            if evaluation_id:
                logger.info(f"Automatic evaluation created: {evaluation_id}")

        except Exception as e:
            logger.warning(f"Automatic evaluation error: {e}")

        return {
            "question_id": request.question_id,
            "question_title": question_data['title'],
            "question_body": question_data.get('body', ''),
            "question_tags": question_data.get('tags', []),
            "generated_answer": result.answer,
            "confidence_score": result.confidence_score,
            "processing_time_ms": result.processing_time_ms,
            "documents_retrieved": result.documents_retrieved,
            "stackoverflow_documents": result.stackoverflow_documents,
            "source_breakdown": result.source_breakdown,
            "existing_answers_count": len(question_data.get('answers', [])),
            "session_id": request.session_id,
            "evaluation_id": evaluation_id,
            "graph_trace": result.graph_trace,
            "rewritten_question": result.rewritten_question
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"StackOverflow answer generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")


@router.get("/questions", response_model=PaginatedQuestionsResponse)
async def list_stackoverflow_questions(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        tags: Optional[str] = Query(None, description="Comma-separated tags filter"),
        min_score: Optional[int] = Query(None, ge=0, description="Minimum score"),
        sort_by: SortField = Query(SortField.CREATION_DATE, description="Sort field"),
        sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    List all Stackoverflow questions from database (paginated)

    Returns all questions stored in the PostgreSQL database with pagination.
    Useful for data exploration and selecting test questions.

    Parameters:
    - page: Page number (1-indexed)
    - page_size: Number of items per page (max 100)
    - tags: Filter by tags (comma-separated, OR logic)
    - min_score: Filter by minimum question score
    - sort_by: Sort field (creation_date, score, view_count)
    - sort_order: Sort order (asc or desc)
    """
    try:
        tag_list = tags.split(",") if tags else None

        result = so_connector.get_questions_paginated(
            page=page,
            page_size=page_size,
            tags=tag_list,
            min_score=min_score,
            sort_by=sort_by.value,
            sort_order=sort_order.value
        )

        return PaginatedQuestionsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list questions: {str(e)}")


@router.get("/questions-with-collections")
async def get_questions_with_collections(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        tags: Optional[str] = Query(None, description="Comma-separated tags filter"),
        min_score: Optional[int] = Query(None, ge=0, description="Minimum score"),
        sort_by: SortField = Query(SortField.CREATION_DATE, description="Sort field"),
        sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
        only_without_collections: bool = Query(False, description="Only show questions not in any collection"),
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    Get StackOverflow questions with collection membership info.

    - Shows which collections each question belongs to
    - Can filter to show only questions NOT in any collection
    - Supports pagination, filtering, and sorting
    - Used for batch query selection UI

    Parameters:
    - page: Page number (1-indexed)
    - page_size: Number of items per page (max 100)
    - tags: Filter by tags (comma-separated, OR logic)
    - min_score: Filter by minimum question score
    - sort_by: Sort field (creation_date, score, view_count)
    - sort_order: Sort order (asc or desc)
    - only_without_collections: If True, only return questions not in any collection
    """
    try:
        tag_list = tags.split(",") if tags else None

        result = so_connector.get_questions_with_collections(
            page=page,
            page_size=page_size,
            tags=tag_list,
            min_score=min_score,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
            only_without_collections=only_without_collections
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions with collections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions with collections: {str(e)}")


@router.get("/stats", response_model=StackOverflowStats)
async def get_stackoverflow_stats(
        vector_store_service=Depends(get_vector_store_service)
):
    """
    Get statistics about StackOverflow data

    Zeigt Anzahl der Dokumente, Tags, etc. in der Vector Store Collection.
    """
    try:
        stats = vector_store_service.get_stackoverflow_stats()

        if not stats or "error" in stats:
            raise HTTPException(
                status_code=503,
                detail="StackOverflow data not available or connection failed"
            )

        return StackOverflowStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting StackOverflow stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/rebuild-collection")
async def rebuild_stackoverflow_collection(
        background_tasks: BackgroundTasks,
        vector_store_service=Depends(get_vector_store_service)
):
    """
    Rebuild StackOverflow vector store collection

    Lädt Daten neu aus der StackOverflow-Datenbank und indexiert sie.
    Läuft im Hintergrund.
    """

    def rebuild_task():
        try:
            result = vector_store_service.rebuild_collection(RetrieverType.STACKOVERFLOW)
            logger.info(f"StackOverflow collection rebuilt: {result}")
        except Exception as e:
            logger.error(f"StackOverflow collection rebuild failed: {e}")

    background_tasks.add_task(rebuild_task)

    return {
        "message": "StackOverflow collection rebuild started",
        "status": "running",
        "filters": settings.stackoverflow_default_filters
    }


@router.get("/search")
async def search_stackoverflow_direct(
        q: str,
        limit: int = 10,
        min_score: int = 0,
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    Direct search in StackOverflow database (not vector search)

    Sucht direkt in der SQL-Datenbank (nicht im Vector Store).
    Nützlich für debugging und administrative Zwecke.
    """
    try:
        results = so_connector.search_questions(
            search_term=q,
            limit=limit,
            min_score=min_score
        )

        return {
            "query": q,
            "results": results,
            "count": len(results),
            "search_type": "direct_database"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"StackOverflow direct search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/question/{question_id}")
async def get_stackoverflow_question(
        question_id: int,
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    Get specific StackOverflow question with answers

    Liefert alle Details zu einer Frage inklusive aller Antworten.
    """
    try:
        question = so_connector.get_question_by_id(question_id)

        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")

        return question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting StackOverflow question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get question: {str(e)}")