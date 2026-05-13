from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import FinancialReport, User, UserRole

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/financial", response_model=schemas.FinancialReportRead, status_code=status.HTTP_201_CREATED)
def submit_financial_report(
    payload: schemas.FinancialReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ACCOUNTANT)),
):
    # Lock the financial snapshot securely into the database
    db_report = FinancialReport(
        total_revenue=payload.total_revenue,
        pending_dues=payload.pending_dues,
        overdue_count=payload.overdue_count,
        generated_by_id=current_user.id
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/financial", response_model=List[schemas.FinancialReportRead])
def get_financial_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    # Securely retrieve all submitted financial ledgers for Director eyes only
    return db.query(FinancialReport).order_by(FinancialReport.id.desc()).all()

from sqlalchemy import func
from ..models import Attendance, AttendanceStatus, Student, ClassRoom

@router.get("/teacher/absences", response_model=List[schemas.AbsentReportRead])
def get_teacher_absences(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    class_room = db.get(ClassRoom, class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user.role == UserRole.TEACHER and class_room.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    absent_counts = db.query(
        Student.id, 
        Student.first_name, 
        Student.last_name, 
        func.count(Attendance.id).label("absent_count")
    ).outerjoin(
        Attendance, (Attendance.student_id == Student.id) & (Attendance.status == AttendanceStatus.ABSENT)
    ).filter(
        Student.class_id == class_id,
        Student.is_active == True
    ).group_by(Student.id).all()
    
    return [
        schemas.AbsentReportRead(
            student_id=r.id,
            first_name=r.first_name,
            last_name=r.last_name,
            absent_count=r.absent_count
        ) for r in absent_counts if r.absent_count > 0
    ]

@router.get("/teacher/consecutive-absences", response_model=List[schemas.ConsecutiveAbsenceRead])
def get_consecutive_absences(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    class_room = db.get(ClassRoom, class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user.role == UserRole.TEACHER and class_room.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    students = db.query(Student).filter(
        Student.class_id == class_id,
        Student.is_active == True
    ).all()
    
    result = []
    for student in students:
        records = db.query(Attendance).filter(
            Attendance.student_id == student.id
        ).order_by(Attendance.date.desc()).all()
        
        consecutive = 0
        for record in records:
            if record.status == AttendanceStatus.ABSENT:
                consecutive += 1
            else:
                break
                
        if consecutive >= 3:
            result.append(schemas.ConsecutiveAbsenceRead(
                student_id=student.id,
                first_name=student.first_name,
                last_name=student.last_name,
                consecutive_absent_days=consecutive
            ))
            
    return result

