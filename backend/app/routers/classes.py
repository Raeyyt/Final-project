from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import ClassRoom, User, UserRole

router = APIRouter(prefix="/classes", tags=["classes"])

@router.get("/", response_model=list[schemas.ClassRead])
def get_classes(db: Session = Depends(get_db)):
    return db.query(ClassRoom).all()

@router.post("/", response_model=schemas.ClassRead, status_code=status.HTTP_201_CREATED)
def create_class(
    class_in: schemas.ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing_class = db.query(ClassRoom).filter(ClassRoom.name == class_in.name).first()
    if existing_class:
        raise HTTPException(status_code=400, detail="Class already exists")

    new_class = ClassRoom(**class_in.model_dump())
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class

@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    class_room = db.get(ClassRoom, class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
    
    from sqlalchemy.exc import IntegrityError
    try:
        db.delete(class_room)
        db.commit()
    except IntegrityError:
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    class_room = db.get(ClassRoom, class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    update_data = class_in.model_dump(exclude_unset=True)
    
    if "teacher_id" in update_data:
        t_id = update_data["teacher_id"]
        if t_id is not None:
            teacher = db.get(User, t_id)
            if not teacher or teacher.role != UserRole.TEACHER:
                raise HTTPException(status_code=400, detail="Invalid teacher")
            
            existing = db.query(ClassRoom).filter(ClassRoom.teacher_id == t_id).first()
            if existing and existing.id != class_id:
                raise HTTPException(status_code=400, detail="Teacher is already managing another class")
                
        class_room.teacher_id = t_id

    if "name" in update_data and update_data["name"] is not None:
        class_room.name = update_data["name"]
    if "description" in update_data and update_data["description"] is not None:
        class_room.description = update_data["description"]

    db.add(class_room)
    db.commit()
    db.refresh(class_room)
    return class_room

from pydantic import BaseModel
class PromotePayload(BaseModel):
    academic_year: str

@router.post("/{from_class_id}/promote/{to_class_id}", status_code=status.HTTP_200_OK)
def promote_class(
    from_class_id: int,
    to_class_id: int,
    payload: PromotePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    from_class = db.get(ClassRoom, from_class_id)
    to_class = db.get(ClassRoom, to_class_id)
    
    if not from_class or not to_class:
        raise HTTPException(status_code=404, detail="Source or target class not found")
        
    if not to_class.teacher_id:
        raise HTTPException(status_code=400, detail="Target class has no assigned teacher")
        
    from ..models import Student
    
    students = db.query(Student).filter(
        Student.class_id == from_class_id,
        Student.is_active == True
    ).all()
    
    if not students:
        return {"message": "No active students found in the source class to promote."}
        
    promoted_count = 0
    for student in students:
        student.class_id = to_class_id
        student.teacher_id = to_class.teacher_id
        student.academic_year = payload.academic_year.strip()
        db.add(student)
        promoted_count += 1
        
    db.commit()
    return {"message": f"Successfully promoted {promoted_count} students to {to_class.name}."}

