"""
Unit tests for CollectionManager service.

Tests the core functionality:
- Collection CRUD operations
- Adding/removing questions to collections
- Adding PDF documents to collections
"""
import pytest
from datetime import datetime

from app.services.collection_manager import CollectionManager
from app.database import CollectionConfiguration, CollectionQuestion, CollectionDocument


class TestCollectionCRUD:
    """Tests for Collection Create, Read, Update, Delete operations."""

    def test_create_collection(self, db_session):
        """
        Test creating a new collection with valid parameters.

        Assume:
            - Database session is available
            - No collection with name "SQL Basics" exists

        Expect:
            - Collection is created with an auto-generated ID
            - Collection name matches input
            - Collection type matches input
        """
        manager = CollectionManager(db=db_session)

        collection = manager.create_collection(
            name="SQL Basics",
            description="SQL concepts",
            collection_type="stackoverflow"
        )

        assert collection.id is not None
        assert collection.name == "SQL Basics"
        assert collection.collection_type == "stackoverflow"

    def test_duplicate_name_raises_error(self, db_session):
        """
        Test that creating a collection with a duplicate name raises ValueError.

        Assume:
            - A collection named "SQL Basics" already exists

        Expect:
            - ValueError is raised
            - Error message contains "already exists"
        """
        manager = CollectionManager(db=db_session)
        manager.create_collection(name="SQL Basics")

        with pytest.raises(ValueError) as excinfo:
            manager.create_collection(name="SQL Basics")

        assert "already exists" in str(excinfo.value)

    def test_get_collection(self, db_session):
        """
        Test retrieving a collection by ID.

        Assume:
            - A collection has been created and its ID is known

        Expect:
            - Retrieved collection has the same ID
            - Retrieved collection has the same name
        """
        manager = CollectionManager(db=db_session)
        created = manager.create_collection(name="Test")

        retrieved = manager.get_collection(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == "Test"

    def test_get_nonexistent_returns_none(self, db_session):
        """
        Test that retrieving a non-existent collection returns None.

        Assume:
            - No collection with ID 99999 exists

        Expect:
            - get_collection returns None
        """
        manager = CollectionManager(db=db_session)
        assert manager.get_collection(99999) is None

    def test_delete_collection(self, db_session):
        """
        Test deleting a collection.

        Assume:
            - A collection exists and its ID is known

        Expect:
            - delete_collection returns True
            - Collection is no longer retrievable
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="To Delete")

        result = manager.delete_collection(collection.id)

        assert result is True
        assert manager.get_collection(collection.id) is None


class TestQuestionManagement:
    """Tests for adding and removing questions from collections."""

    def test_add_questions(self, db_session, sample_questions):
        """
        Test adding questions to a collection.

        Assume:
            - A StackOverflow collection exists
            - Sample questions are available in database

        Expect:
            - add_questions_to_collection returns count of added questions
            - Collection's question_count is updated
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="SQL Collection")
        question_ids = [q.stack_overflow_id for q in sample_questions[:3]]

        count = manager.add_questions_to_collection(
            collection_id=collection.id,
            question_ids=question_ids
        )

        assert count == 3
        db_session.refresh(collection)
        assert collection.question_count == 3

    def test_add_duplicate_questions_skipped(self, db_session, sample_questions):
        """
        Test that duplicate questions are skipped when adding.

        Assume:
            - A collection with 2 questions exists
            - Trying to add 2 questions where one is already in collection

        Expect:
            - Only the new question is added (count = 1)
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="SQL Collection")
        question_ids = [sample_questions[0].stack_overflow_id, sample_questions[1].stack_overflow_id]

        manager.add_questions_to_collection(collection.id, question_ids)
        count = manager.add_questions_to_collection(
            collection.id,
            [sample_questions[0].stack_overflow_id, sample_questions[2].stack_overflow_id]
        )

        assert count == 1

    def test_remove_questions(self, db_session, sample_questions):
        """
        Test removing questions from a collection.

        Assume:
            - A collection with 4 questions exists

        Expect:
            - remove_questions_from_collection returns count of removed questions
            - Collection's question_count is reduced accordingly
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="SQL Collection")
        question_ids = [q.stack_overflow_id for q in sample_questions[:4]]
        manager.add_questions_to_collection(collection.id, question_ids)

        count = manager.remove_questions_from_collection(
            collection.id,
            [sample_questions[0].stack_overflow_id, sample_questions[1].stack_overflow_id]
        )

        assert count == 2
        db_session.refresh(collection)
        assert collection.question_count == 2


class TestDocumentManagement:
    """Tests for PDF document management in collections."""

    def test_add_documents_to_pdf_collection(self, db_session):
        """
        Test adding documents to a PDF-type collection.

        Assume:
            - A PDF-type collection exists

        Expect:
            - add_documents_to_collection returns count of added documents
            - Collection's question_count reflects added documents
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="SQL Docs", collection_type="pdf")

        count = manager.add_documents_to_collection(
            collection_id=collection.id,
            document_paths=["doc1.pdf", "doc2.pdf"]
        )

        assert count == 2
        db_session.refresh(collection)
        assert collection.question_count == 2

    def test_add_documents_to_stackoverflow_raises_error(self, db_session):
        """
        Test that adding documents to a StackOverflow collection raises ValueError.

        Assume:
            - A StackOverflow-type collection exists

        Expect:
            - ValueError is raised
            - Error message contains "not a PDF collection"
        """
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(
            name="SQL Questions",
            collection_type="stackoverflow"
        )

        with pytest.raises(ValueError) as excinfo:
            manager.add_documents_to_collection(collection.id, ["test.pdf"])

        assert "not a PDF collection" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
