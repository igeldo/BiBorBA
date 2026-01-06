"""
Shared pytest fixtures for testing
"""
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import shutil
import tempfile
from datetime import datetime

from app.database import Base, SOQuestion, SOAnswer, CollectionConfiguration
from app.services.collection_manager import CollectionManager

# Import app for test client
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing"""
    from sqlalchemy import event

    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key constraints for SQLite
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

    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up override
    app.dependency_overrides.clear()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_questions(db_session):
    """Create sample StackOverflow questions with answers

    Hinweis: SOQuestion hat keinen 'id' Feld - der Primärschlüssel ist 'stack_overflow_id'
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

        # Antworten erstellen
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

    # Refresh für Relationships
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

    # Create PDF with content
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica", 12)

    # Add content about SQL JOINs
    c.drawString(100, 750, "SQL JOIN Documentation")
    c.drawString(100, 700, "A JOIN clause is used to combine rows from two or more tables,")
    c.drawString(100, 680, "based on a related column between them.")
    c.drawString(100, 650, "Types of JOINs:")
    c.drawString(120, 630, "- INNER JOIN: Returns matching rows")
    c.drawString(120, 610, "- LEFT JOIN: Returns all rows from left table")
    c.drawString(120, 590, "- RIGHT JOIN: Returns all rows from right table")
    c.drawString(120, 570, "- FULL OUTER JOIN: Returns all rows from both tables")

    c.save()

    # Copy to resources/documents directory
    resources_dir = Path(__file__).parent.parent / "resources" / "documents"
    resources_dir.mkdir(parents=True, exist_ok=True)
    target = resources_dir / pdf_path.name
    shutil.copy(pdf_path, target)

    yield pdf_path

    # Cleanup
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

        # Copy to resources
        target = resources_dir / pdf_path.name
        shutil.copy(pdf_path, target)
        files.append(pdf_path)

    yield files

    # Cleanup
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

    # Use ephemeral client for tests (in-memory)
    client = chromadb.EphemeralClient()
    yield client

    # Cleanup happens automatically with ephemeral client


@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Temporary directory for ChromaDB persistence during tests"""
    chroma_dir = tmp_path / "chroma_test"
    chroma_dir.mkdir()
    yield chroma_dir
    # Cleanup happens automatically via tmp_path


# =============================================================================
# Settings Override Fixtures
# =============================================================================

@pytest.fixture
def test_settings(tmp_path):
    """Override settings for testing"""
    from app.config import settings

    # Store original values
    original_pdf_path = settings.pdf_path
    original_chroma_dir = settings.chroma_persist_dir

    # Set test paths
    test_resources = tmp_path / "resources" / "documents"
    test_resources.mkdir(parents=True, exist_ok=True)
    settings.pdf_path = test_resources

    test_chroma = tmp_path / "chroma"
    test_chroma.mkdir()
    settings.chroma_persist_dir = test_chroma

    yield settings

    # Restore original values
    settings.pdf_path = original_pdf_path
    settings.chroma_persist_dir = original_chroma_dir


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Auto-cleanup after each test"""
    yield
    # Any global cleanup needed after each test
    pass
