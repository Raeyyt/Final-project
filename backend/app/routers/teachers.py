from typing import List
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..deps import get_db, get_current_user
from ..models import UserRole
from ..security import get_password_hash

router = APIRouter(prefix="/teachers", tags=["teachers"])

@router.get("/", response_model=List[schemas.UserRead])
def get_teachers(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in (UserRole.ADMIN.value, UserRole.DIRECTOR.value):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teachers = db.execute("SELECT * FROM users WHERE role = ?", (UserRole.TEACHER.value,)).fetchall()
    return [dict(t) for t in teachers]

@router.post("/", response_model=schemas.UserRead)
def create_teacher(
    teacher_in: schemas.UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in (UserRole.ADMIN.value, UserRole.DIRECTOR.value):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if teacher_in.role != UserRole.TEACHER:
         raise HTTPException(status_code=400, detail="Can only create teachers here")

    title = (teacher_in.teaching_title or "").strip()
    if not title:
        raise HTTPException(
            status_code=400,
            detail="Teaching title (subject specialty) is required for teachers",
        )

    existing_user = db.execute("SELECT id FROM users WHERE username = ?", (teacher_in.username,)).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    if teacher_in.id:
        existing_id = db.execute("SELECT id FROM users WHERE id = ?", (teacher_in.id,)).fetchone()
        if existing_id:
            raise HTTPException(status_code=400, detail="User ID already exists")

    hashed_password = get_password_hash(teacher_in.password)
    
    if teacher_in.id:
        cursor = db.execute(
            "INSERT INTO users (id, username, full_name, hashed_password, role, teaching_title) VALUES (?, ?, ?, ?, ?, ?)",
            (teacher_in.id, teacher_in.username, teacher_in.full_name, hashed_password, UserRole.TEACHER.value, title)
        )
        new_id = teacher_in.id
    else:
        cursor = db.execute(
            "INSERT INTO users (username, full_name, hashed_password, role, teaching_title) VALUES (?, ?, ?, ?, ?)",
            (teacher_in.username, teacher_in.full_name, hashed_password, UserRole.TEACHER.value, title)
        )
        new_id = cursor.lastrowid
        
    db.commit()
    
    new_teacher = db.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    return dict(new_teacher)

@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in (UserRole.ADMIN.value, UserRole.DIRECTOR.value):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teacher = db.execute("SELECT * FROM users WHERE id = ?", (teacher_id,)).fetchone()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher["role"] != UserRole.TEACHER.value:
        raise HTTPException(status_code=400, detail="User is not a teacher")

    db.execute("DELETE FROM users WHERE id = ?", (teacher_id,))
    db.commit()
    return None
