from typing import List, Optional

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique collection name")
    description: Optional[str] = Field(None, description="Optional description")
    collection_type: str = Field(default="stackoverflow", description="Type of collection")


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    collection_type: str
    question_count: int
    created_at: str
    last_rebuilt_at: Optional[str]

    class Config:
        from_attributes = True


class AddQuestionsRequest(BaseModel):
    question_ids: List[int] = Field(..., description="List of question IDs to add")
    added_by: Optional[str] = Field(None, description="Optional username")


class RemoveQuestionsRequest(BaseModel):
    question_ids: List[int] = Field(..., description="List of question IDs to remove")


class QuestionResponse(BaseModel):
    id: int
    stack_overflow_id: int
    title: str
    tags: Optional[str]
    score: int
    view_count: int
    is_answered: bool
    creation_date: Optional[str]

    class Config:
        from_attributes = True


class PaginatedQuestionsResponse(BaseModel):
    questions: List[QuestionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CollectionStatisticsResponse(BaseModel):
    collection_id: int
    name: str
    description: Optional[str]
    question_count: int
    created_at: Optional[str]
    last_rebuilt_at: Optional[str]
    avg_score: float
    avg_views: float
    rebuild_error: Optional[str] = None


class AddDocumentsRequest(BaseModel):
    document_paths: List[str] = Field(..., description="List of document paths to add")
    added_by: Optional[str] = Field(None, description="Optional username")


class RemoveDocumentsRequest(BaseModel):
    document_ids: List[int] = Field(..., description="List of document IDs to remove")


class DocumentResponse(BaseModel):
    id: int
    document_path: str
    document_name: str
    document_hash: Optional[str]
    added_at: str
    added_by: Optional[str]

    class Config:
        from_attributes = True


class PaginatedDocumentsResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AvailablePDFResponse(BaseModel):
    path: str
    name: str
    size: int
    modified: str