"""
Batched Ollama Embeddings
Wrapper für OllamaEmbeddings mit automatischem Batching
"""

import logging
from typing import List
from langchain_ollama import OllamaEmbeddings
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class BatchedOllamaEmbeddings(Embeddings):
    """
    Wrapper für OllamaEmbeddings mit automatischem Batching
    Verhindert "context length exceeded" Fehler bei großen Dokumentmengen
    """

    def __init__(self, model: str, base_url: str, batch_size: int = 10):
        """
        Args:
            model: Name des Ollama Embedding-Modells
            base_url: Ollama Base URL
            batch_size: Maximale Anzahl von Dokumenten pro Batch (default: 10)
        """
        self._embeddings = OllamaEmbeddings(
            model=model,
            base_url=base_url
        )
        self.batch_size = batch_size

        logger.info(f"BatchedOllamaEmbeddings initialized with batch_size={batch_size}")

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text"""
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed documents in batches to avoid context length errors

        Args:
            texts: List of document texts to embed

        Returns:
            List of embeddings (one per document)
        """
        total_docs = len(texts)

        if total_docs == 0:
            return []

        if total_docs <= self.batch_size:
            # Small enough - process directly
            logger.debug(f"Embedding {total_docs} documents in single batch")
            return self._embeddings.embed_documents(texts)

        # Process in batches
        logger.info(f"Embedding {total_docs} documents in batches of {self.batch_size}")

        all_embeddings = []

        for i in range(0, total_docs, self.batch_size):
            batch_end = min(i + self.batch_size, total_docs)
            batch = texts[i:batch_end]

            logger.debug(f"Embedding batch {i//self.batch_size + 1}: documents {i}-{batch_end} ({len(batch)} docs)")

            try:
                batch_embeddings = self._embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Error embedding batch {i//self.batch_size + 1}: {e}")

                # Retry with smaller batches if error occurs
                if len(batch) > 5:
                    logger.info(f"Retrying batch with smaller sub-batches (size 5)")
                    for j in range(0, len(batch), 5):
                        sub_batch = batch[j:min(j + 5, len(batch))]
                        try:
                            sub_embeddings = self._embeddings.embed_documents(sub_batch)
                            all_embeddings.extend(sub_embeddings)
                            logger.debug(f"Successfully embedded sub-batch {j//5 + 1}")
                        except Exception as sub_e:
                            logger.error(f"Failed to embed sub-batch: {sub_e}")
                            # Try one document at a time as last resort
                            for k, single_text in enumerate(sub_batch):
                                try:
                                    single_embedding = self._embeddings.embed_documents([single_text])
                                    all_embeddings.extend(single_embedding)
                                except Exception as single_e:
                                    logger.error(f"Failed to embed single document: {single_e}")
                                    raise
                else:
                    # Already small batch - try one at a time
                    logger.info(f"Retrying batch one document at a time")
                    for k, single_text in enumerate(batch):
                        try:
                            single_embedding = self._embeddings.embed_documents([single_text])
                            all_embeddings.extend(single_embedding)
                        except Exception as single_e:
                            logger.error(f"Failed to embed single document: {single_e}")
                            raise

        logger.info(f"Successfully embedded {len(all_embeddings)} documents")

        return all_embeddings
