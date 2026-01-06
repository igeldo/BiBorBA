# core/graph/tools/document_loaders/pdf_loader.py
"""
PDF Document Loader mit PyMuPDF
"""

import logging
import gc
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from app.config import settings
from .base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class PDFDocumentLoader(BaseDocumentLoader):
    """Spezialisierter Loader für PDF-Dokumente"""

    def __init__(self):
        super().__init__()
        self.max_file_size_mb = settings.max_pdf_size_mb

    def load_documents(self) -> List[Document]:
        """Load and split PDF documents with optimizations for large files"""
        pdf_path = settings.pdf_path

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF path not found: {pdf_path}")

        logger.info(f"Loading PDF documents from: {pdf_path}")

        documents = []

        if pdf_path.is_file() and pdf_path.suffix.lower() == '.pdf':
            # Single PDF file
            documents = self._load_single_pdf(pdf_path)
        elif pdf_path.is_dir():
            # Directory with PDF files
            documents = self._load_pdf_directory(pdf_path)
        else:
            raise ValueError(f"PDF path must be a file or directory: {pdf_path}")

        if not documents:
            raise ValueError("No documents could be loaded from PDF path")

        # Validate and split documents
        documents = self.validate_documents(documents)
        return self.split_documents(documents)

    def _load_single_pdf(self, pdf_file: Path) -> List[Document]:
        """Load a single PDF file"""
        logger.info(f"Loading single PDF: {pdf_file.name}")
        documents = self._load_pdf(pdf_file)
        logger.info(f"Loaded single PDF: {pdf_file.name} ({len(documents)} pages)")
        return documents

    def _load_pdf_directory(self, pdf_dir: Path) -> List[Document]:
        """Load all PDF files from a directory"""
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in directory: {pdf_dir}")

        pdf_files.sort(key=lambda f: f.stat().st_size)
        total_files = len(pdf_files)

        all_documents = []

        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"Processing file {i}/{total_files}: {pdf_file.name}")

            try:
                file_docs = self._load_pdf(pdf_file)
                all_documents.extend(file_docs)
                logger.info(f"Successfully loaded: {pdf_file.name} ({len(file_docs)} pages)")

                gc.collect()

            except Exception as e:
                logger.error(f"Failed to load {pdf_file.name}: {e}")
                continue

        logger.info(f"Total documents loaded: {len(all_documents)}")
        gc.collect()

        return all_documents

    def _load_pdf(self, pdf_file: Path) -> List[Document]:
        """Checks filesize before loading"""
        file_info = self.check_file_size(pdf_file, self.max_file_size_mb)

        if file_info["too_large"]:
            raise ValueError(f"PDF file too large: {file_info['size_mb']:.1f} MB (max: {self.max_file_size_mb} MB)")

        if file_info["is_large"]:
            logger.warning(f"Large PDF detected: {pdf_file.name} ({file_info['size_mb']:.1f} MB)")

        return self._load_with_pymupdf(pdf_file)

    def _load_with_pymupdf(self, pdf_file: Path) -> List[Document]:
        """Load PDF using PyMuPDF"""
        try:
            import fitz  # pymupdf

            logger.info(f"Using PyMuPDF for {pdf_file.name}")

            documents = []
            pdf_doc = fitz.open(str(pdf_file))
            total_pages = len(pdf_doc)

            logger.info(f"Processing {total_pages} pages with PyMuPDF")

            for page_num in range(total_pages):
                try:
                    page = pdf_doc[page_num]
                    text = page.get_text()

                    if text.strip():  # Nur Seiten mit Inhalt
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": str(pdf_file),
                                "page": page_num + 1,
                                "total_pages": total_pages,
                                "loader": "pymupdf"
                            }
                        )
                        documents.append(doc)

                    if total_pages > 100 and (page_num + 1) % 50 == 0:
                        logger.info(f"Processed {page_num + 1}/{total_pages} pages")

                except Exception as e:
                    logger.warning(f"Error processing page {page_num + 1}: {e}")
                    continue

            pdf_doc.close()
            logger.info(f"PyMuPDF loaded {len(documents)} pages with content")
            return documents

        except ImportError as e:
            logger.debug("PyMuPDF not installed. Install with: pip install pymupdf")
            raise ImportError("PyMuPDF not available") from e