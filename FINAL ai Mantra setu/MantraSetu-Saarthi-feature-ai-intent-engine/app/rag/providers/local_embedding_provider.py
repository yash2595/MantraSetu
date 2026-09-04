"""Local embedding provider using sentence-transformers.

Implements BaseEmbeddingProvider for MantraSetu RAG subsystem.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.rag.contracts import BaseEmbeddingProvider, EmbeddingError

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using a local sentence-transformers model.

    The model is loaded lazily on the first generation call to prevent
    slowing down application startup when RAG features are unused.
    """

    def __init__(self) -> None:
        """Initialize the provider, keeping the model uninitialized for lazy loading."""
        self._model_name = settings.embedding_model_name
        self._model: Any = None
        self._is_loaded = False

    def _load_model(self) -> None:
        """Lazily load the sentence-transformers model."""
        if self._is_loaded:
            return

        try:
            logger.info("Loading local embedding model: %s", self._model_name)
            # Import delayed to avoid slowing down app startup
            from sentence_transformers import SentenceTransformer

            # Load model onto CPU explicitly to ensure compatibility
            self._model = SentenceTransformer(self._model_name, device="cpu")
            self._is_loaded = True
            logger.info("Successfully loaded embedding model: %s", self._model_name)
        except Exception as e:
            logger.error("Failed to load sentence-transformers model %s: %s", self._model_name, e)
            raise EmbeddingError(f"Failed to load embedding model: {e}") from e

    async def generate_embeddings(
        self,
        texts: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        """Generate vector embeddings for an immutable tuple of text strings.

        Args:
            texts: Immutable tuple of input text strings.

        Returns:
            tuple[tuple[float, ...], ...]: Tuple of vector float tuples.

        Raises:
            EmbeddingError: If vector embedding generation fails.
        """
        if not texts:
            return ()

        # Ensure model is loaded before inference
        self._load_model()

        try:
            # We convert tuple to list for the underlying library
            text_list = list(texts)
            
            # encode() returns a numpy array or tensor depending on arguments,
            # we use convert_to_numpy=True (default) to get numpy arrays.
            # Then convert to float tuples as required by the contract.
            embeddings_array = await asyncio.to_thread(
                self._model.encode, text_list, convert_to_numpy=True
            )
            
            # Map the numpy arrays (which are iterable) to tuples of floats
            result = tuple(tuple(float(val) for val in emb) for emb in embeddings_array)
            return result
        except Exception as e:
            logger.error("Error generating embeddings: %s", e)
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e
