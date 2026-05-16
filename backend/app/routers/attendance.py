from datetime import date
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..database import get_db
from ..deps import require_roles, get_current_user
from ..models import UserRole

router = APIRouter(prefix="/attendance", tags=["attendance"])

def _build_attendance_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
        "id": d["att_id"],
        "student_id": d["att_student_id"],
        "status": d["att_status"],
        "date": d["att_date"],
        "recorded_by": d["att_recorded_by"],
        "created_at": d["att_created_at"],
        "student": {
            "id": d["stu_id"],
            "first_name": d["stu_first_name"],
            "last_name": d["stu_last_name"],
            "class_id": d["stu_class_id"],
            "teacher_id": d["stu_teacher_id"],
            "parent_id": d["stu_parent_id"],
            "academic_year": d["stu_academic_year"],
            "is_active": bool(d["stu_is_active"]),
            "class_room": {
                "id": d["cls_id"],
                "name": d["cls_name"],
                "description": d["cls_description"],
                "teacher_id": d["cls_teacher_id"],
            }
        }
    }

@router.get("/", response_model=list[schemas.AttendanceRead])
def list_attendance(
    query_date: date | None = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER, UserRole.PARENT)),
):
    query = """
        SELECT 
            a.id as att_id, a.student_id as att_student_id, a.status as att_status, 
            a.date as att_date, a.recorded_by as att_recorded_by, a.created_at as att_created_at,
            s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
            s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
            s.academic_year as stu_academic_year, s.is_active as stu_is_active,
            c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []
    
    if query_date:
        query += " AND a.date = ?"
        params.append(query_date)
        
    if current_user["role"] == UserRole.TEACHER.value:
        query += " AND c.teacher_id = ?"
        params.append(current_user["id"])
    elif current_user["role"] == UserRole.PARENT.value:
        query += " AND s.parent_id = ?"
        params.append(current_user["id"])
        
    query += " ORDER BY a.date DESC"
    
    rows = db.execute(query, params).fetchall()
    return [_build_attendance_dict(r) for r in rows]


@router.post("/", response_model=schemas.AttendanceRead, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: schemas.AttendanceCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    student = db.execute("SELECT * FROM students WHERE id = ?", (payload.student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (student["class_id"],)).fetchone()
    if current_user["role"] == UserRole.TEACHER.value and class_room["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot mark this student")

    target_date = payload.date or date.today()
    record = db.execute(
        "SELECT id FROM attendance WHERE student_id = ? AND date = ?", 
        (payload.student_id, target_date)
    ).fetchone()

    if record:
        db.execute(
            "UPDATE attendance SET status = ?, recorded_by = ? WHERE id = ?",
            (payload.status.value, current_user["id"], record["id"])
        )
        db.commit()
        att_id = record["id"]
    else:
        try:
            cursor = db.execute(
                "INSERT INTO attendance (student_id, status, date, recorded_by) VALUES (?, ?, ?, ?)",
                (payload.student_id, payload.status.value, target_date, current_user["id"])
            )
            db.commit()
            att_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400, detail="Constraints error marking attendance"
            ) from None

    # Fetch the full record to return
    query = """
        SELECT 
            a.id as att_id, a.student_id as att_student_id, a.status as att_status, 
            a.date as att_date, a.recorded_by as att_recorded_by, a.created_at as att_created_at,
            s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
            s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
            s.academic_year as stu_academic_year, s.is_active as stu_is_active,
            c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE a.id = ?
    """
    row = db.execute(query, (att_id,)).fetchone()
    return _build_attendance_dict(row)


@router.get("/daily-summary", response_model=list[schemas.DailyAttendanceSummaryRead])
def get_daily_summary(
    class_id: int,
    target_date: date = None,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)),
):
    if target_date is None:
        target_date = date.today()
        
    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    if current_user["role"] == UserRole.TEACHER.value and class_room["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")
        
    students = db.execute(
        "SELECT id, first_name, last_name FROM students WHERE class_id = ? AND is_active = 1 ORDER BY first_name, last_name",
        (class_id,)
    ).fetchall()
    
    if not students:
        return []
        
    student_ids = [s["id"] for s in students]
    placeholders = ",".join("?" for _ in student_ids)
    
    attendance_records = db.execute(
        f"SELECT student_id, status FROM attendance WHERE date = ? AND student_id IN ({placeholders})",
        [target_date] + student_ids
    ).fetchall()
    
    att_map = {r["student_id"]: r["status"] for r in attendance_records}
    
    result = []
    for student in students:
        result.append(schemas.DailyAttendanceSummaryRead(
            student_id=student["id"],
            first_name=student["first_name"],
            last_name=student["last_name"],
            status=att_map.get(student["id"])
        ))
        
    return result
