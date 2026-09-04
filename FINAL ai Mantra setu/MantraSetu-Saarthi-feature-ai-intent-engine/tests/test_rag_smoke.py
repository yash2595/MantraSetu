import asyncio
import os
import shutil
import time
from uuid import uuid4

from app.core.config import settings
from app.rag.models import DocumentChunk, RetrievalRequest
from app.rag.providers.chroma_vector_store import ChromaVectorStore
from app.rag.providers.local_embedding_provider import LocalEmbeddingProvider

async def main():
    print("--- RAG Smoke Test ---")
    
    # We will use a temporary path for the smoke test
    test_db_path = "./data/smoke_test_chroma"
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    
    print("1. Initializing Embedding Provider...")
    t0 = time.time()
    embedding_provider = LocalEmbeddingProvider()
    print(f"Embedding provider initialized (lazy load) in {time.time()-t0:.2f}s")
    
    print("2. Initializing Chroma Vector Store...")
    t0 = time.time()
    vector_store = ChromaVectorStore(
        db_path=test_db_path,
        embedding_provider=embedding_provider,
        collection_name="smoke_test"
    )
    await vector_store.initialize()
    print(f"Vector store initialized in {time.time()-t0:.2f}s")
    
    print("3. Adding Chunks...")
    doc_id = uuid4()
    chunks = (
        DocumentChunk(
            document_id=doc_id,
            content="Rudrabhishek Puja brings peace and prosperity to your home. It involves offering milk and water to Lord Shiva.",
            chunk_index=0,
            metadata={"source": "puja_guide"}
        ),
        DocumentChunk(
            document_id=doc_id,
            content="Satyanarayan Puja is performed before major milestones like a new house or marriage. It requires bananas, pan, and supari.",
            chunk_index=1,
            metadata={"source": "puja_guide"}
        ),
        DocumentChunk(
            document_id=doc_id,
            content="Kundali matching compares the horoscopes of the bride and groom for compatibility in Hindu marriages.",
            chunk_index=2,
            metadata={"source": "astrology"}
        )
    )
    
    t0 = time.time()
    await vector_store.add_chunks(chunks)
    print(f"Chunks embedded and added in {time.time()-t0:.2f}s")
    
    print("4. Executing Similarity Search...")
    request = RetrievalRequest(query="What are the benefits of Rudrabhishek?", top_k=2)
    t0 = time.time()
    results = await vector_store.similarity_search(request)
    print(f"Similarity search completed in {time.time()-t0:.2f}s")
    
    print(f"Results found: {len(results)}")
    for i, res in enumerate(results):
        print(f"  Result {i+1} (Score: {res.score:.4f}): {res.chunk.content}")
        
    # Check health
    health = await vector_store.health_check()
    print(f"Health Check: {health.status} - {health.message}")
    
    # Cleanup
    import gc
    del vector_store
    gc.collect()
    shutil.rmtree(test_db_path, ignore_errors=True)
    print("--- Smoke Test Completed ---")

if __name__ == "__main__":
    asyncio.run(main())
