"""
Unit tests for PDFDocumentLoader.

Tests the core functionality:
- Loading single PDF files
- Loading from directories
- Error handling for missing files and empty directories
- Metadata extraction
"""
import pytest
from pathlib import Path
from langchain_core.documents import Document

from app.core.graph.tools.document_loaders.pdf_loader import PDFDocumentLoader
from app.config import settings


class TestPDFLoader:
    """Tests for PDF document loading functionality."""

    def test_load_single_pdf(self, test_pdf_file, test_settings):
        """
        Test loading a single PDF file.

        Assume:
            - A valid test PDF file exists at the configured path

        Expect:
            - At least one document is returned
            - All returned items are Document objects
            - All documents have non-empty content
        """
        loader = PDFDocumentLoader()
        settings.pdf_path = test_pdf_file

        documents = loader.load_documents()

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.page_content.strip() for doc in documents)

    def test_load_pdf_directory(self, test_pdf_files, test_settings):
        """
        Test loading all PDF files from a directory.

        Assume:
            - A directory with multiple test PDF files exists

        Expect:
            - At least one document is returned
        """
        loader = PDFDocumentLoader()
        pdf_dir = test_pdf_files[0].parent
        settings.pdf_path = pdf_dir

        documents = loader.load_documents()

        assert len(documents) > 0

    def test_file_not_found_raises_error(self, tmp_path):
        """
        Test that loading a non-existent file raises FileNotFoundError.

        Assume:
            - pdf_path points to a file that does not exist

        Expect:
            - FileNotFoundError is raised
        """
        loader = PDFDocumentLoader()
        settings.pdf_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            loader.load_documents()

    def test_empty_directory_raises_error(self, tmp_path):
        """
        Test that loading from an empty directory raises FileNotFoundError.

        Assume:
            - pdf_path points to an empty directory

        Expect:
            - FileNotFoundError is raised
            - Error message contains "No PDF files found"
        """
        loader = PDFDocumentLoader()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        settings.pdf_path = empty_dir

        with pytest.raises(FileNotFoundError) as excinfo:
            loader.load_documents()

        assert "No PDF files found" in str(excinfo.value)

    def test_documents_have_metadata(self, test_pdf_file, test_settings):
        """
        Test that loaded documents include source metadata.

        Assume:
            - A valid test PDF file exists

        Expect:
            - All documents have "source" in their metadata
        """
        loader = PDFDocumentLoader()
        settings.pdf_path = test_pdf_file

        documents = loader.load_documents()

        for doc in documents:
            assert "source" in doc.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
