from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import UserRole, PaymentStatus

router = APIRouter(prefix="/payments", tags=["payments"])

from datetime import date, timedelta
from pydantic import BaseModel
import urllib.request
import urllib.error
import json
import time
import os

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                try:
                    key, val = line.strip().split('=', 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
                except ValueError:
                    pass

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY", "missing_key")

def _build_payment_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
        "id": d["pay_id"],
        "student_id": d["pay_student_id"],
        "amount_due": d["pay_amount_due"],
        "amount_paid": d["pay_amount_paid"],
        "due_date": d["pay_due_date"],
        "status": d["pay_status"],
        "transaction_id": d["pay_transaction_id"],
        "invoice_title": d["pay_invoice_title"],
        "recorded_by": d["pay_recorded_by"],
        "updated_at": d["pay_updated_at"],
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


@router.get("/", response_model=list[schemas.PaymentRead])
def list_payments(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.PARENT, UserRole.DIRECTOR)),
):
    today = date.today().isoformat()
    overdue_threshold = (date.today() - timedelta(days=10)).isoformat()
    
    db.execute(
        """
        UPDATE payments 
        SET status = ?, amount_due = amount_due * 1.05 
        WHERE status = ? AND due_date < ?
        """,
        (PaymentStatus.OVERDUE.value, PaymentStatus.PENDING.value, overdue_threshold)
    )
    db.commit()

    query = """
        SELECT 
            p.id as pay_id, p.student_id as pay_student_id, p.amount_due as pay_amount_due, 
            p.amount_paid as pay_amount_paid, p.due_date as pay_due_date, p.status as pay_status, 
            p.transaction_id as pay_transaction_id, p.invoice_title as pay_invoice_title, 
            p.recorded_by as pay_recorded_by, p.updated_at as pay_updated_at,
            s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
            s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
            s.academic_year as stu_academic_year, s.is_active as stu_is_active,
            c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
        FROM payments p
        JOIN students s ON p.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []
    
    if current_user["role"] == UserRole.PARENT.value:
        query += " AND s.parent_id = ?"
        params.append(current_user["id"])
        
    query += " ORDER BY p.due_date DESC"
    
    rows = db.execute(query, params).fetchall()
    return [_build_payment_dict(r) for r in rows]


@router.post("/", response_model=schemas.PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: schemas.PaymentCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    student = db.execute("SELECT id FROM students WHERE id = ?", (payload.student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    cursor = db.execute(
        """
        INSERT INTO payments 
        (student_id, amount_due, amount_paid, due_date, status, invoice_title, recorded_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (payload.student_id, payload.amount_due, payload.amount_paid, payload.due_date, 
         payload.status.value, payload.invoice_title, current_user["id"])
    )
    db.commit()
    pay_id = cursor.lastrowid
    
    query = """
        SELECT 
            p.id as pay_id, p.student_id as pay_student_id, p.amount_due as pay_amount_due, 
            p.amount_paid as pay_amount_paid, p.due_date as pay_due_date, p.status as pay_status, 
            p.transaction_id as pay_transaction_id, p.invoice_title as pay_invoice_title, 
            p.recorded_by as pay_recorded_by, p.updated_at as pay_updated_at,
            s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
            s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
            s.academic_year as stu_academic_year, s.is_active as stu_is_active,
            c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
        FROM payments p
        JOIN students s ON p.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE p.id = ?
    """
    row = db.execute(query, (pay_id,)).fetchone()
    return _build_payment_dict(row)


class GenerateInvoicePayload(BaseModel):
    class_id: int
    start_date: date
    amount: float

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_quarterly_invoices(
    payload: GenerateInvoicePayload,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.DIRECTOR))
):
    target_class = db.execute("SELECT name FROM classes WHERE id = ?", (payload.class_id,)).fetchone()
    if not target_class:
        raise HTTPException(status_code=404, detail="Isolated target class not found in system")
        
    students = db.execute("SELECT id FROM students WHERE class_id = ?", (payload.class_id,)).fetchall()
    
    if not students:
        raise HTTPException(status_code=400, detail="Target class has zero explicitly enrolled students")
    
    created_count = 0
    for student in students:
        db.execute(
            """
            INSERT INTO payments (student_id, amount_due, due_date, status, recorded_by) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (student["id"], payload.amount, payload.start_date, PaymentStatus.PENDING.value, current_user["id"])
        )
        created_count += 1
            
    db.commit()
    return {"message": f"Successfully mapped {created_count} isolated quarter invoices specific to {target_class['name']}."}


@router.patch("/{payment_id}", response_model=schemas.PaymentRead)
def update_payment(
    payment_id: int,
    payload: schemas.PaymentUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    payment = db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    payment = dict(payment)
    
    if payload.amount_paid is not None:
        payment["amount_paid"] = payload.amount_paid
    if payload.status is not None:
        payment["status"] = payload.status.value
        if payload.status.value == PaymentStatus.PAID.value and payment["invoice_title"] == "Registration fee":
            db.execute("UPDATE students SET is_active = 1 WHERE id = ?", (payment["student_id"],))

    if payload.amount_due is not None:
        payment["amount_due"] = payload.amount_due
    if payload.due_date is not None:
        payment["due_date"] = payload.due_date

    db.execute(
        "UPDATE payments SET amount_paid = ?, status = ?, amount_due = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (payment["amount_paid"], payment["status"], payment["amount_due"], payment["due_date"], payment_id)
    )
    db.commit()
    
    query = """
        SELECT 
            p.id as pay_id, p.student_id as pay_student_id, p.amount_due as pay_amount_due, 
            p.amount_paid as pay_amount_paid, p.due_date as pay_due_date, p.status as pay_status, 
            p.transaction_id as pay_transaction_id, p.invoice_title as pay_invoice_title, 
            p.recorded_by as pay_recorded_by, p.updated_at as pay_updated_at,
            s.id as stu_id, s.first_name as stu_first_name, s.last_name as stu_last_name, 
            s.class_id as stu_class_id, s.teacher_id as stu_teacher_id, s.parent_id as stu_parent_id, 
            s.academic_year as stu_academic_year, s.is_active as stu_is_active,
            c.id as cls_id, c.name as cls_name, c.description as cls_description, c.teacher_id as cls_teacher_id
        FROM payments p
        JOIN students s ON p.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE p.id = ?
    """
    row = db.execute(query, (payment_id,)).fetchone()
    return _build_payment_dict(row)


def _chapa_customization_text(raw: str | None, max_len: int, fallback: str = "Payment") -> str:
    if not raw or not str(raw).strip():
        return fallback[:max_len]
    s = str(raw).strip()
    for bad, good in (
        ("\u2014", "-"), 
        ("\u2013", "-"), 
        ("\u2212", "-"), 
    ):
        s = s.replace(bad, good)
    out: list[str] = []
    for ch in s:
        if ch.isalnum() or ch in "._- ":
            out.append(ch)
        elif ch.isspace():
            out.append(" ")
    s = "".join(out)
    s = " ".join(s.split())
    return (s or fallback)[:max_len]


@router.post("/{payment_id}/chapa-initiate", response_model=dict)
def chapa_initiate(
    payment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.PARENT))
):
    payment = db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    student = db.execute("SELECT parent_id, first_name, last_name FROM students WHERE id = ?", (payment["student_id"],)).fetchone()
        
    if student["parent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")

    if payment["status"] == PaymentStatus.PAID.value:
        raise HTTPException(status_code=400, detail="Payment is already resolved")

    tx_ref = f"FEE_{payment['id']}_{int(time.time())}"
    db.execute("UPDATE payments SET transaction_id = ? WHERE id = ?", (tx_ref, payment_id))
    db.commit()
    
    first_name = current_user["full_name"].split()[0]
    last_name = current_user["full_name"].split()[-1] if " " in current_user["full_name"] else "Parent"
    
    safe_email = "testparent@gmail.com"
    
    fee_label = (payment["invoice_title"] or "School fee").strip() or "School fee"
    name_part = f"{student['first_name']} {student['last_name']}".strip()
    desc_raw = f"{fee_label} - {name_part}".strip() if name_part else fee_label

    payload = json.dumps({
        "amount": str(payment["amount_due"]),
        "currency": "ETB",
        "email": safe_email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "customization": {
            "title": _chapa_customization_text(fee_label, 50, "School fee"),
            "description": _chapa_customization_text(desc_raw, 120, "School fee payment"),
        },
    }).encode("utf-8")
    
    req = urllib.request.Request("https://api.chapa.co/v1/transaction/initialize", data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {CHAPA_SECRET_KEY}")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                return {"checkout_url": res_data["data"]["checkout_url"], "tx_ref": tx_ref}
            else:
                raise HTTPException(status_code=400, detail=res_data.get("message", "Chapa initialization failed"))
    except urllib.error.HTTPError as e:
        error_info = e.read().decode()
        if e.code == 401:
            raise HTTPException(status_code=502, detail="Invalid Chapa Secret Key configured natively in the backend .env file.")
        raise HTTPException(status_code=e.code, detail=f"Chapa API Error: {error_info}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.get("/chapa-verify/{tx_ref}", response_model=dict)
def chapa_verify(
    tx_ref: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.PARENT, UserRole.ACCOUNTANT))
):
    try:
        payment_id = int(tx_ref.split("_")[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid transaction reference format")
        
    payment = db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found natively")
        
    student = db.execute("SELECT parent_id FROM students WHERE id = ?", (payment["student_id"],)).fetchone()
        
    if current_user["role"] == UserRole.PARENT.value and student["parent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to verify this payment")
        
    req = urllib.request.Request(f"https://api.chapa.co/v1/transaction/verify/{tx_ref}")
    req.add_header("Authorization", f"Bearer {CHAPA_SECRET_KEY}")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            api_status = res_data.get("status")
            tx_status = res_data.get("data", {}).get("status")
            
            if api_status == "success" and tx_status == "success":
                verified_amount = float(res_data["data"]["amount"])
                
                db.execute(
                    "UPDATE payments SET status = ?, amount_paid = ? WHERE id = ?",
                    (PaymentStatus.PAID.value, verified_amount, payment_id)
                )
                if payment["invoice_title"] == "Registration fee":
                    db.execute("UPDATE students SET is_active = 1 WHERE id = ?", (payment["student_id"],))
                db.commit()
                return {"status": "PAID", "message": "Transaction verified securely."}
            else:
                return {"status": "PENDING", "message": "Transaction verification failed or abandoned."}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=401, detail="Invalid Chapa Secret Key during verification.")
        raise HTTPException(status_code=400, detail="Chapa record not found or error pinging gateway.")
