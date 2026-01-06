"""
Tests für CollectionManager

Testet Kernfunktionalität:
- Collection CRUD
- Fragen zu Collection hinzufügen/entfernen
- PDF-Dokumente zu Collection hinzufügen
"""
import pytest
from datetime import datetime

from app.services.collection_manager import CollectionManager
from app.database import CollectionConfiguration, CollectionQuestion, CollectionDocument


class TestCollectionCRUD:
    """Test Collection CRUD"""

    def test_create_collection(self, db_session):
        """Collection erstellen"""
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
        """Doppelter Name wirft ValueError"""
        manager = CollectionManager(db=db_session)
        manager.create_collection(name="SQL Basics")

        with pytest.raises(ValueError) as excinfo:
            manager.create_collection(name="SQL Basics")

        assert "already exists" in str(excinfo.value)

    def test_get_collection(self, db_session):
        """Collection abrufen"""
        manager = CollectionManager(db=db_session)
        created = manager.create_collection(name="Test")

        retrieved = manager.get_collection(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == "Test"

    def test_get_nonexistent_returns_none(self, db_session):
        """Nicht existierende Collection -> None"""
        manager = CollectionManager(db=db_session)
        assert manager.get_collection(99999) is None

    def test_delete_collection(self, db_session):
        """Collection löschen"""
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="To Delete")

        result = manager.delete_collection(collection.id)

        assert result is True
        assert manager.get_collection(collection.id) is None


class TestQuestionManagement:
    """Test Fragen-Verwaltung"""

    def test_add_questions(self, db_session, sample_questions):
        """Fragen zu Collection hinzufügen"""
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
        """Duplikate werden übersprungen"""
        manager = CollectionManager(db=db_session)
        collection = manager.create_collection(name="SQL Collection")
        question_ids = [sample_questions[0].stack_overflow_id, sample_questions[1].stack_overflow_id]

        manager.add_questions_to_collection(collection.id, question_ids)
        count = manager.add_questions_to_collection(
            collection.id,
            [sample_questions[0].stack_overflow_id, sample_questions[2].stack_overflow_id]  # 0 ist Duplikat
        )

        assert count == 1  # Nur 1 neu

    def test_remove_questions(self, db_session, sample_questions):
        """Fragen entfernen"""
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
    """Test PDF-Dokument-Verwaltung"""

    def test_add_documents_to_pdf_collection(self, db_session):
        """Dokumente zu PDF-Collection hinzufügen"""
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
        """Dokumente zu StackOverflow-Collection -> ValueError"""
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
