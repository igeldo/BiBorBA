# app/api/routes/collection_management.py
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.schemas.collection_schemas import CollectionResponse, CreateCollectionRequest, AddQuestionsRequest, \
    RemoveQuestionsRequest, PaginatedQuestionsResponse, QuestionResponse, CollectionStatisticsResponse, \
    AvailablePDFResponse, AddDocumentsRequest, RemoveDocumentsRequest, PaginatedDocumentsResponse, DocumentResponse
from app.api.schemas.schemas import SortField, SortOrder
from app.config import settings
from app.core.graph.tools.vector_store import rebuild_custom_collection
from app.database import get_db
from app.dependencies import get_collection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection-management", tags=["collection-management"])


@router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    request: CreateCollectionRequest,
    manager=Depends(get_collection_manager)
):
    """Create a new collection"""
    try:
        collection = manager.create_collection(
            name=request.name,
            description=request.description,
            collection_type=request.collection_type
        )

        return CollectionResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            collection_type=collection.collection_type,
            question_count=collection.question_count,
            created_at=collection.created_at.isoformat() if collection.created_at else datetime.utcnow().isoformat(),
            last_rebuilt_at=collection.last_rebuilt_at.isoformat() if collection.last_rebuilt_at else None
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to create collection")


@router.get("/collections", response_model=List[CollectionResponse])
async def get_collections(manager=Depends(get_collection_manager)):
    """Get all collections"""
    try:
        collections = manager.get_collections()

        return [
            CollectionResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                collection_type=c.collection_type,
                question_count=c.question_count,
                created_at=c.created_at.isoformat() if c.created_at else datetime.utcnow().isoformat(),
                last_rebuilt_at=c.last_rebuilt_at.isoformat() if c.last_rebuilt_at else None
            )
            for c in collections
        ]

    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collections")


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: int, manager=Depends(get_collection_manager)):
    """Get a specific collection"""
    try:
        collection = manager.get_collection(collection_id)

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return CollectionResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            collection_type=collection.collection_type,
            question_count=collection.question_count,
            created_at=collection.created_at.isoformat() if collection.created_at else datetime.utcnow().isoformat(),
            last_rebuilt_at=collection.last_rebuilt_at.isoformat() if collection.last_rebuilt_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collection")


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: int, manager=Depends(get_collection_manager)):
    """Delete a collection"""
    try:
        deleted = manager.delete_collection(collection_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"message": "Collection deleted successfully", "collection_id": collection_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete collection")


# Question assignment endpoints

@router.post("/collections/{collection_id}/questions")
async def add_questions_to_collection(
    collection_id: int,
    request: AddQuestionsRequest,
    manager=Depends(get_collection_manager)
):
    """Add questions to a collection"""
    try:
        count_added = manager.add_questions_to_collection(
            collection_id=collection_id,
            question_ids=request.question_ids,
            added_by=request.added_by
        )

        return {
            "message": f"Added {count_added} questions to collection",
            "collection_id": collection_id,
            "questions_added": count_added,
            "questions_requested": len(request.question_ids)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding questions to collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to add questions")


@router.delete("/collections/{collection_id}/questions")
async def remove_questions_from_collection(
    collection_id: int,
    request: RemoveQuestionsRequest,
    manager=Depends(get_collection_manager)
):
    """Remove questions from a collection"""
    try:
        count_removed = manager.remove_questions_from_collection(
            collection_id=collection_id,
            question_ids=request.question_ids
        )

        return {
            "message": f"Removed {count_removed} questions from collection",
            "collection_id": collection_id,
            "questions_removed": count_removed
        }

    except Exception as e:
        logger.error(f"Error removing questions from collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove questions")


@router.get("/collections/{collection_id}/questions", response_model=PaginatedQuestionsResponse)
async def get_collection_questions(
    collection_id: int,
    page: int = 1,
    page_size: int = 50,
    min_score: Optional[int] = None,
    tags: Optional[str] = None,
    sort_by: SortField = SortField.CREATION_DATE,
    sort_order: SortOrder = SortOrder.DESC,
    manager=Depends(get_collection_manager)
):
    """Get questions in a collection (paginated)"""
    try:

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        result = manager.get_collection_questions(
            collection_id=collection_id,
            page=page,
            page_size=page_size,
            min_score=min_score,
            tags=tag_list,
            sort_by=sort_by.value,
            sort_order=sort_order.value
        )

        questions = [
            QuestionResponse(
                id=q.stack_overflow_id,
                stack_overflow_id=q.stack_overflow_id,
                title=q.title,
                tags=q.tags,
                score=q.score,
                view_count=q.view_count,
                is_answered=q.is_answered,
                creation_date=q.creation_date.isoformat() if q.creation_date else None
            )
            for q in result["questions"]
        ]

        return PaginatedQuestionsResponse(
            questions=questions,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        logger.error(f"Error getting collection questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collection questions")


@router.get("/collections/{collection_id}/test-questions", response_model=PaginatedQuestionsResponse)
async def get_test_questions(
    collection_id: int,
    page: int = 1,
    page_size: int = 50,
    min_score: Optional[int] = None,
    tags: Optional[str] = None,
    sort_by: SortField = SortField.CREATION_DATE,
    sort_order: SortOrder = SortOrder.DESC,
    manager=Depends(get_collection_manager)
):
    """Get questions NOT in collection (test set candidates)"""
    try:

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        result = manager.get_non_collection_questions(
            collection_id=collection_id,
            page=page,
            page_size=page_size,
            min_score=min_score,
            tags=tag_list,
            sort_by=sort_by.value,
            sort_order=sort_order.value
        )

        questions = [
            QuestionResponse(
                id=q.stack_overflow_id,
                stack_overflow_id=q.stack_overflow_id,
                title=q.title,
                tags=q.tags,
                score=q.score,
                view_count=q.view_count,
                is_answered=q.is_answered,
                creation_date=q.creation_date.isoformat() if q.creation_date else None
            )
            for q in result["questions"]
        ]

        return PaginatedQuestionsResponse(
            questions=questions,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        logger.error(f"Error getting test questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test questions")


@router.get("/collections/{collection_id}/statistics", response_model=CollectionStatisticsResponse)
async def get_collection_statistics(
    collection_id: int,
    db: Session = Depends(get_db),
    manager=Depends(get_collection_manager)
):
    """Get statistics for a collection including health status"""
    try:
        from app.dependencies import get_collection_health_service

        stats = manager.get_collection_statistics(collection_id)

        # Health Check hinzufügen
        health_service = get_collection_health_service()
        health = health_service.check_collection_health(collection_id, db)

        # Kombiniere Stats + Health
        combined_stats = {
            **stats,
            "chroma_exists": health["exists"],
            "needs_rebuild": health["needs_rebuild"],
            "chroma_document_count": health.get("document_count", 0),
        }

        return CollectionStatisticsResponse(**combined_stats)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting collection statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/collections/health")
async def check_all_collections_health(db: Session = Depends(get_db)):
    """Check health of all collections"""
    try:
        from app.dependencies import get_collection_health_service
        from app.database import CollectionConfiguration

        health_service = get_collection_health_service()
        summary = health_service.check_all_collections(db)

        # Liste aller Collections mit Status
        collections = db.query(CollectionConfiguration).all()
        details = [
            {
                "id": c.id,
                "name": c.name,
                "chroma_exists": c.chroma_exists,
                "needs_rebuild": c.needs_rebuild,
                "last_health_check": c.last_health_check.isoformat() if c.last_health_check else None
            }
            for c in collections
        ]

        return {
            "summary": summary,
            "collections": details
        }

    except Exception as e:
        logger.error(f"Error checking collection health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check collection health")


@router.post("/collections/{collection_id}/rebuild")
async def rebuild_collection(
    collection_id: int,
    background_tasks: BackgroundTasks,
    manager=Depends(get_collection_manager)
):
    """
    Rebuild ChromaDB collection for a custom collection

    This rebuilds the vector store with the current questions in the collection.
    Returns a job_id for tracking progress.
    """
    from app.services.job_manager import get_rebuild_manager

    try:
        # Verify collection exists
        collection = manager.get_collection(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Create job for tracking progress
        job_manager = get_rebuild_manager()
        job_id = job_manager.create_job(
            parameters={
                "collection_id": collection_id,
                "collection_name": collection.name
            },
            progress_fields={
                "total_documents": 0,
                "processed_documents": 0,
                "current_batch": 0,
                "total_batches": 0,
                "phase": "starting"
            }
        )

        # Rebuild in background
        def rebuild_task():
            # Create new session for background task (original db session may be closed)
            from app.database import SessionLocal
            from app.services.collection_manager import CollectionManager

            bg_db = SessionLocal()
            bg_manager = CollectionManager(db=bg_db)

            def progress_callback(progress: dict):
                """Update job progress during rebuild"""
                job_manager.update_progress(job_id, progress)

            try:
                # Clear any previous error
                bg_manager.clear_rebuild_error(collection_id)

                # Update phase to loading
                job_manager.update_progress(job_id, {"phase": "loading_documents"})

                # Perform rebuild with progress callback
                stats = rebuild_custom_collection(collection_id, progress_callback=progress_callback)

                # Update timestamp AFTER successful rebuild
                bg_manager.update_collection_rebuild_time(collection_id)

                # Mark job as completed
                job_manager.update_progress(job_id, {"phase": "completed"})
                job_manager.complete_job(job_id)

                logger.info(f"Background rebuild completed: {stats}")
            except Exception as e:
                # Set error so frontend can display it
                bg_manager.set_rebuild_error(collection_id, str(e))
                job_manager.fail_job(job_id, str(e))
                logger.error(f"Background rebuild failed: {e}")
            finally:
                bg_db.close()

        background_tasks.add_task(rebuild_task)

        return {
            "message": "Collection rebuild started",
            "job_id": job_id,
            "collection_id": collection_id,
            "collection_name": collection.name,
            "question_count": collection.question_count,
            "status": "rebuilding"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rebuilding collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to rebuild collection")


@router.get("/rebuild-jobs/{job_id}")
async def get_rebuild_job_status(job_id: str):
    """
    Get status of a rebuild job.
    Poll this endpoint to track rebuild progress.
    """
    from app.services.job_manager import get_rebuild_manager, JobStatus

    job_manager = get_rebuild_manager()
    job_data = job_manager.get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_data["job_id"],
        "status": job_data["status"].value if isinstance(job_data["status"], JobStatus) else job_data["status"],
        "progress": job_data["progress"],
        "parameters": job_data["parameters"],
        "started_at": job_data["started_at"],
        "completed_at": job_data.get("completed_at"),
        "error": job_data.get("error")
    }


# PDF Document Management Endpoints

@router.get("/available-pdfs", response_model=List[AvailablePDFResponse])
async def get_available_pdfs():
    """Get list of available PDF files from resources/documents directory"""
    try:
        pdf_dir = Path(settings.pdf_path)

        if not pdf_dir.exists():
            logger.warning(f"PDF directory does not exist: {pdf_dir}")
            return []

        available_pdfs = []

        # List all PDF files
        for pdf_file in pdf_dir.rglob("*.pdf"):
            try:
                relative_path = pdf_file.relative_to(pdf_dir)
                stat = pdf_file.stat()

                available_pdfs.append(AvailablePDFResponse(
                    path=str(relative_path),
                    name=pdf_file.name,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))
            except Exception as e:
                logger.warning(f"Error reading PDF file {pdf_file}: {e}")
                continue

        # Sort by name
        available_pdfs.sort(key=lambda x: x.name)

        logger.info(f"Found {len(available_pdfs)} available PDFs")
        return available_pdfs

    except Exception as e:
        logger.error(f"Error getting available PDFs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available PDFs")


@router.post("/collections/{collection_id}/documents")
async def add_documents_to_collection(
    collection_id: int,
    request: AddDocumentsRequest,
    manager=Depends(get_collection_manager)
):
    """Add PDF documents to a collection"""
    try:
        count_added = manager.add_documents_to_collection(
            collection_id=collection_id,
            document_paths=request.document_paths,
            added_by=request.added_by
        )

        return {
            "message": f"Added {count_added} documents to collection",
            "collection_id": collection_id,
            "documents_added": count_added,
            "documents_requested": len(request.document_paths)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding documents to collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to add documents")


@router.delete("/collections/{collection_id}/documents")
async def remove_documents_from_collection(
    collection_id: int,
    request: RemoveDocumentsRequest,
    manager=Depends(get_collection_manager)
):
    """Remove documents from a collection"""
    try:
        count_removed = manager.remove_documents_from_collection(
            collection_id=collection_id,
            document_ids=request.document_ids
        )

        return {
            "message": f"Removed {count_removed} documents from collection",
            "collection_id": collection_id,
            "documents_removed": count_removed
        }

    except Exception as e:
        logger.error(f"Error removing documents from collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove documents")


@router.get("/collections/{collection_id}/documents", response_model=PaginatedDocumentsResponse)
async def get_collection_documents(
    collection_id: int,
    page: int = 1,
    page_size: int = 50,
    manager=Depends(get_collection_manager)
):
    """Get documents in a PDF collection (paginated)"""
    try:
        result = manager.get_collection_documents(
            collection_id=collection_id,
            page=page,
            page_size=page_size
        )

        documents = [
            DocumentResponse(
                id=d.id,
                document_path=d.document_path,
                document_name=d.document_name,
                document_hash=d.document_hash,
                added_at=d.added_at.isoformat() if d.added_at else datetime.utcnow().isoformat(),
                added_by=d.added_by
            )
            for d in result["documents"]
        ]

        return PaginatedDocumentsResponse(
            documents=documents,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        logger.error(f"Error getting collection documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collection documents")
