import sqlite3
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .database import get_db
from .models import UserRole
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_by_username(db: sqlite3.Connection, username: str) -> dict | None:
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return dict(row)
    return None


def get_current_user(
    token: str = Depends(oauth2_scheme), db: sqlite3.Connection = Depends(get_db)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001 - we rethrow as HTTP
        raise credentials_exception from exc

    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker

