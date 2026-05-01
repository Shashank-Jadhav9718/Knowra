from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict, EmailStr, UUID4

from app.core.dependencies import get_current_admin
from app.db.session import get_db
from app.db.models import User, QueryHistory, Document, Chunk, UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])

# --- Schemas ---

class UserOut(BaseModel):
    id: UUID4
    email: EmailStr
    role: UserRole
    organization_id: UUID4
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class QueryHistoryOut(BaseModel):
    id: UUID4
    user_id: UUID4
    query: str
    response: str
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AdminStatsOut(BaseModel):
    total_users: int
    total_documents: int
    total_chunks: int
    total_queries: int

# --- Routes ---

@router.get("/users", response_model=List[UserOut])
async def get_admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all users in the current admin's organization.
    """
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_admin.organization_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/logs", response_model=List[QueryHistoryOut])
async def get_admin_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns QueryHistory for the current admin's organization, ordered by timestamp descending.
    """
    result = await db.execute(
        select(QueryHistory)
        .where(QueryHistory.organization_id == current_admin.organization_id)
        .order_by(QueryHistory.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/stats", response_model=AdminStatsOut)
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns total document, chunk, query, and user counts for the current organization.
    """
    # Total Users
    total_users = await db.scalar(
        select(func.count(User.id))
        .where(User.organization_id == current_admin.organization_id)
    )
    
    # Total Documents
    total_documents = await db.scalar(
        select(func.count(Document.id))
        .where(Document.organization_id == current_admin.organization_id)
    )
    
    # Total Queries
    total_queries = await db.scalar(
        select(func.count(QueryHistory.id))
        .where(QueryHistory.organization_id == current_admin.organization_id)
    )
    
    # Total Chunks (requires join with Document to filter by organization_id)
    total_chunks = await db.scalar(
        select(func.count(Chunk.id))
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.organization_id == current_admin.organization_id)
    )
    
    return AdminStatsOut(
        total_users=total_users or 0,
        total_documents=total_documents or 0,
        total_chunks=total_chunks or 0,
        total_queries=total_queries or 0
    )
