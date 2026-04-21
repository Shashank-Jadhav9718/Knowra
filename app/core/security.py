from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Assuming a default expiry time in settings, defaulting to 15 minutes otherwise
        expire = datetime.now(timezone.utc) + timedelta(minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    
    to_encode.update({"exp": expire})
    # Assuming SECRET_KEY and ALGORITHM are defined in settings
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=getattr(settings, "ALGORITHM", "HS256"))
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[getattr(settings, "ALGORITHM", "HS256")])
        token_data = TokenData(**payload)
        return token_data
    except JWTError:
        raise credentials_exception
