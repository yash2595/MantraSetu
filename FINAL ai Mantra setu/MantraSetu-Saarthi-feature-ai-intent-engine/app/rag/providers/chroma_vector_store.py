"""ChromaDB implementation of BaseVectorStore.

Implements the vector database storage and similarity search for MantraSetu using ChromaDB.
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.rag.contracts import BaseEmbeddingProvider, BaseVectorStore, VectorDatabaseError
from app.rag.models import DocumentChunk, RetrievalRequest, RetrievalResult, RetrievalStatus

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """Vector storage and retrieval using ChromaDB.

    Operates in persistent local mode, storing SQLite/Parquet files
    at the configured db_path. Uses the injected BaseEmbeddingProvider
    to explicitly embed queries and chunks.
    """

    def __init__(
        self,
        db_path: str,
        embedding_provider: BaseEmbeddingProvider,
        collection_name: str = "mantrasetu_knowledge_base",
    ) -> None:
        """Initialize the ChromaDB store wrapper.

        Args:
            db_path: Path on disk to store the persistent Chroma database.
            embedding_provider: Initialized provider for generating text vectors.
            collection_name: Name of the Chroma collection to use.
        """
        self._db_path = db_path
        self._embedding_provider = embedding_provider
        self._collection_name = collection_name
        self._client = None
        self._collection = None

    async def initialize(self) -> None:
        """Initialize the ChromaDB client and collection."""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            # Ensure the directory exists
            os.makedirs(self._db_path, exist_ok=True)

            logger.info("Initializing ChromaDB persistent client at %s", self._db_path)
            self._client = chromadb.PersistentClient(
                path=self._db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"description": "MantraSetu RAG Knowledge Base"}
            )
            logger.info("Successfully initialized ChromaDB collection '%s'", self._collection_name)
        except Exception as e:
            logger.error("Failed to initialize ChromaDB: %s", e)
            raise VectorDatabaseError(f"Failed to initialize ChromaDB: {e}") from e

    async def add_chunks(
        self,
        chunks: tuple[DocumentChunk, ...],
    ) -> None:
        """Add and index an immutable tuple of DocumentChunk instances.

        Args:
            chunks: Immutable tuple of DocumentChunk models.

        Raises:
            VectorDatabaseError: If chunk indexing fails.
        """
        if not self._collection:
            await self.initialize()

        if not chunks:
            return

        try:
            # We embed all texts using our provider first
            texts = tuple(chunk.content for chunk in chunks)
            embeddings = await self._embedding_provider.generate_embeddings(texts)

            # Chroma expects lists of ids, lists of lists for embeddings, metadatas, and documents
            ids = [str(chunk.chunk_id) for chunk in chunks]
            documents = list(texts)
            metadatas = [
                {
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    **{k: (str(v) if not isinstance(v, (str, int, float, bool)) else v) 
                       for k, v in chunk.metadata.items()}
                }
                for chunk in chunks
            ]

            # Upsert into Chroma (updates if id exists, else inserts)
            await asyncio.to_thread(
                self._collection.upsert,
                ids=ids,
                embeddings=[list(emb) for emb in embeddings],
                metadatas=metadatas,
                documents=documents
            )
            logger.info("Added %d chunks to ChromaDB collection", len(chunks))
        except Exception as e:
            logger.error("Error adding chunks to ChromaDB: %s", e)
            raise VectorDatabaseError(f"Failed to add chunks: {e}") from e

    async def similarity_search(
        self,
        request: RetrievalRequest,
    ) -> tuple[RetrievalResult, ...]:
        """Execute a vector similarity search for a RetrievalRequest.

        Args:
            request: RetrievalRequest model containing query and top_k.

        Returns:
            tuple[RetrievalResult, ...]: Immutable tuple of matching RetrievalResult entities.

        Raises:
            VectorDatabaseError: If search query execution fails.
        """
        if not self._collection:
            await self.initialize()

        try:
            # Generate embedding for the query explicitly
            query_embeddings = await self._embedding_provider.generate_embeddings((request.query,))
            if not query_embeddings:
                return ()
                
            query_vector = query_embeddings[0]

            # Query Chroma
            chroma_results = await asyncio.to_thread(
                self._collection.query,
                query_embeddings=[list(query_vector)],
                n_results=request.top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Map results back to Domain Models
            results = []
            if not chroma_results["ids"] or not chroma_results["ids"][0]:
                return ()

            for i in range(len(chroma_results["ids"][0])):
                chunk_id_str = chroma_results["ids"][0][i]
                document = chroma_results["documents"][0][i]
                metadata = dict(chroma_results["metadatas"][0][i] or {})
                
                # Chroma uses L2 distance by default. Convert to a similarity score between 0 and 1.
                # Smaller distance = higher similarity.
                distance = chroma_results["distances"][0][i]
                similarity_score = 1.0 / (1.0 + distance)

                doc_id_str = metadata.pop("document_id", "")
                try:
                    document_id = UUID(str(doc_id_str))
                except ValueError:
                    # Fallback if document_id is missing or malformed
                    from uuid import uuid4
                    document_id = uuid4()
                    
                chunk_index = int(metadata.pop("chunk_index", 0))

                chunk = DocumentChunk(
                    chunk_id=UUID(chunk_id_str),
                    document_id=document_id,
                    content=document,
                    chunk_index=chunk_index,
                    metadata=metadata
                )
                
                results.append(
                    RetrievalResult(
                        chunk=chunk,
                        score=similarity_score,
                        status=RetrievalStatus.SUCCESS
                    )
                )

            return tuple(results)
        except Exception as e:
            logger.error("Error executing similarity search in ChromaDB: %s", e)
            raise VectorDatabaseError(f"Failed to execute similarity search: {e}") from e

    async def delete_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all vector chunk records associated with a document_id.

        Args:
            document_id: Unique document identifier UUID.

        Raises:
            VectorDatabaseError: If deletion fails.
        """
        if not self._collection:
            await self.initialize()

        try:
            # Chroma supports deleting by metadata filters
            await asyncio.to_thread(
                self._collection.delete,
                where={"document_id": str(document_id)}
            )
            logger.info("Deleted chunks for document %s from ChromaDB", document_id)
        except Exception as e:
            logger.error("Error deleting document %s from ChromaDB: %s", document_id, e)
            raise VectorDatabaseError(f"Failed to delete document: {e}") from e

    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the vector store backend.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        try:
            if not self._client:
                # Can be healthy but uninitialized
                return ComponentHealth(
                    component_name="chroma_vector_store",
                    status=SystemHealthStatus.HEALTHY,
                    message="ChromaDB uninitialized but reachable (lazy load)."
                )
                
            # Perform a lightweight operation to verify connectivity
            await asyncio.to_thread(self._client.heartbeat)
            return ComponentHealth(
                component_name="chroma_vector_store",
                status=SystemHealthStatus.HEALTHY,
                message="ChromaDB persistent client operational."
            )
        except Exception as e:
            return ComponentHealth(
                component_name="chroma_vector_store",
                status=SystemHealthStatus.UNHEALTHY,
                message=f"ChromaDB health check failed: {e}"
            )
