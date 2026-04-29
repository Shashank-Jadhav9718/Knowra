from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List

class DocumentOut(BaseModel):
    id: UUID
    filename: str
    created_at: datetime
    organization_id: UUID

    model_config = ConfigDict(from_attributes=True)

class DocumentList(BaseModel):
    documents: List[DocumentOut]
    total: int
