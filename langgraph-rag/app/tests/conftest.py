"""
Shared pytest fixtures for testing
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, SOQuestion, SOAnswer
from app.services.collection_manager import CollectionManager

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing"""
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a database session for tests with automatic rollback"""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# API Client Fixture
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with database override"""
    from app.main import app
    from app.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_questions(db_session):
    """Create sample StackOverflow questions with answers

    Note: SOQuestion has no 'id' field - the primary key is 'stack_overflow_id'
    """
    questions = []

    for i in range(5):
        so_id = 1000 + i
        q = SOQuestion(
            stack_overflow_id=so_id,
            title=f"How to use SQL JOIN {i}?",
            body=f"I want to learn about SQL JOINs. Question body {i}.",
            tags="sql,join,database",
            score=10 + i,
            view_count=100 * (i + 1),
            is_answered=True,
            creation_date=datetime(2024, 1, i + 1),
            owner_display_name=f"User{i}"
        )
        db_session.add(q)

        for j in range(2):
            a = SOAnswer(
                stack_overflow_id=2000 + (i * 10) + j,
                question_stack_overflow_id=so_id,  # FK zu SOQuestion.stack_overflow_id
                body=f"Answer {j} for question {i}",
                score=5 + j,
                is_accepted=(j == 0),
                creation_date=datetime(2024, 1, i + 1),
                owner_display_name=f"AnswerUser{j}"
            )
            db_session.add(a)

        questions.append(q)

    db_session.commit()

    for q in questions:
        db_session.refresh(q)

    return questions


@pytest.fixture
def collection_manager(db_session):
    """Provide a CollectionManager instance"""
    return CollectionManager(db_session)


# =============================================================================
# PDF File Fixtures
# =============================================================================

@pytest.fixture
def test_pdf_file(tmp_path):
    """Create a test PDF file with actual content"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        pytest.skip("reportlab not installed")

    pdf_path = tmp_path / "test_document.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(100, 750, "SQL JOIN Documentation")
    c.drawString(100, 700, "A JOIN clause is used to combine rows from two or more tables,")
    c.drawString(100, 680, "based on a related column between them.")
    c.drawString(100, 650, "Types of JOINs:")
    c.drawString(120, 630, "- INNER JOIN: Returns matching rows")
    c.drawString(120, 610, "- LEFT JOIN: Returns all rows from left table")
    c.drawString(120, 590, "- RIGHT JOIN: Returns all rows from right table")
    c.drawString(120, 570, "- FULL OUTER JOIN: Returns all rows from both tables")

    c.save()

    resources_dir = Path(__file__).parent.parent / "resources" / "documents"
    resources_dir.mkdir(parents=True, exist_ok=True)
    target = resources_dir / pdf_path.name
    shutil.copy(pdf_path, target)

    yield pdf_path

    if target.exists():
        target.unlink()


@pytest.fixture
def test_pdf_files(tmp_path):
    """Create multiple test PDF files"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        pytest.skip("reportlab not installed")

    files = []
    resources_dir = Path(__file__).parent.parent / "resources" / "documents"
    resources_dir.mkdir(parents=True, exist_ok=True)

    for i in range(3):
        pdf_path = tmp_path / f"test_doc_{i}.pdf"

        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, f"SQL Document {i}")
        c.drawString(100, 700, f"This is test document number {i}")
        c.drawString(100, 680, f"Content about SQL topic {i}")
        c.save()

        target = resources_dir / pdf_path.name
        shutil.copy(pdf_path, target)
        files.append(pdf_path)

    yield files

    for f in files:
        target = resources_dir / f.name
        if target.exists():
            target.unlink()


# =============================================================================
# Vector Store Fixtures
# =============================================================================

@pytest.fixture
def chroma_client():
    """ChromaDB client for testing (ephemeral)"""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        pytest.skip("chromadb not installed")

    client = chromadb.EphemeralClient()
    yield client



@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Temporary directory for ChromaDB persistence during tests"""
    chroma_dir = tmp_path / "chroma_test"
    chroma_dir.mkdir()
    yield chroma_dir


# =============================================================================
# Settings Override Fixtures
# =============================================================================

@pytest.fixture
def test_settings(tmp_path):
    """Override settings for testing"""
    from app.config import settings

    original_pdf_path = settings.pdf_path
    original_chroma_dir = settings.chroma_persist_dir

    test_resources = tmp_path / "resources" / "documents"
    test_resources.mkdir(parents=True, exist_ok=True)
    settings.pdf_path = test_resources

    test_chroma = tmp_path / "chroma"
    test_chroma.mkdir()
    settings.chroma_persist_dir = test_chroma

    yield settings

    settings.pdf_path = original_pdf_path
    settings.chroma_persist_dir = original_chroma_dir



# =============================================================================
# Graph Node Test Fixtures
# =============================================================================

@pytest.fixture
def mock_model_manager():
    """Mocked ModelManager for graph node tests"""
    from unittest.mock import MagicMock
    manager = MagicMock()
    manager.get_chat_model.return_value = MagicMock()
    manager.get_structured_model.return_value = MagicMock()
    return manager


@pytest.fixture
def mock_prompt_manager():
    """Mocked PromptManager for graph node tests"""
    from unittest.mock import MagicMock
    manager = MagicMock()
    manager.get_document_grader_prompt.return_value = MagicMock()
    manager.get_hallucination_grader_prompt.return_value = MagicMock()
    manager.get_answer_generator_prompt.return_value = MagicMock()
    manager.get_question_rewriter_prompt.return_value = MagicMock()
    manager.get_answer_grader_prompt.return_value = MagicMock()
    manager.get_pure_llm_prompt.return_value = MagicMock()
    return manager


@pytest.fixture
def sample_graph_state():
    """Sample GraphState for tests"""
    return {
        "question": "What is SQL JOIN?",
        "original_question": "What is SQL JOIN?",
        "generation": "",
        "documents": [],
        "model_config": {},
        "collection_ids": [],
        "generation_attempts": 0,
        "transform_attempts": 0,
        "total_iterations": 0,
        "max_iterations_reached": False,
        "no_relevant_docs_fallback": False,
        "fallback_type": ""
    }


@pytest.fixture
def sample_documents():
    """Create sample Document objects for tests"""
    from langchain_core.documents import Document

    return [
        Document(
            page_content="SQL JOIN is used to combine rows from two or more tables based on a related column.",
            metadata={"source": "test_doc_1.pdf", "page": 1}
        ),
        Document(
            page_content="INNER JOIN returns rows that have matching values in both tables.",
            metadata={"source": "test_doc_2.pdf", "page": 1}
        ),
        Document(
            page_content="LEFT JOIN returns all rows from the left table with matching rows from the right table.",
            metadata={"source": "test_doc_3.pdf", "page": 2}
        )
    ]
