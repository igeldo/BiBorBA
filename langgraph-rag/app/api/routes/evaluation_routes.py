# app/api/evaluation_routes.py
"""
API routes for answer evaluation system
"""
import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas.evaluation_schemas import BERTScoreResponse, BERTScoreRequest, ManualEvaluationRequest
from app.api.middleware import safe_error_handler
from app.dependencies import get_bert_evaluation_service, get_evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = logging.getLogger(__name__)


@router.post("/bert-score", response_model=BERTScoreResponse)
async def compute_bert_score(request: BERTScoreRequest):
    """Compute BERT Score between generated and reference answers"""
    try:
        bert_service = get_bert_evaluation_service()

        if not bert_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="BERT Score service not available. Please install bert-score package."
            )

        result = bert_service.evaluate_answer(
            request.generated_answer,
            request.reference_answer
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="BERT Score computation failed"
            )

        return BERTScoreResponse(
            precision=result.precision,
            recall=result.recall,
            f1=result.f1,
            model_type=result.model_type,
            interpretation=bert_service.get_score_interpretation(result.f1)
        )

    except Exception as e:
        logger.error(f"BERT Score computation error: {e}")
        raise HTTPException(status_code=500, detail=f"BERT Score failed: {str(e)}")


@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(evaluation_id: int):
    """Get specific evaluation by ID"""
    try:
        evaluation_service = get_evaluation_service()
        result = evaluation_service.get_evaluation(evaluation_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation {evaluation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation: {str(e)}")


@router.post("/evaluations/{evaluation_id}/manual")
async def add_manual_evaluation(
        evaluation_id: int,
        request: ManualEvaluationRequest
):
    """Add manual evaluation to existing evaluation record"""
    try:
        evaluation_service = get_evaluation_service()

        success = evaluation_service.add_manual_evaluation(
            evaluation_id=evaluation_id,
            rating=request.rating,
            comment=request.comment,
            evaluator_name=request.evaluator_name
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )

        return {
            "message": "Manual evaluation added successfully",
            "evaluation_id": evaluation_id,
            "rating": request.rating
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding manual evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add manual evaluation: {str(e)}")


@router.get("/sessions/{session_id}/evaluations")
async def get_session_evaluations(session_id: str):
    """Get all evaluations for a specific session"""
    try:
        evaluation_service = get_evaluation_service()
        evaluations = evaluation_service.get_evaluations_by_session(session_id)

        return {
            "session_id": session_id,
            "evaluations": evaluations,
            "count": len(evaluations)
        }

    except Exception as e:
        logger.error(f"Error getting session evaluations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get evaluations: {str(e)}")


@router.get("/statistics")
async def get_evaluation_statistics():
    """Get evaluation statistics"""
    try:
        evaluation_service = get_evaluation_service()
        stats = evaluation_service.get_evaluation_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error getting evaluation statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/status")
async def get_evaluation_status():
    """Get evaluation system status"""
    try:
        bert_service = get_bert_evaluation_service()
        evaluation_service = get_evaluation_service()

        return {
            "bert_score_available": bert_service.is_available(),
            "bert_model_type": bert_service.model_type if bert_service.is_available() else None,
            "evaluation_service_active": True,
            "database_connected": True
        }

    except Exception as e:
        logger.error(f"Error getting evaluation status: {e}")
        return {
            "bert_score_available": False,
            "evaluation_service_active": False,
            "database_connected": False,
            "error": str(e)
        }