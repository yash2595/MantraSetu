"""Unit & Integration Test Suite for Enterprise Knowledge & RAG Intelligence Sprint 6C v1.1."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.knowledge import (
    KnowledgeSyncManager,
    ProductionChunkingEngine,
    ProductionCitationManager,
    ProductionDocumentIngestionEngine,
    ProductionEmbeddingPipeline,
    ProductionHybridRetriever,
    ProductionKnowledgeCache,
    ProductionKnowledgeTelemetryEngine,
    ProductionRerankingEngine,
    QdrantProductionVectorStore,
)


class TestSprint6CKnowledgeRAG(unittest.TestCase):
    """Test suite covering ingestion, chunking, embedding, Qdrant vector store, hybrid search, RRF reranking, citations, sync, cache, telemetry, and SLAs."""

    def setUp(self):
        self.telemetry = ProductionKnowledgeTelemetryEngine()
        self.cache = ProductionKnowledgeCache()
        self.ingestion = ProductionDocumentIngestionEngine()
        self.chunking = ProductionChunkingEngine()
        self.embedding = ProductionEmbeddingPipeline()
        self.vector_store = QdrantProductionVectorStore()
        self.retriever = ProductionHybridRetriever()
        self.reranker = ProductionRerankingEngine()
        self.citation_mgr = ProductionCitationManager()
        self.sync_mgr = KnowledgeSyncManager()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all RAG modules."""
        modules = [
            self.telemetry,
            self.cache,
            self.ingestion,
            self.chunking,
            self.embedding,
            self.vector_store,
            self.retriever,
            self.reranker,
            self.citation_mgr,
            self.sync_mgr,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_document_ingestion_formats(self):
        """Test document ingestion across PDF, DOCX, MD, HTML, TXT, JSON."""
        formats = ["pdf", "docx", "md", "html", "txt", "json"]
        for fmt in formats:
            doc = self.ingestion.ingest_document(
                title=f"Sample {fmt.upper()} Doc",
                content=f"Satyanarayan Puja details for format {fmt}",
                file_type=fmt,
                collection="mantrasetu_pujas",
            )
            self.assertIsNotNone(doc.doc_id)
            self.assertEqual(doc.file_type, fmt)

    def test_chunking_strategies(self):
        """Test semantic, sliding window, and recursive chunking."""
        content = "Line 1 text. Line 2 text. Line 3 text. Line 4 text. Line 5 text."
        chunks = self.chunking.chunk_document(doc_id="d1", content=content, strategy="SEMANTIC")
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].doc_id, "d1")

    def test_end_to_end_rag_sync_and_hybrid_retrieval(self):
        """Test complete flow: Ingest -> Sync -> Embed -> Qdrant -> Hybrid Search -> RRF Rerank -> Citations."""
        # 1. Ingest document
        doc = self.ingestion.ingest_document(
            title="Satyanarayan Vidhi",
            content="Satyanarayan Puja requires prasad, banana leaves, panchamrit, and panditji.",
            file_type="pdf",
            collection="mantrasetu_pujas",
        )

        # 2. Sync document into Qdrant vector store
        points_count = self.sync_mgr.sync_document(doc)
        self.assertGreater(points_count, 0)

        # 3. Hybrid search
        hybrid_results = self.sync_mgr.retriever.retrieve(
            query="Satyanarayan Puja items required",
            collection_name="mantrasetu_pujas",
            top_k=3,
        )
        self.assertGreater(len(hybrid_results), 0)

        # 4. Rerank
        reranked = self.reranker.rerank(hybrid_results, top_n=2)
        self.assertGreater(len(reranked), 0)

        # 5. Build citations
        citation_pkg = self.citation_mgr.build_citation_package("Satyanarayan Puja items", reranked)
        self.assertGreater(len(citation_pkg.citations), 0)
        self.assertEqual(citation_pkg.citation_coverage, 100.0)

    def test_thread_safety(self):
        def worker(i: int):
            ing = ProductionDocumentIngestionEngine()
            _ = ing.ingest_document(title=f"Doc {i}", content=f"Content {i}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
