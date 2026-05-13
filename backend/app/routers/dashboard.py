from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import Attendance, ClassRoom, Payment, PaymentStatus, Student, User
from ..models import UserRole, AttendanceStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    total_students = db.query(func.count(Student.id)).scalar() or 0
    total_classes = db.query(func.count(ClassRoom.id)).scalar() or 0
    attendance_today = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.date == date.today())
        .scalar()
        or 0
    )
    payments_pending = (
        db.query(func.count(Payment.id))
        .filter(Payment.status == PaymentStatus.PENDING)
        .scalar()
        or 0
    )
    payments_overdue = (
        db.query(func.count(Payment.id))
        .filter(Payment.status == PaymentStatus.OVERDUE)
        .scalar()
        or 0
    )
    return schemas.DashboardStats(
        total_students=total_students,
        total_classes=total_classes,
        attendance_today=attendance_today,
        payments_pending=payments_pending,
        payments_overdue=payments_overdue,
    )

@router.get("/analytics", response_model=schemas.SchoolAttendanceAnalyticsRead)
def get_attendance_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    today = date.today()
    enrolled = db.query(func.count(Student.id)).scalar() or 0

    def window_row(
        key: str, label: str, start: date, end: date
    ) -> schemas.AnalyticsWindowRead:
        present = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.date >= start,
                Attendance.date <= end,
                Attendance.status == AttendanceStatus.PRESENT,
            )
            .scalar()
            or 0
        )
        absent = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.date >= start,
                Attendance.date <= end,
                Attendance.status == AttendanceStatus.ABSENT,
            )
            .scalar()
            or 0
        )
        marked = present + absent
        if marked == 0:
            absence_pct = 0.0
            attendance_pct = 0.0
        else:
            absence_pct = round((absent / marked) * 100, 2)
            attendance_pct = round((present / marked) * 100, 2)
        return schemas.AnalyticsWindowRead(
            key=key,
            label=label,
            period_start=start,
            period_end=end,
            records_marked=marked,
            present=present,
            absent=absent,
            absence_pct=absence_pct,
            attendance_pct=attendance_pct,
        )

    windows = [
        window_row("today", "Today", today, today),
        window_row("week", "Last 7 days", today - timedelta(days=6), today),
        window_row("month", "Last 30 days", today - timedelta(days=29), today),
        window_row("year", "Last 365 days", today - timedelta(days=364), today),
    ]

    daily_trend: list[schemas.AttendanceTrendRead] = []
    for i in range(30):
        target_date = today - timedelta(days=29 - i)
        present = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.date == target_date,
                Attendance.status == AttendanceStatus.PRESENT,
            )
            .scalar()
            or 0
        )
        absent = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.date == target_date,
                Attendance.status == AttendanceStatus.ABSENT,
            )
            .scalar()
            or 0
        )
        daily_trend.append(
            schemas.AttendanceTrendRead(
                date=target_date,
                present_count=present,
                absent_count=absent,
            )
        )

    return schemas.SchoolAttendanceAnalyticsRead(
        as_of=today,
        enrolled_students=enrolled,
        windows=windows,
        daily_trend=daily_trend,
    )

@router.get("/class-metrics", response_model=List[schemas.ClassMetricRead])
def get_class_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    query = db.query(ClassRoom)
    if current_user.role == UserRole.TEACHER:
        query = query.filter(ClassRoom.teacher_id == current_user.id)
    classes = query.all()
    
    result = []
    today = date.today()
    for c in classes:
        total_students = db.query(func.count(Student.id)).filter(Student.class_id == c.id).scalar() or 0
        
        present = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.class_id == c.id, 
            Attendance.date == today, 
            Attendance.status == AttendanceStatus.PRESENT
        ).scalar() or 0
        
        absent = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.class_id == c.id, 
            Attendance.date == today, 
            Attendance.status == AttendanceStatus.ABSENT
        ).scalar() or 0
        
        result.append(schemas.ClassMetricRead(
            class_name=c.name,
            total_students=total_students,
            present_today=present,
            absent_today=absent
        ))
    return result

@router.get("/teacher/attendance-trends", response_model=List[schemas.AttendanceTrendRead])
def get_attendance_trends(
    timeframe: str = "week",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER)),
):
    today = date.today()
    if timeframe == "day":
        days_back = 1
    elif timeframe == "week":
        days_back = 7
    elif timeframe == "month":
        days_back = 30
    else:
        days_back = 7

    start_date = today - timedelta(days=days_back - 1)
    
    classes = db.query(ClassRoom).filter(ClassRoom.teacher_id == current_user.id).all()
    class_ids = [c.id for c in classes]

    if not class_ids:
        return []

    results = []
    
    for i in range(days_back):
        target_date = start_date + timedelta(days=i)
        
        present = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.class_id.in_(class_ids),
            Attendance.date == target_date,
            Attendance.status == AttendanceStatus.PRESENT
        ).scalar() or 0
        
        absent = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.class_id.in_(class_ids),
            Attendance.date == target_date,
            Attendance.status == AttendanceStatus.ABSENT
        ).scalar() or 0
        
        results.append(schemas.AttendanceTrendRead(
            date=target_date,
            present_count=present,
            absent_count=absent
        ))

    return results

@router.post("/reset-quarter", status_code=200)
def reset_quarter(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    from ..models import SubjectSchedule
    try:
        # Delete all attendance records
        db.query(Attendance).delete()
        # Delete all subject schedules
        db.query(SubjectSchedule).delete()
        db.commit()
        return {"message": "Successfully reset all attendance records and master schedules for the new quarter."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset quarter: {str(e)}")
