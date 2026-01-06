"""
Tests für PDFDocumentLoader

Testet Kernfunktionalität:
- Laden einzelner PDFs
- Laden aus Verzeichnis
- Fehlerbehandlung
"""
import pytest
from pathlib import Path
from langchain_core.documents import Document

from app.core.graph.tools.document_loaders.pdf_loader import PDFDocumentLoader
from app.config import settings


class TestPDFLoader:
    """Test PDF-Loading"""

    def test_load_single_pdf(self, test_pdf_file, test_settings):
        """Einzelne PDF laden"""
        loader = PDFDocumentLoader()
        settings.pdf_path = test_pdf_file

        documents = loader.load_documents()

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.page_content.strip() for doc in documents)

    def test_load_pdf_directory(self, test_pdf_files, test_settings):
        """PDFs aus Verzeichnis laden"""
        loader = PDFDocumentLoader()
        pdf_dir = test_pdf_files[0].parent
        settings.pdf_path = pdf_dir

        documents = loader.load_documents()

        assert len(documents) > 0

    def test_file_not_found_raises_error(self, tmp_path):
        """Fehlende Datei wirft FileNotFoundError"""
        loader = PDFDocumentLoader()
        settings.pdf_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            loader.load_documents()

    def test_empty_directory_raises_error(self, tmp_path):
        """Leeres Verzeichnis wirft FileNotFoundError"""
        loader = PDFDocumentLoader()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        settings.pdf_path = empty_dir

        with pytest.raises(FileNotFoundError) as excinfo:
            loader.load_documents()

        assert "No PDF files found" in str(excinfo.value)

    def test_documents_have_metadata(self, test_pdf_file, test_settings):
        """Dokumente haben Source-Metadaten"""
        loader = PDFDocumentLoader()
        settings.pdf_path = test_pdf_file

        documents = loader.load_documents()

        for doc in documents:
            assert "source" in doc.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
