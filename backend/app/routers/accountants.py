from typing import List
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..deps import get_db, get_current_user
from ..models import UserRole
from ..security import get_password_hash

router = APIRouter(prefix="/accountants", tags=["accountants"])

@router.get("/", response_model=List[schemas.UserRead])
def get_accountants(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    accountants = db.execute("SELECT * FROM users WHERE role = ?", (UserRole.ACCOUNTANT.value,)).fetchall()
    return [dict(a) for a in accountants]

@router.post("/", response_model=schemas.UserRead)
def create_accountant(
    accountant_in: schemas.UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if accountant_in.role != UserRole.ACCOUNTANT:
         raise HTTPException(status_code=400, detail="Can only create accountants here")

    existing_user = db.execute("SELECT id FROM users WHERE username = ?", (accountant_in.username,)).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(accountant_in.password)
    
    cursor = db.execute(
        "INSERT INTO users (username, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
        (accountant_in.username, accountant_in.full_name, hashed_password, UserRole.ACCOUNTANT.value)
    )
    db.commit()
    
    new_accountant = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(new_accountant)

@router.delete("/{accountant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accountant(
    accountant_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    accountant = db.execute("SELECT * FROM users WHERE id = ?", (accountant_id,)).fetchone()
    if not accountant:
        raise HTTPException(status_code=404, detail="Accountant not found")
    
    if accountant["role"] != UserRole.ACCOUNTANT.value:
        raise HTTPException(status_code=400, detail="User is not an accountant")

    db.execute("DELETE FROM users WHERE id = ?", (accountant_id,))
    db.commit()
    return None
