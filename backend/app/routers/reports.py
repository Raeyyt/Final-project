from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from typing import List

from .. import schemas
from ..database import get_db
from ..deps import require_roles, get_current_user
from ..models import UserRole, AttendanceStatus

router = APIRouter(prefix="/reports", tags=["reports"])

def _build_financial_report_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
        "id": d["fr_id"],
        "total_revenue": d["fr_total_revenue"],
        "pending_dues": d["fr_pending_dues"],
        "overdue_count": d["fr_overdue_count"],
        "report_date": d["fr_report_date"],
        "generated_by": {
            "id": d["usr_id"],
            "username": d["usr_username"],
            "full_name": d["usr_full_name"],
            "role": d["usr_role"],
            "teaching_title": d["usr_teaching_title"],
        }
    }


@router.post("/financial", response_model=schemas.FinancialReportRead, status_code=status.HTTP_201_CREATED)
def submit_financial_report(
    payload: schemas.FinancialReportCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ACCOUNTANT)),
):
    cursor = db.execute(
        """
        INSERT INTO financial_reports (total_revenue, pending_dues, overdue_count, generated_by_id)
        VALUES (?, ?, ?, ?)
        """,
        (payload.total_revenue, payload.pending_dues, payload.overdue_count, current_user["id"])
    )
    db.commit()
    
    query = """
        SELECT 
            fr.id as fr_id, fr.total_revenue as fr_total_revenue, 
            fr.pending_dues as fr_pending_dues, fr.overdue_count as fr_overdue_count, 
            fr.report_date as fr_report_date,
            u.id as usr_id, u.username as usr_username, u.full_name as usr_full_name, 
            u.role as usr_role, u.teaching_title as usr_teaching_title
        FROM financial_reports fr
        JOIN users u ON fr.generated_by_id = u.id
        WHERE fr.id = ?
    """
    row = db.execute(query, (cursor.lastrowid,)).fetchone()
    return _build_financial_report_dict(row)

@router.get("/financial", response_model=List[schemas.FinancialReportRead])
def get_financial_reports(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    query = """
        SELECT 
            fr.id as fr_id, fr.total_revenue as fr_total_revenue, 
            fr.pending_dues as fr_pending_dues, fr.overdue_count as fr_overdue_count, 
            fr.report_date as fr_report_date,
            u.id as usr_id, u.username as usr_username, u.full_name as usr_full_name, 
            u.role as usr_role, u.teaching_title as usr_teaching_title
        FROM financial_reports fr
        JOIN users u ON fr.generated_by_id = u.id
        ORDER BY fr.id DESC
    """
    rows = db.execute(query).fetchall()
    return [_build_financial_report_dict(r) for r in rows]


@router.get("/teacher/absences", response_model=List[schemas.AbsentReportRead])
def get_teacher_absences(
    class_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user["role"] == UserRole.TEACHER.value and class_room["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    query = """
        SELECT s.id, s.first_name, s.last_name, 
               (SELECT COUNT(a.id) FROM attendance a WHERE a.student_id = s.id AND a.status = ?) as absent_count
        FROM students s
        WHERE s.class_id = ? AND s.is_active = 1
    """
    students = db.execute(query, (AttendanceStatus.ABSENT.value, class_id)).fetchall()
    
    return [
        schemas.AbsentReportRead(
            student_id=r["id"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            absent_count=r["absent_count"]
        ) for r in students if r["absent_count"] > 0
    ]

@router.get("/teacher/consecutive-absences", response_model=List[schemas.ConsecutiveAbsenceRead])
def get_consecutive_absences(
    class_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user["role"] == UserRole.TEACHER.value and class_room["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    students = db.execute("SELECT id, first_name, last_name FROM students WHERE class_id = ? AND is_active = 1", (class_id,)).fetchall()
    
    result = []
    for student in students:
        records = db.execute(
            "SELECT status FROM attendance WHERE student_id = ? ORDER BY date DESC",
            (student["id"],)
        ).fetchall()
        
        consecutive = 0
        for record in records:
            if record["status"] == AttendanceStatus.ABSENT.value:
                consecutive += 1
            else:
                break
                
        if consecutive >= 3:
            result.append(schemas.ConsecutiveAbsenceRead(
                student_id=student["id"],
                first_name=student["first_name"],
                last_name=student["last_name"],
                consecutive_absent_days=consecutive
            ))
            
    return result
