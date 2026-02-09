"""
Base Document Loader
Shared functionality for all document loaders
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)


class BaseDocumentLoader(ABC):
    """Base class for all document loaders"""

    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    @abstractmethod
    def load_documents(self) -> List[Document]:
        """Load documents from source"""
        pass

    def split_documents(self, documents: List[Document], custom_separators: Optional[List[str]] = None) -> List[
        Document]:
        """Split documents into chunks with optimization"""
        if not documents:
            return documents

        logger.info(f"Splitting {len(documents)} documents...")

        total_chars = sum(len(doc.page_content) for doc in documents)
        avg_chars_per_doc = total_chars / len(documents) if documents else 0

        logger.info(f"Total characters: {total_chars:,}, Average per document: {avg_chars_per_doc:.0f}")

        chunk_size, chunk_overlap = self._calculate_chunk_params(total_chars, avg_chars_per_doc)

        if custom_separators:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=custom_separators
            )
        else:
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        doc_splits = text_splitter.split_documents(documents)

        logger.info(
            f"Split into {len(doc_splits)} chunks (average: {len(doc_splits) / len(documents):.1f} chunks per document)")

        MAX_CHUNK_CHARS = 1600
        final_chunks = []
        chunks_resplit = 0

        for chunk in doc_splits:
            if len(chunk.page_content) > MAX_CHUNK_CHARS:
                chunks_resplit += 1
                char_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=MAX_CHUNK_CHARS,
                    chunk_overlap=min(chunk_overlap * 4, 400),
                    length_function=len
                )
                sub_chunks = char_splitter.split_documents([chunk])
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        if chunks_resplit > 0:
            logger.info(f"Re-split {chunks_resplit} oversized chunks. Final count: {len(final_chunks)} chunks")

        return final_chunks

    def _calculate_chunk_params(self, total_chars: int, avg_chars_per_doc: float) -> tuple[int, int]:
        """Calculate optimal chunk parameters based on document size

        IMPORTANT: Chunk size is limited to max 800 tokens to avoid Ollama context length errors
        (Embedding models typically have 2048 token context, but with overhead we need smaller chunks)
        """
        max_safe_chunk_size = 800

        chunk_size = min(self.chunk_size, max_safe_chunk_size)
        chunk_overlap = min(self.chunk_overlap, chunk_size // 4)

        if avg_chars_per_doc > 5000:
            chunk_overlap = min(200, chunk_size // 4)
            logger.info(f"Large documents detected (avg {avg_chars_per_doc:.0f} chars), using chunk_size={chunk_size}, overlap={chunk_overlap}")

        logger.info(f"Chunk parameters: size={chunk_size} tokens, overlap={chunk_overlap} tokens")

        return chunk_size, chunk_overlap

    def check_file_size(self, file_path: Path, max_size_mb: int = 100) -> Dict[str, Any]:
        """Check file size and return metadata"""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        return {
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "is_large": size_mb > 20,
            "needs_chunking": size_mb > 25,
            "too_large": size_mb > max_size_mb
        }

    def validate_documents(self, documents: List[Document]) -> List[Document]:
        """Validate and clean documents"""
        valid_docs = []

        for i, doc in enumerate(documents):
            if not doc.page_content or not doc.page_content.strip():
                logger.warning(f"Skipping empty document {i}")
                continue

            doc.page_content = doc.page_content.strip()

            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}

            doc.metadata["document_index"] = i
            doc.metadata["content_length"] = len(doc.page_content)

            valid_docs.append(doc)

        logger.info(f"Validated {len(valid_docs)} documents (filtered {len(documents) - len(valid_docs)} empty)")

        return valid_docs

    def get_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """Get statistics about loaded documents"""
        if not documents:
            return {"total_documents": 0}

        content_lengths = [len(doc.page_content) for doc in documents]

        return {
            "total_documents": len(documents),
            "total_characters": sum(content_lengths),
            "avg_document_size": sum(content_lengths) / len(documents),
            "min_document_size": min(content_lengths),
            "max_document_size": max(content_lengths),
            "sources": list(set(doc.metadata.get("source", "unknown") for doc in documents))
        }