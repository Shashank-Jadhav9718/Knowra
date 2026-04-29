import os
import shutil
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_current_user
from app.db.session import get_db, AsyncSessionLocal
from app.db.models import User, Document, Chunk
from app.schemas.document import DocumentOut, DocumentList
from app.services.ingestion import ingest_document
from app.core.config import settings
from app.services.faiss_store import remove_vectors
from app.utils.logger import logger

router = APIRouter()

async def run_ingestion_task(file_path: str, document_id: UUID, organization_id: UUID):
    """
    Wrapper for ingestion task to provide a fresh db session
    since the request session will be closed by the time background task runs.
    """
    async with AsyncSessionLocal() as session:
        try:
            await ingest_document(file_path, document_id, organization_id, session)
        except Exception as e:
            logger.error(f"Background ingestion failed for doc {document_id}: {e}")

@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    # Check max 10MB
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB allowed.")

    org_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.organization_id))
    os.makedirs(org_dir, exist_ok=True)
    
    file_path = os.path.join(org_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    document = Document(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        filename=file.filename,
        file_path=file_path
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    background_tasks.add_task(
        run_ingestion_task,
        file_path=file_path,
        document_id=document.id,
        organization_id=current_user.organization_id
    )
    
    return document

@router.get("", response_model=DocumentList)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).where(Document.organization_id == current_user.organization_id)
    )
    docs = result.scalars().all()
    
    return DocumentList(
        documents=docs,
        total=len(docs)
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    # Get all chunks to get FAISS IDs before deleting the document
    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == document_id)
    )
    chunks = chunks_result.scalars().all()
    faiss_ids = [chunk.faiss_index_id for chunk in chunks if chunk.faiss_index_id != -1]
    
    # Remove from FAISS
    remove_vectors(str(current_user.organization_id), faiss_ids)
    
    # Remove file from disk
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError as e:
            logger.warning(f"Could not remove file {document.file_path}: {e}")
        
    # Delete from DB
    await db.delete(document)
    await db.commit()
    return
