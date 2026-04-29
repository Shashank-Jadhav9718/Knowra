from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.services.embedding import get_query_embedding
from app.services.faiss_store import search_vectors
from app.db.models import Chunk, Document

async def retrieve_chunks(query: str, organization_id: str, db: AsyncSession, top_k: int = 5) -> list[dict]:
    """
    Retrieve top_k chunks for a query from FAISS and return their DB representations,
    ensuring they belong to the correct organization.
    """
    # 1. Get embedding for the query
    query_vector = get_query_embedding(query)
    
    # 2. Retrieve nearest neighbor IDs from FAISS index
    faiss_index_ids = search_vectors(organization_id, query_vector, top_k)
    
    if not faiss_index_ids:
        return []
        
    # 3. Query DB for chunks that match FAISS IDs, strictly enforcing tenant isolation
    stmt = (
        select(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.faiss_index_id.in_(faiss_index_ids),
            Document.organization_id == organization_id
        )
        .options(selectinload(Chunk.document))
    )
    
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    
    # Map retrieved chunks to preserve FAISS ordering (which is based on relevance)
    chunk_map = {chunk.faiss_index_id: chunk for chunk in chunks}
    
    # 4. Return as list of dictionaries
    ordered_chunks = []
    for faiss_id in faiss_index_ids:
        if faiss_id in chunk_map:
            chunk = chunk_map[faiss_id]
            ordered_chunks.append({
                "chunk_id": str(chunk.id),
                "text": chunk.text,
                "document_id": str(chunk.document_id),
                "filename": chunk.document.filename
            })
            
    return ordered_chunks
