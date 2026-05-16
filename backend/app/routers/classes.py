import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import UserRole

router = APIRouter(prefix="/classes", tags=["classes"])

@router.get("/", response_model=list[schemas.ClassRead])
def get_classes(db: sqlite3.Connection = Depends(get_db)):
    classes = db.execute("SELECT * FROM classes").fetchall()
    return [dict(c) for c in classes]

@router.post("/", response_model=schemas.ClassRead, status_code=status.HTTP_201_CREATED)
def create_class(
    class_in: schemas.ClassCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.DIRECTOR.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing_class = db.execute("SELECT id FROM classes WHERE name = ?", (class_in.name,)).fetchone()
    if existing_class:
        raise HTTPException(status_code=400, detail="Class already exists")

    cursor = db.execute(
        "INSERT INTO classes (name, teacher_id) VALUES (?, ?)",
        (class_in.name, class_in.teacher_id)
    )
    db.commit()
    
    new_class = db.execute("SELECT * FROM classes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(new_class)

@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.DIRECTOR.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    class_room = db.execute("SELECT id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
    
    try:
        db.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete this class securely because it natively houses active enrolled students."
        )
    return None

@router.patch("/{class_id}", response_model=schemas.ClassRead)
def update_class(
    class_id: int,
    class_in: schemas.ClassUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.DIRECTOR.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    class_room = db.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    class_room = dict(class_room)
    update_data = class_in.model_dump(exclude_unset=True)
    
    if "teacher_id" in update_data:
        t_id = update_data["teacher_id"]
        if t_id is not None:
            teacher = db.execute("SELECT id, role FROM users WHERE id = ?", (t_id,)).fetchone()
            if not teacher or teacher["role"] != UserRole.TEACHER.value:
                raise HTTPException(status_code=400, detail="Invalid teacher")
            
            existing = db.execute("SELECT id FROM classes WHERE teacher_id = ?", (t_id,)).fetchone()
            if existing and existing["id"] != class_id:
                raise HTTPException(status_code=400, detail="Teacher is already managing another class")
                
        class_room["teacher_id"] = t_id

    if "name" in update_data and update_data["name"] is not None:
        class_room["name"] = update_data["name"]

    db.execute(
        "UPDATE classes SET name = ?, teacher_id = ? WHERE id = ?",
        (class_room["name"], class_room["teacher_id"], class_id)
    )
    db.commit()
    
    updated_class = db.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    return dict(updated_class)

from pydantic import BaseModel
class PromotePayload(BaseModel):
    academic_year: str

@router.post("/{from_class_id}/promote/{to_class_id}", status_code=status.HTTP_200_OK)
def promote_class(
    from_class_id: int,
    to_class_id: int,
    payload: PromotePayload,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.DIRECTOR.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    from_class = db.execute("SELECT * FROM classes WHERE id = ?", (from_class_id,)).fetchone()
    to_class = db.execute("SELECT * FROM classes WHERE id = ?", (to_class_id,)).fetchone()
    
    if not from_class or not to_class:
        raise HTTPException(status_code=404, detail="Source or target class not found")
        
    if not to_class["teacher_id"]:
        raise HTTPException(status_code=400, detail="Target class has no assigned teacher")
        
    students = db.execute(
        "SELECT id FROM students WHERE class_id = ? AND is_active = 1", 
        (from_class_id,)
    ).fetchall()
    
    if not students:
        return {"message": "No active students found in the source class to promote."}
        
    promoted_count = 0
    for student in students:
        db.execute(
            "UPDATE students SET class_id = ?, teacher_id = ?, academic_year = ? WHERE id = ?",
            (to_class_id, to_class["teacher_id"], payload.academic_year.strip(), student["id"])
        )
        promoted_count += 1
        
    db.commit()
    return {"message": f"Successfully promoted {promoted_count} students to {to_class['name']}."}
