"""
StackOverflow-spezifische Endpoints
- Question Listing
- Question Details
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.schemas import (
    PaginatedQuestionsResponse,
    SortField,
    SortOrder,
)
from app.dependencies import (
    get_stackoverflow_connector,
)

router = APIRouter(prefix="/stackoverflow", tags=["StackOverflow"])
logger = logging.getLogger(__name__)


@router.get("/questions", response_model=PaginatedQuestionsResponse)
async def list_stackoverflow_questions(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=200, description="Items per page (max 200)"),
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
        page_size: int = Query(20, ge=1, le=200, description="Items per page (max 200)"),
        tags: Optional[str] = Query(None, description="Comma-separated tags filter"),
        min_score: Optional[int] = Query(None, ge=0, description="Minimum score"),
        sort_by: SortField = Query(SortField.CREATION_DATE, description="Sort field"),
        sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
        only_without_collections: bool = Query(False, description="Only show questions not in any collection"),
        not_in_collection_ids: Optional[str] = Query(
            None,
            description="Comma-separated collection IDs - filter to questions NOT in these specific collections"
        ),
        only_without_evaluations: bool = Query(
            False,
            description="Only show questions without any generated answers"
        ),
        so_connector=Depends(get_stackoverflow_connector)
):
    """
    Get StackOverflow questions with collection membership info.

    - Shows which collections each question belongs to
    - Can filter to show only questions NOT in any collection (global filter)
    - Can filter to show only questions NOT in specific collections (collection-specific filter)
    - Can filter to show only questions without generated answers
    - Supports pagination, filtering, and sorting
    - Used for batch query selection UI

    Parameters:
    - page: Page number (1-indexed)
    - page_size: Number of items per page (max 100)
    - tags: Filter by tags (comma-separated, OR logic)
    - min_score: Filter by minimum question score
    - sort_by: Sort field (creation_date, score, view_count)
    - sort_order: Sort order (asc or desc)
    - only_without_collections: If True, enables the collection filter
    - not_in_collection_ids: If provided with only_without_collections=True, filter to questions NOT in these specific collections
    - only_without_evaluations: If True, only show questions without any generated answers
    """
    try:
        tag_list = tags.split(",") if tags else None
        collection_id_list = [int(x) for x in not_in_collection_ids.split(",")] if not_in_collection_ids else None

        result = so_connector.get_questions_with_collections(
            page=page,
            page_size=page_size,
            tags=tag_list,
            min_score=min_score,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
            only_without_collections=only_without_collections,
            not_in_collection_ids=collection_id_list,
            only_without_evaluations=only_without_evaluations
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions with collections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions with collections: {str(e)}")


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
