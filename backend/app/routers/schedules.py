import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from .. import schemas
from ..database import get_db
from ..deps import require_roles, get_current_user
from ..models import UserRole

router = APIRouter(prefix="/schedules", tags=["schedules"])

def _build_schedule_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
        "id": d["sch_id"],
        "class_id": d["sch_class_id"],
        "teacher_id": d["sch_teacher_id"],
        "subject_name": d["sch_subject_name"],
        "day_of_week": d["sch_day_of_week"],
        "period": d["sch_period"],
        "class_room": {
            "id": d["cls_id"],
            "name": d["cls_name"],
            "description": d["cls_description"],
            "teacher_id": d["cls_teacher_id"],
        },
        "teacher": {
            "id": d["usr_id"],
            "username": d["usr_username"],
            "full_name": d["usr_full_name"],
            "role": d["usr_role"],
            "teaching_title": d["usr_teaching_title"],
        }
    }

query_base = """
    SELECT 
        s.id as sch_id, s.class_id as sch_class_id, s.teacher_id as sch_teacher_id, 
        s.subject_name as sch_subject_name, s.day_of_week as sch_day_of_week, s.period as sch_period,
        c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id,
        u.id as usr_id, u.username as usr_username, u.full_name as usr_full_name, 
        u.role as usr_role, u.teaching_title as usr_teaching_title
    FROM schedules s
    JOIN classes c ON s.class_id = c.id
    JOIN users u ON s.teacher_id = u.id
"""

@router.post("/", response_model=schemas.ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: schemas.ScheduleCreate,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    class_room = db.execute("SELECT id FROM classes WHERE id = ?", (payload.class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
        
    teacher = db.execute("SELECT id, role, teaching_title FROM users WHERE id = ?", (payload.teacher_id,)).fetchone()
    if not teacher or teacher["role"] != UserRole.TEACHER.value:
        raise HTTPException(status_code=400, detail="Invalid teacher ID")

    ttitle = (teacher["teaching_title"] or "").strip()
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

    conflict = db.execute(
        "SELECT class_id, subject_name FROM schedules WHERE teacher_id = ? AND day_of_week = ? AND period = ?",
        (payload.teacher_id, payload.day_of_week, payload.period)
    ).fetchone()
    
    if conflict:
        raise HTTPException(
            status_code=409, 
            detail=f"Collision detected: Teacher is already scheduled for {conflict['subject_name']} at Class ID {conflict['class_id']} on {payload.day_of_week} {payload.period}"
        )

    db.execute(
        "DELETE FROM schedules WHERE class_id = ? AND day_of_week = ? AND period = ?",
        (payload.class_id, payload.day_of_week, payload.period)
    )

    cursor = db.execute(
        "INSERT INTO schedules (class_id, teacher_id, subject_name, day_of_week, period) VALUES (?, ?, ?, ?, ?)",
        (payload.class_id, payload.teacher_id, payload.subject_name, payload.day_of_week, payload.period)
    )
    db.commit()
    
    row = db.execute(query_base + " WHERE s.id = ?", (cursor.lastrowid,)).fetchone()
    return _build_schedule_dict(row)

@router.get("/classroom/{class_id}", response_model=List[schemas.ScheduleRead])
def get_class_schedule(
    class_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    rows = db.execute(query_base + " WHERE s.class_id = ?", (class_id,)).fetchall()
    return [_build_schedule_dict(r) for r in rows]

@router.get("/my-schedule", response_model=List[schemas.ScheduleRead])
def get_my_schedule(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.TEACHER)),
):
    rows = db.execute(query_base + " WHERE s.teacher_id = ?", (current_user["id"],)).fetchall()
    return [_build_schedule_dict(r) for r in rows]

@router.get("/check-collision")
def check_schedule_collision(
    teacher_id: int,
    day_of_week: str,
    period: str,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR))
):
    conflict = db.execute(
        "SELECT class_id, subject_name FROM schedules WHERE teacher_id = ? AND day_of_week = ? AND period = ?",
        (teacher_id, day_of_week, period)
    ).fetchone()
    
    if conflict:
        return {"collision": True, "message": f"Clash: Teacher scheduled for {conflict['subject_name']} in Class {conflict['class_id']}."}
    return {"collision": False, "message": "No collision."}

@router.get("/student-subjects/{student_id}", response_model=List[schemas.ScheduleRead])
def get_student_subjects(
    student_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.PARENT, UserRole.TEACHER))
):
    student = db.execute("SELECT class_id, parent_id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if current_user["role"] == UserRole.PARENT.value and student["parent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this student")
        
    rows = db.execute(query_base + " WHERE s.class_id = ?", (student["class_id"],)).fetchall()
    return [_build_schedule_dict(r) for r in rows]
