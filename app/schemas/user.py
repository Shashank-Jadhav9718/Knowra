from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    organization_id: UUID


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    organization_id: UUID

    @field_validator("role", mode="before")
    @classmethod
    def extract_role_value(cls, v):
        if hasattr(v, "value"):
            return v.value
        return str(v)

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[Union[UUID, str]] = None
    organization_id: Optional[Union[UUID, str]] = None
    role: Optional[str] = None
    model_config = ConfigDict(extra="ignore")

    @field_validator("user_id", "organization_id", mode="before")
    @classmethod
    def coerce_to_uuid(cls, v):
        """Coerce string UUIDs from JWT payload to UUID objects."""
        if v is None:
            return v
        if isinstance(v, UUID):
            return v
        try:
            return UUID(str(v))
        except (ValueError, AttributeError):
            return v
