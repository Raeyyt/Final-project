from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
import pandas as pd
import io
import sqlite3

from .. import schemas
from ..academic import current_academic_year_label
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import UserRole, PaymentStatus

router = APIRouter(prefix="/students", tags=["students"])

def _build_student_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
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

query_base = """
    SELECT 
        s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
        s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
        s.academic_year as stu_academic_year, s.is_active as stu_is_active,
        c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
    FROM students s
    JOIN classes c ON s.class_id = c.id
    WHERE 1=1
"""

@router.get("/meta/defaults")
def enrollment_defaults(current_user: dict = Depends(get_current_user)):
    return {"default_academic_year": current_academic_year_label()}

@router.get("/meta/academic-years")
def list_distinct_academic_years(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    rows = db.execute("SELECT DISTINCT academic_year FROM students").fetchall()
    years = sorted({r["academic_year"] for r in rows if r["academic_year"]}, reverse=True)
    return {"academic_years": years}

@router.get("/", response_model=list[schemas.StudentRead])
def list_students(
    academic_year: str | None = Query(None, description="Filter by academic year (admin/director only)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(
        require_roles(UserRole.ADMIN, UserRole.TEACHER, UserRole.ACCOUNTANT, UserRole.DIRECTOR, UserRole.PARENT)
    ),
):
    query = query_base
    params = []

    if current_user["role"] == UserRole.TEACHER.value:
        query += " AND c.teacher_id = ?"
        params.append(current_user["id"])
    elif current_user["role"] == UserRole.PARENT.value:
        query += " AND s.parent_id = ?"
        params.append(current_user["id"])

    if academic_year and academic_year.strip() and current_user["role"] in (UserRole.ADMIN.value, UserRole.DIRECTOR.value):
        query += " AND s.academic_year = ?"
        params.append(academic_year.strip())

    rows = db.execute(query, params).fetchall()
    return [_build_student_dict(r) for r in rows]

@router.post("/", response_model=schemas.StudentCreatedRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.StudentCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (payload.class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
    if not class_room["teacher_id"]:
        raise HTTPException(status_code=400, detail="Cannot assign student to a class with no assigned teacher")

    ay = (payload.academic_year or "").strip() or current_academic_year_label()
    
    duplicate = db.execute(
        "SELECT id FROM students WHERE LOWER(first_name) = LOWER(?) AND LOWER(last_name) = LOWER(?) AND academic_year = ?",
        (payload.first_name, payload.last_name, ay)
    ).fetchone()
    if duplicate:
        raise HTTPException(status_code=400, detail=f"A student with the name '{payload.first_name} {payload.last_name}' is already registered for the academic year '{ay}'.")

    is_active = 0 if payload.create_registration_invoice else 1

    cursor = db.execute(
        "INSERT INTO students (first_name, last_name, class_id, teacher_id, parent_id, academic_year, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (payload.first_name, payload.last_name, payload.class_id, class_room["teacher_id"], payload.parent_id, ay, is_active)
    )
    student_id = cursor.lastrowid

    registration_payment_id = None
    if payload.create_registration_invoice:
        due = (date.today() + timedelta(days=14)).isoformat()
        cursor = db.execute(
            "INSERT INTO payments (student_id, amount_due, amount_paid, due_date, status, recorded_by, invoice_title) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (student_id, 0.0, 0.0, due, PaymentStatus.PENDING.value, current_user["id"], "Registration fee")
        )
        registration_payment_id = cursor.lastrowid
        
    db.commit()

    row = db.execute(query_base + " AND s.id = ?", (student_id,)).fetchone()
    res = _build_student_dict(row)
    res["registration_payment_id"] = registration_payment_id
    return res

@router.post("/{student_id}/re-enroll", response_model=schemas.StudentRead)
def re_enroll_student(
    student_id: int,
    payload: schemas.StudentReEnroll,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (payload.class_id,)).fetchone()
    if not class_room:
        raise HTTPException(status_code=404, detail="Target class not found")
    if not class_room["teacher_id"]:
        raise HTTPException(status_code=400, detail="Target class has no assigned teacher")

    db.execute(
        "UPDATE students SET class_id = ?, teacher_id = ?, academic_year = ? WHERE id = ?",
        (payload.class_id, class_room["teacher_id"], payload.academic_year.strip(), student_id)
    )
    db.commit()
    
    row = db.execute(query_base + " AND s.id = ?", (student_id,)).fetchone()
    return _build_student_dict(row)

@router.patch("/{student_id}", response_model=schemas.StudentRead)
def update_student(
    student_id: int,
    payload: schemas.StudentUpdate,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    student = dict(student)
    update_data = payload.model_dump(exclude_unset=True)

    if "class_id" in update_data:
        class_room = db.execute("SELECT teacher_id FROM classes WHERE id = ?", (update_data["class_id"],)).fetchone()
        if not class_room:
            raise HTTPException(status_code=404, detail="Target class not found")
        if not class_room["teacher_id"]:
            raise HTTPException(status_code=400, detail="Target class has no assigned teacher")

        student["class_id"] = update_data["class_id"]
        student["teacher_id"] = class_room["teacher_id"]

    if "first_name" in update_data: student["first_name"] = update_data["first_name"]
    if "last_name" in update_data: student["last_name"] = update_data["last_name"]
    if "parent_id" in update_data: student["parent_id"] = update_data["parent_id"]
    if "academic_year" in update_data and update_data["academic_year"] is not None:
        student["academic_year"] = update_data["academic_year"].strip()

    db.execute(
        "UPDATE students SET first_name=?, last_name=?, class_id=?, teacher_id=?, parent_id=?, academic_year=? WHERE id=?",
        (student["first_name"], student["last_name"], student["class_id"], student["teacher_id"], student["parent_id"], student["academic_year"], student_id)
    )
    db.commit()

    row = db.execute(query_base + " AND s.id = ?", (student_id,)).fetchone()
    return _build_student_dict(row)


@router.get("/{student_id}", response_model=schemas.StudentRead)
def get_student(
    student_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(
        require_roles(UserRole.ADMIN, UserRole.TEACHER, UserRole.ACCOUNTANT, UserRole.DIRECTOR, UserRole.PARENT)
    ),
):
    row = db.execute(query_base + " AND s.id = ?", (student_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
        
    d = _build_student_dict(row)
    if current_user["role"] == UserRole.TEACHER.value and d["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to view this student")
    if current_user["role"] == UserRole.PARENT.value and d["parent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to view this child")
    return d

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return None

@router.post("/bulk-upload", status_code=status.HTTP_201_CREATED)
def bulk_upload_students(
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are allowed.")
    
    try:
        contents = file.file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        required_cols = ["first_name", "last_name", "class_id"]
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
        
        created_count = 0
        skipped_reasons = []
        
        for idx, row in df.iterrows():
            class_identifier = str(row["class_id"]).strip()
            
            if class_identifier.isdigit():
                class_room = db.execute("SELECT id, teacher_id FROM classes WHERE id = ?", (int(class_identifier),)).fetchone()
            else:
                class_room = db.execute("SELECT id, teacher_id FROM classes WHERE name = ?", (class_identifier,)).fetchone()
                
            if not class_room:
                skipped_reasons.append(f"Class '{class_identifier}' not found")
                continue
            if not class_room["teacher_id"]:
                skipped_reasons.append(f"Class '{class_identifier}' has no assigned teacher")
                continue
            
            ay = current_academic_year_label()
            if "academic_year" in df.columns and pd.notna(row["academic_year"]):
                ay = str(row["academic_year"]).strip()
                
            db.execute(
                "INSERT INTO students (first_name, last_name, class_id, teacher_id, academic_year, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                (str(row["first_name"]).strip(), str(row["last_name"]).strip(), class_room["id"], class_room["teacher_id"], ay)
            )
            created_count += 1
            
        db.commit()
        
        msg = f"Successfully uploaded and created {created_count} students."
        if skipped_reasons:
            unique_reasons = list(set(skipped_reasons))
            msg += f" Skipped {len(skipped_reasons)} rows. Reasons: " + ", ".join(unique_reasons)
            
        return {"message": msg}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
