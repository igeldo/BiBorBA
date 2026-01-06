# app/services/collection_manager.py
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

from app.database import (
    CollectionConfiguration,
    CollectionQuestion,
    CollectionDocument,
    SOQuestion,
)

logger = logging.getLogger(__name__)


class CollectionManager:
    """Service for managing custom collections of StackOverflow questions"""

    def __init__(self, db: Session):
        """
        Initialize CollectionManager

        Args:
            db: SQLAlchemy database session (injected via DI)
        """
        self.db = db

    # Collection CRUD operations

    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        collection_type: str = "stackoverflow"
    ) -> CollectionConfiguration:
        """
        Create a new collection

        Args:
            name: Unique name for the collection
            description: Optional description
            collection_type: Type of collection (default: stackoverflow)

        Returns:
            Created CollectionConfiguration

        Raises:
            ValueError: If collection with name already exists
        """
        try:
            existing = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.name == name
            ).first()

            if existing:
                raise ValueError(f"Collection with name '{name}' already exists")

            collection = CollectionConfiguration(
                name=name,
                description=description,
                collection_type=collection_type,
                question_count=0
            )

            self.db.add(collection)
            self.db.commit()

            collection_id = collection.id
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            logger.info(f"Created collection: {name} (ID: {collection.id})")
            return collection

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating collection: {e}")
            raise

    def get_collections(self) -> List[CollectionConfiguration]:
        """
        Get all collections

        Returns:
            List of all CollectionConfiguration objects
        """
        collections = self.db.query(CollectionConfiguration).order_by(
            CollectionConfiguration.created_at.desc()
        ).all()
        return collections

    def get_collection(self, collection_id: int) -> Optional[CollectionConfiguration]:
        """
        Get a specific collection by ID

        Args:
            collection_id: ID of the collection

        Returns:
            CollectionConfiguration or None if not found
        """
        collection = self.db.query(CollectionConfiguration).filter(
            CollectionConfiguration.id == collection_id
        ).first()
        return collection

    def delete_collection(self, collection_id: int) -> bool:
        """
        Delete a collection

        Args:
            collection_id: ID of the collection to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if not collection:
                return False

            self.db.delete(collection)
            self.db.commit()

            logger.info(f"Deleted collection ID: {collection_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting collection: {e}")
            raise

    # Question assignment operations

    def add_questions_to_collection(
        self,
        collection_id: int,
        question_ids: List[int],
        added_by: Optional[str] = None
    ) -> int:
        """
        Add questions to a collection

        Args:
            collection_id: ID of the collection
            question_ids: List of question IDs to add
            added_by: Optional username who added the questions

        Returns:
            Number of questions added (excluding duplicates)
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if not collection:
                raise ValueError(f"Collection with ID {collection_id} not found")

            existing_ids = set(
                self.db.query(CollectionQuestion.question_stack_overflow_id).filter(
                    CollectionQuestion.collection_id == collection_id
                ).all()
            )
            existing_ids = {q_id for (q_id,) in existing_ids}

            valid_question_ids = self.db.query(SOQuestion.stack_overflow_id).filter(
                SOQuestion.stack_overflow_id.in_(question_ids)
            ).all()
            valid_question_ids = {q_id for (q_id,) in valid_question_ids}

            new_questions = valid_question_ids - existing_ids
            count_added = 0

            for question_id in new_questions:
                collection_question = CollectionQuestion(
                    collection_id=collection_id,
                    question_stack_overflow_id=question_id,
                    added_by=added_by
                )
                self.db.add(collection_question)
                count_added += 1

            collection.question_count = self.db.query(CollectionQuestion).filter(
                CollectionQuestion.collection_id == collection_id
            ).count()

            self.db.commit()

            logger.info(
                f"Added {count_added} questions to collection {collection_id} "
                f"({len(question_ids) - count_added} duplicates skipped)"
            )

            return count_added

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding questions to collection: {e}")
            raise

    def remove_questions_from_collection(
        self,
        collection_id: int,
        question_ids: List[int]
    ) -> int:
        """
        Remove questions from a collection

        Args:
            collection_id: ID of the collection
            question_ids: List of question IDs to remove

        Returns:
            Number of questions removed
        """
        try:
            count_removed = self.db.query(CollectionQuestion).filter(
                and_(
                    CollectionQuestion.collection_id == collection_id,
                    CollectionQuestion.question_stack_overflow_id.in_(question_ids)
                )
            ).delete(synchronize_session=False)

            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if collection:
                collection.question_count = self.db.query(CollectionQuestion).filter(
                    CollectionQuestion.collection_id == collection_id
                ).count()

            self.db.commit()

            logger.info(f"Removed {count_removed} questions from collection {collection_id}")
            return count_removed

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing questions from collection: {e}")
            raise

    # Query operations

    def get_collection_questions(
        self,
        collection_id: int,
        page: int = 1,
        page_size: int = 50,
        min_score: Optional[int] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "creation_date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get paginated questions in a collection

        Args:
            collection_id: ID of the collection
            page: Page number (1-indexed)
            page_size: Number of items per page
            min_score: Optional minimum score filter
            tags: Optional tags filter
            sort_by: Sort field (creation_date, score, view_count)
            sort_order: Sort order (asc, desc)

        Returns:
            Dict with questions, total count, and pagination info
        """
        query = self.db.query(SOQuestion).join(
            CollectionQuestion,
            SOQuestion.stack_overflow_id == CollectionQuestion.question_stack_overflow_id
        ).filter(
            CollectionQuestion.collection_id == collection_id
        )

        if min_score is not None:
            query = query.filter(SOQuestion.score >= min_score)

        if tags:
            tag_filters = [SOQuestion.tags.contains(tag) for tag in tags]
            query = query.filter(or_(*tag_filters))

        total = query.count()

        sort_column = getattr(SOQuestion, sort_by, SOQuestion.creation_date)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        questions = query.offset(offset).limit(page_size).all()

        return {
            "questions": questions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def get_non_collection_questions(
        self,
        collection_id: int,
        page: int = 1,
        page_size: int = 50,
        min_score: Optional[int] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "creation_date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get paginated questions NOT in a collection (test set candidates)

        Args:
            collection_id: ID of the collection to exclude
            page: Page number (1-indexed)
            page_size: Number of items per page
            min_score: Optional minimum score filter
            tags: Optional tags filter
            sort_by: Sort field
            sort_order: Sort order

        Returns:
            Dict with questions, total count, and pagination info
        """
        in_collection_subquery = self.db.query(CollectionQuestion.question_stack_overflow_id).filter(
            CollectionQuestion.collection_id == collection_id
        ).subquery()

        query = self.db.query(SOQuestion).filter(
            not_(SOQuestion.stack_overflow_id.in_(in_collection_subquery))
        )

        if min_score is not None:
            query = query.filter(SOQuestion.score >= min_score)

        if tags:
            tag_filters = [SOQuestion.tags.contains(tag) for tag in tags]
            query = query.filter(or_(*tag_filters))

        total = query.count()

        sort_column = getattr(SOQuestion, sort_by, SOQuestion.creation_date)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        questions = query.offset(offset).limit(page_size).all()

        return {
            "questions": questions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def get_collection_question_ids(self, collection_id: int) -> List[int]:
        """
        Get all question IDs in a collection

        Args:
            collection_id: ID of the collection

        Returns:
            List of question IDs
        """
        question_ids = self.db.query(CollectionQuestion.question_stack_overflow_id).filter(
            CollectionQuestion.collection_id == collection_id
        ).all()

        return [q_id for (q_id,) in question_ids]

    def update_collection_rebuild_time(self, collection_id: int):
        """
        Update the last_rebuilt_at timestamp for a collection

        Args:
            collection_id: ID of the collection
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if collection:
                collection.last_rebuilt_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Updated rebuild time for collection {collection_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating collection rebuild time: {e}")
            raise

    def set_rebuild_error(self, collection_id: int, error: str):
        """
        Set rebuild error for a collection (called when background rebuild fails)

        Args:
            collection_id: ID of the collection
            error: Error message
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if collection:
                collection.rebuild_error = error
                self.db.commit()
                logger.info(f"Set rebuild error for collection {collection_id}: {error}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting rebuild error: {e}")

    def clear_rebuild_error(self, collection_id: int):
        """
        Clear rebuild error for a collection (called when rebuild starts)

        Args:
            collection_id: ID of the collection
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if collection:
                collection.rebuild_error = None
                self.db.commit()
                logger.debug(f"Cleared rebuild error for collection {collection_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error clearing rebuild error: {e}")

    def get_collection_statistics(self, collection_id: int) -> Dict[str, Any]:
        """
        Get statistics for a collection

        Args:
            collection_id: ID of the collection

        Returns:
            Dict with various statistics
        """
        collection = self.db.query(CollectionConfiguration).filter(
            CollectionConfiguration.id == collection_id
        ).first()

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        from sqlalchemy import func
        stats = self.db.query(
            func.count(SOQuestion.stack_overflow_id).label('total_questions'),
            func.avg(SOQuestion.score).label('avg_score'),
            func.avg(SOQuestion.view_count).label('avg_views')
        ).join(
            CollectionQuestion,
            SOQuestion.stack_overflow_id == CollectionQuestion.question_stack_overflow_id
        ).filter(
            CollectionQuestion.collection_id == collection_id
        ).first()

        return {
            "collection_id": collection_id,
            "name": collection.name,
            "description": collection.description,
            "question_count": collection.question_count,
            "created_at": collection.created_at.isoformat() if collection.created_at else None,
            "last_rebuilt_at": collection.last_rebuilt_at.isoformat() if collection.last_rebuilt_at else None,
            "avg_score": round(stats.avg_score or 0, 2),
            "avg_views": round(stats.avg_views or 0, 2),
            "rebuild_error": collection.rebuild_error
        }

    # PDF Collection Operations

    def add_documents_to_collection(
        self,
        collection_id: int,
        document_paths: List[str],
        added_by: Optional[str] = None
    ) -> int:
        """
        Add PDF documents to a collection

        Args:
            collection_id: ID of the collection
            document_paths: List of document paths (relative to resources/documents)
            added_by: Optional username who added the documents

        Returns:
            Number of documents added (excluding duplicates)
        """
        try:
            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if not collection:
                raise ValueError(f"Collection with ID {collection_id} not found")

            if collection.collection_type != "pdf":
                raise ValueError(f"Collection is not a PDF collection (type: {collection.collection_type})")

            existing_paths = set(
                self.db.query(CollectionDocument.document_path).filter(
                    CollectionDocument.collection_id == collection_id
                ).all()
            )
            existing_paths = {path for (path,) in existing_paths}

            new_paths = set(document_paths) - existing_paths
            count_added = 0

            for doc_path in new_paths:
                import os
                document_name = os.path.basename(doc_path)

                import hashlib
                document_hash = hashlib.md5(doc_path.encode()).hexdigest()

                collection_doc = CollectionDocument(
                    collection_id=collection_id,
                    document_path=doc_path,
                    document_name=document_name,
                    document_hash=document_hash,
                    added_by=added_by
                )
                self.db.add(collection_doc)
                count_added += 1

            collection.question_count = self.db.query(CollectionDocument).filter(
                CollectionDocument.collection_id == collection_id
            ).count()

            self.db.commit()

            logger.info(
                f"Added {count_added} documents to PDF collection {collection_id} "
                f"({len(document_paths) - count_added} duplicates skipped)"
            )

            return count_added

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding documents to collection: {e}")
            raise

    def remove_documents_from_collection(
        self,
        collection_id: int,
        document_ids: List[int]
    ) -> int:
        """
        Remove PDF documents from a collection

        Args:
            collection_id: ID of the collection
            document_ids: List of document IDs to remove

        Returns:
            Number of documents removed
        """
        try:
            count_removed = self.db.query(CollectionDocument).filter(
                and_(
                    CollectionDocument.collection_id == collection_id,
                    CollectionDocument.id.in_(document_ids)
                )
            ).delete(synchronize_session=False)

            collection = self.db.query(CollectionConfiguration).filter(
                CollectionConfiguration.id == collection_id
            ).first()

            if collection:
                collection.question_count = self.db.query(CollectionDocument).filter(
                    CollectionDocument.collection_id == collection_id
                ).count()

            self.db.commit()

            logger.info(f"Removed {count_removed} documents from collection {collection_id}")
            return count_removed

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing documents from collection: {e}")
            raise

    def get_collection_documents(
        self,
        collection_id: int,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Get PDF documents in a collection (paginated)

        Args:
            collection_id: ID of the collection
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dict with documents, total count, and pagination info
        """
        query = self.db.query(CollectionDocument).filter(
            CollectionDocument.collection_id == collection_id
        )

        total = query.count()

        offset = (page - 1) * page_size
        documents = query.order_by(CollectionDocument.added_at.desc()).offset(offset).limit(page_size).all()

        return {
            "documents": documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
