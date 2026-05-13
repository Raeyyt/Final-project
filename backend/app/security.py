from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
import bcrypt

from .config import settings
from .schemas import TokenData


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or settings.access_token_expiry)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise JWTError("Invalid token payload")
        return TokenData(username=username, role=role)
    except JWTError as exc:
        raise JWTError("Could not validate credentials") from exc

