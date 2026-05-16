from datetime import date, timedelta
from typing import List
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..database import get_db
from ..deps import require_roles, get_current_user
from ..models import UserRole, AttendanceStatus, PaymentStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    total_students = db.execute("SELECT COUNT(id) as count FROM students").fetchone()["count"]
    total_classes = db.execute("SELECT COUNT(id) as count FROM classes").fetchone()["count"]
    
    attendance_today = db.execute(
        "SELECT COUNT(id) as count FROM attendance WHERE date = ?", 
        (date.today().isoformat(),)
    ).fetchone()["count"]
    
    payments_pending = db.execute(
        "SELECT COUNT(id) as count FROM payments WHERE status = ?", 
        (PaymentStatus.PENDING.value,)
    ).fetchone()["count"]
    
    payments_overdue = db.execute(
        "SELECT COUNT(id) as count FROM payments WHERE status = ?", 
        (PaymentStatus.OVERDUE.value,)
    ).fetchone()["count"]
    
    return schemas.DashboardStats(
        total_students=total_students,
        total_classes=total_classes,
        attendance_today=attendance_today,
        payments_pending=payments_pending,
        payments_overdue=payments_overdue,
    )

@router.get("/analytics", response_model=schemas.SchoolAttendanceAnalyticsRead)
def get_attendance_analytics(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    today = date.today()
    enrolled = db.execute("SELECT COUNT(id) as count FROM students").fetchone()["count"]

    def window_row(key: str, label: str, start: date, end: date) -> schemas.AnalyticsWindowRead:
        present = db.execute(
            "SELECT COUNT(id) as count FROM attendance WHERE date >= ? AND date <= ? AND status = ?",
            (start.isoformat(), end.isoformat(), AttendanceStatus.PRESENT.value)
        ).fetchone()["count"]
        
        absent = db.execute(
            "SELECT COUNT(id) as count FROM attendance WHERE date >= ? AND date <= ? AND status = ?",
            (start.isoformat(), end.isoformat(), AttendanceStatus.ABSENT.value)
        ).fetchone()["count"]
        
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
        
        present = db.execute(
            "SELECT COUNT(id) as count FROM attendance WHERE date = ? AND status = ?",
            (target_date.isoformat(), AttendanceStatus.PRESENT.value)
        ).fetchone()["count"]
        
        absent = db.execute(
            "SELECT COUNT(id) as count FROM attendance WHERE date = ? AND status = ?",
            (target_date.isoformat(), AttendanceStatus.ABSENT.value)
        ).fetchone()["count"]
        
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
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    if current_user["role"] == UserRole.TEACHER.value:
        classes = db.execute("SELECT id, name FROM classes WHERE teacher_id = ?", (current_user["id"],)).fetchall()
    else:
        classes = db.execute("SELECT id, name FROM classes").fetchall()
    
    result = []
    today = date.today().isoformat()
    for c in classes:
        total_students = db.execute("SELECT COUNT(id) as count FROM students WHERE class_id = ?", (c["id"],)).fetchone()["count"]
        
        present = db.execute(
            "SELECT COUNT(a.id) as count FROM attendance a JOIN students s ON a.student_id = s.id WHERE s.class_id = ? AND a.date = ? AND a.status = ?",
            (c["id"], today, AttendanceStatus.PRESENT.value)
        ).fetchone()["count"]
        
        absent = db.execute(
            "SELECT COUNT(a.id) as count FROM attendance a JOIN students s ON a.student_id = s.id WHERE s.class_id = ? AND a.date = ? AND a.status = ?",
            (c["id"], today, AttendanceStatus.ABSENT.value)
        ).fetchone()["count"]
        
        result.append(schemas.ClassMetricRead(
            class_name=c["name"],
            total_students=total_students,
            present_today=present,
            absent_today=absent
        ))
    return result

@router.get("/teacher/attendance-trends", response_model=List[schemas.AttendanceTrendRead])
def get_attendance_trends(
    timeframe: str = "week",
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.TEACHER)),
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
    
    classes = db.execute("SELECT id FROM classes WHERE teacher_id = ?", (current_user["id"],)).fetchall()
    class_ids = [c["id"] for c in classes]

    if not class_ids:
        return []

    placeholders = ",".join("?" for _ in class_ids)
    results = []
    
    for i in range(days_back):
        target_date = start_date + timedelta(days=i)
        target_str = target_date.isoformat()
        
        present = db.execute(
            f"SELECT COUNT(a.id) as count FROM attendance a JOIN students s ON a.student_id = s.id WHERE s.class_id IN ({placeholders}) AND a.date = ? AND a.status = ?",
            class_ids + [target_str, AttendanceStatus.PRESENT.value]
        ).fetchone()["count"]
        
        absent = db.execute(
            f"SELECT COUNT(a.id) as count FROM attendance a JOIN students s ON a.student_id = s.id WHERE s.class_id IN ({placeholders}) AND a.date = ? AND a.status = ?",
            class_ids + [target_str, AttendanceStatus.ABSENT.value]
        ).fetchone()["count"]
        
        results.append(schemas.AttendanceTrendRead(
            date=target_date,
            present_count=present,
            absent_count=absent
        ))

    return results

@router.post("/reset-quarter", status_code=200)
def reset_quarter(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    try:
        db.execute("DELETE FROM attendance")
        db.execute("DELETE FROM schedules")
        db.commit()
        return {"message": "Successfully reset all attendance records and master schedules for the new quarter."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset quarter: {str(e)}")
