import logging
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.db.models import User, QueryHistory
from app.schemas.query import QueryRequest, QueryResponse
from app.services.retrieval import retrieve_chunks
from app.services.llm import build_prompt, generate_answer

router = APIRouter(prefix="/query", tags=["Query"])
logger = logging.getLogger(__name__)

@router.post("", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Call retrieve_chunks(query, org_id, db)
    chunks = await retrieve_chunks(request.query, current_user.organization_id, db)
    
    # 2. If no chunks found -> return "No relevant documents found" immediately
    if not chunks:
        answer = "No relevant documents found"
        sources = []
    else:
        # 3. Build prompt -> call generate_answer()
        prompt = build_prompt(request.query, chunks)
        answer = generate_answer(prompt)
        
        # sources: list[dict] (chunk text + filename)
        sources = [{"text": chunk["text"], "filename": chunk["filename"]} for chunk in chunks]
    
    # 4. Save QueryHistory row to DB
    history = QueryHistory(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        query=request.query,
        response=answer
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    
    # Log query + response length
    logger.info(f"User {current_user.id} query: '{request.query}' | Response length: {len(answer)}")
    
    # 5. Return QueryResponse
    return QueryResponse(
        answer=answer,
        sources=sources,
        query_id=history.id
    )
