from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import SubjectSchedule, User, UserRole, ClassRoom, Student

router = APIRouter(prefix="/schedules", tags=["schedules"])

@router.post("/", response_model=schemas.ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: schemas.ScheduleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    # Verify Class and Teacher
    class_room = db.get(ClassRoom, payload.class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    teacher = db.get(User, payload.teacher_id)
    if not teacher or teacher.role != UserRole.TEACHER:
        raise HTTPException(status_code=400, detail="Invalid teacher ID")

    ttitle = (teacher.teaching_title or "").strip()
    subj = (payload.subject_name or "").strip()
    if not ttitle:
        raise HTTPException(
            status_code=400,
            detail="This teacher has no teaching subject on file. Set their subject specialty first.",
        )
    if subj.lower() != ttitle.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Subject '{subj}' does not match this teacher's assigned specialty '{ttitle}'. "
            "Use the same name as their teaching title (e.g. Chemistry, Mathematics).",
        )

    # Anti-collision logic: Ensure teacher isn't teaching another class at exactly the same time.
    conflict = db.query(SubjectSchedule).filter(
        SubjectSchedule.teacher_id == payload.teacher_id,
        SubjectSchedule.day_of_week == payload.day_of_week,
        SubjectSchedule.period == payload.period
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=409, 
            detail=f"Collision detected: Teacher is already scheduled for {conflict.subject_name} at Class ID {conflict.class_id} on {payload.day_of_week} {payload.period}"
        )

    # Class Collision logic: Ensure class doesn't already have a subject for this period
    class_conflict = db.query(SubjectSchedule).filter(
        SubjectSchedule.class_id == payload.class_id,
        SubjectSchedule.day_of_week == payload.day_of_week,
        SubjectSchedule.period == payload.period
    ).first()

    if class_conflict:
        db.delete(class_conflict) # Overwrite it

    db_schedule = SubjectSchedule(**payload.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.get("/classroom/{class_id}", response_model=List[schemas.ScheduleRead])
def get_class_schedule(
    class_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    return db.query(SubjectSchedule).filter(SubjectSchedule.class_id == class_id).all()

@router.get("/my-schedule", response_model=List[schemas.ScheduleRead])
def get_my_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER)),
):
    return db.query(SubjectSchedule).filter(SubjectSchedule.teacher_id == current_user.id).all()

@router.get("/check-collision")
def check_schedule_collision(
    teacher_id: int,
    day_of_week: str,
    period: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR))
):
    """Returns whether a teacher is already booked for a specific day and period."""
    conflict = db.query(SubjectSchedule).filter(
        SubjectSchedule.teacher_id == teacher_id,
        SubjectSchedule.day_of_week == day_of_week,
        SubjectSchedule.period == period
    ).first()
    
    if conflict:
        return {"collision": True, "message": f"Clash: Teacher scheduled for {conflict.subject_name} in Class {conflict.class_id}."}
    return {"collision": False, "message": "No collision."}

@router.get("/student-subjects/{student_id}", response_model=List[schemas.ScheduleRead])
def get_student_subjects(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.PARENT, UserRole.TEACHER))
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if current_user.role == UserRole.PARENT and student.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this student")
        
    # Return all schedules/subjects for the student's class
    return db.query(SubjectSchedule).filter(SubjectSchedule.class_id == student.class_id).all()


