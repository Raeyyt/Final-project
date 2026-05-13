from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import Attendance, Student, User, UserRole, ClassRoom

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/", response_model=list[schemas.AttendanceRead])
def list_attendance(
    query_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER, UserRole.PARENT)),
):
    attendance_query = db.query(Attendance)
    if query_date:
        attendance_query = attendance_query.filter(Attendance.date == query_date)
    if current_user.role == UserRole.TEACHER:
        attendance_query = attendance_query.join(Attendance.student).join(Student.class_room).filter(
            ClassRoom.teacher_id == current_user.id
        )
    elif current_user.role == UserRole.PARENT:
        attendance_query = attendance_query.join(Attendance.student).filter(
            Student.parent_id == current_user.id
        )
    return attendance_query.order_by(Attendance.date.desc()).all()


@router.post("/", response_model=schemas.AttendanceRead, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: schemas.AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == UserRole.TEACHER and student.class_room.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot mark this student")

    target_date = payload.date or date.today()
    record = db.query(Attendance).filter(
        Attendance.student_id == payload.student_id,
        Attendance.date == target_date
    ).first()

    if record:
        record.status = payload.status
        record.recorded_by = current_user.id
        db.commit()
        db.refresh(record)
        return record

    record = Attendance(
        student_id=payload.student_id,
        status=payload.status,
        date=target_date,
        recorded_by=current_user.id,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Constraints error marking attendance"
        ) from None

    return record

@router.get("/daily-summary", response_model=list[schemas.DailyAttendanceSummaryRead])
def get_daily_summary(
    class_id: int,
    target_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    if target_date is None:
        target_date = date.today()
        
    class_room = db.get(ClassRoom, class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user.role == UserRole.TEACHER and class_room.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    students = db.query(Student).filter(
        Student.class_id == class_id,
        Student.is_active == True
    ).order_by(Student.first_name, Student.last_name).all()
    
    attendance_records = db.query(Attendance).filter(
        Attendance.date == target_date,
        Attendance.student_id.in_([s.id for s in students]) if students else False
    ).all()
    
    att_map = {r.student_id: r.status for r in attendance_records}
    
    result = []
    for student in students:
        result.append(schemas.DailyAttendanceSummaryRead(
            student_id=student.id,
            first_name=student.first_name,
            last_name=student.last_name,
            status=att_map.get(student.id)
        ))
        
    return result
