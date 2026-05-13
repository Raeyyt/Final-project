from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import engine
from ..deps import get_db, get_current_user
from ..models import User, UserRole
from ..security import get_password_hash

router = APIRouter(prefix="/teachers", tags=["teachers"])

@router.get("/", response_model=List[schemas.UserRead])
def get_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    return teachers

@router.post("/", response_model=schemas.UserRead)
def create_teacher(
    teacher_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Force role to TEACHER if not set or incorrect (though schema has it)
    if teacher_in.role != UserRole.TEACHER:
         raise HTTPException(status_code=400, detail="Can only create teachers here")

    title = (teacher_in.teaching_title or "").strip()
    if not title:
        raise HTTPException(
            status_code=400,
            detail="Teaching title (subject specialty) is required for teachers",
        )

    existing_user = db.query(User).filter(User.username == teacher_in.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    if teacher_in.id:
        existing_id = db.get(User, teacher_in.id)
        if existing_id:
            raise HTTPException(status_code=400, detail="User ID already exists")

    hashed_password = get_password_hash(teacher_in.password)
    new_teacher = User(
        id=teacher_in.id,
        username=teacher_in.username,
        full_name=teacher_in.full_name,
        hashed_password=hashed_password,
        role=UserRole.TEACHER,
        teaching_title=title,
    )
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return new_teacher

@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.DIRECTOR):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    teacher = db.get(User, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.role != UserRole.TEACHER:
        raise HTTPException(status_code=400, detail="User is not a teacher")

    db.delete(teacher)
    db.commit()
    return None
