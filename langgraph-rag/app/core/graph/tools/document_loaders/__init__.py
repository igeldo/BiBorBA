# core/graph/tools/document_loaders/__init__.py
"""
Document Loading Module
Aufgeteilte Loader für verschiedene Dokumenttypen
"""

from .base_loader import BaseDocumentLoader
from .pdf_loader import PDFDocumentLoader
from .stackoverflow_loader import StackOverflowDocumentLoader

__all__ = [
    'BaseDocumentLoader',
    'PDFDocumentLoader',
    'StackOverflowDocumentLoader'
]