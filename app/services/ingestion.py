import fitz  # PyMuPDF
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import logger
from app.utils.chunker import chunk_document
from app.services.embedding import get_embedding
from app.services.faiss_store import add_vectors
from app.db.models import Chunk

async def ingest_document(file_path: str, document_id: UUID, organization_id: UUID, db: AsyncSession) -> int:
    """
    Ingest a PDF document: extract text, chunk it, generate embeddings,
    store chunks in database, and index vectors in FAISS.
    """
    logger.info(f"Starting ingestion for document {document_id} from {file_path}")
    
    # 1. Extract text from PDF using PyMuPDF (fitz) page by page
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        raise

    # 2. Chunk text using chunk_document() from app.utils.chunker
    logger.info(f"Chunking extracted text for document {document_id}")
    chunks = chunk_document(full_text)
    
    if not chunks:
        logger.warning(f"No text chunks generated for document {document_id}")
        return 0

    # 3. For each chunk: call get_embedding(), store Chunk row in DB (text + document_id), get chunk DB id
    logger.info(f"Generating embeddings and preparing DB records for {len(chunks)} chunks")
    db_chunks = []
    vectors = []
    
    for text_chunk in chunks:
        # Get embedding
        vector = get_embedding(text_chunk)
        vectors.append(vector)
        
        # Store Chunk row in DB
        chunk_model = Chunk(
            text=text_chunk, 
            document_id=document_id,
            faiss_index_id=-1  # Temporary value to allow flush since it's not nullable
        )
        db.add(chunk_model)
        db_chunks.append(chunk_model)
        
    # Flush to get chunk DB ids
    await db.flush()
    
    # 4. Batch add all vectors to FAISS via add_vectors(), update each Chunk.faiss_index_id
    logger.info(f"Adding {len(vectors)} vectors to FAISS for organization {organization_id}")
    
    # Get the generated DB chunk IDs
    chunk_ids = [str(c.id) for c in db_chunks]
    
    # Add vectors to FAISS and get the FAISS internal index IDs
    faiss_ids = add_vectors(str(organization_id), vectors, chunk_ids)
    
    # Update each Chunk with its corresponding FAISS index ID
    for db_chunk, faiss_id in zip(db_chunks, faiss_ids):
        db_chunk.faiss_index_id = faiss_id
        
    # 5. Commit DB, return total chunk count
    logger.info("Committing chunks to database")
    await db.commit()
    
    logger.info(f"Successfully ingested document {document_id} with {len(db_chunks)} chunks")
    return len(db_chunks)
