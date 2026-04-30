import uuid
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    query_id: uuid.UUID
