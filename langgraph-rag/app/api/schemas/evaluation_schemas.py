from typing import Optional

from pydantic import BaseModel, Field


class ManualEvaluationRequest(BaseModel):
    """Request for adding manual evaluation"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, description="Optional comment")
    evaluator_name: Optional[str] = Field(None, description="Name of evaluator")


class BERTScoreRequest(BaseModel):
    """Request for BERT Score evaluation"""
    generated_answer: str = Field(..., description="Generated answer text")
    reference_answer: str = Field(..., description="Reference answer text")


class BERTScoreResponse(BaseModel):
    """Response for BERT Score evaluation"""
    precision: float
    recall: float
    f1: float
    model_type: str
    interpretation: str