from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import require_roles
from ..models import Payment, Student, User, UserRole

router = APIRouter(prefix="/payments", tags=["payments"])


from datetime import date, timedelta
from pydantic import BaseModel
from ..models import PaymentStatus

@router.get("/", response_model=list[schemas.PaymentRead])
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.PARENT, UserRole.DIRECTOR)),
):
    # Lazy 10-day Overdue Logic Penalty Engine
    today = date.today()
    overdue_threshold = today - timedelta(days=10)
    
    db.query(Payment).filter(
        Payment.status == PaymentStatus.PENDING,
        Payment.due_date < overdue_threshold
    ).update({
        "status": PaymentStatus.OVERDUE,
        "amount_due": Payment.amount_due * 1.05
    }, synchronize_session=False)
    db.commit()

    query = db.query(Payment)
    if current_user.role == UserRole.PARENT:
        query = query.join(Payment.student).filter(Student.parent_id == current_user.id)
    return query.order_by(Payment.due_date.desc()).all()


@router.post("/", response_model=schemas.PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    payment = Payment(
        **payload.model_dump(),
        recorded_by=current_user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

class GenerateInvoicePayload(BaseModel):
    class_id: int
    start_date: date
    amount: float

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_quarterly_invoices(
    payload: GenerateInvoicePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.DIRECTOR))
):
    from ..models import ClassRoom
    
    target_class = db.get(ClassRoom, payload.class_id)
    if not target_class:
        raise HTTPException(status_code=404, detail="Isolated target class not found in system")
        
    students = db.query(Student).filter(Student.class_id == payload.class_id).all()
    
    if not students:
        raise HTTPException(status_code=400, detail="Target class has zero explicitly enrolled students")
    
    created_count = 0
    for student in students:
        payment = Payment(
            student_id=student.id,
            amount_due=payload.amount,
            due_date=payload.start_date,
            status=PaymentStatus.PENDING,
            recorded_by=current_user.id
        )
        db.add(payment)
        created_count += 1
            
    db.commit()
    return {"message": f"Successfully mapped {created_count} isolated quarter invoices specific to {target_class.name}."}


@router.patch("/{payment_id}", response_model=schemas.PaymentRead)
def update_payment(
    payment_id: int,
    payload: schemas.PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payload.amount_paid is not None:
        payment.amount_paid = payload.amount_paid
    if payload.status is not None:
        payment.status = payload.status
        if payload.status == PaymentStatus.PAID and payment.invoice_title == "Registration fee":
            payment.student.is_active = True
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

import urllib.request
import urllib.error
import urllib.parse
import json
import time
import os

# Natively load .env relative to backend root
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


def _chapa_customization_text(raw: str | None, max_len: int, fallback: str = "Payment") -> str:
    """Chapa only allows letters, numbers, hyphens, underscores, spaces, and dots."""
    if not raw or not str(raw).strip():
        return fallback[:max_len]
    s = str(raw).strip()
    for bad, good in (
        ("\u2014", "-"),  # em dash
        ("\u2013", "-"),  # en dash
        ("\u2212", "-"),  # minus sign
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PARENT))
):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    if payment.student.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")

    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Payment is already resolved")

    tx_ref = f"FEE_{payment.id}_{int(time.time())}"
    payment.transaction_id = tx_ref
    db.commit()
    
    first_name = current_user.full_name.split()[0]
    last_name = current_user.full_name.split()[-1] if " " in current_user.full_name else "Parent"
    
    safe_email = "testparent@gmail.com"
    
    fee_label = (payment.invoice_title or "School fee").strip() or "School fee"
    stu = payment.student
    name_part = f"{stu.first_name} {stu.last_name}".strip() if stu else ""
    desc_raw = f"{fee_label} - {name_part}".strip() if name_part else fee_label

    payload = json.dumps({
        "amount": str(payment.amount_due),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PARENT, UserRole.ACCOUNTANT))
):
    try:
        payment_id = int(tx_ref.split("_")[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid transaction reference format")
        
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found natively")
        
    if current_user.role == UserRole.PARENT and payment.student.parent_id != current_user.id:
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
                payment.status = PaymentStatus.PAID
                payment.amount_paid = verified_amount
                if payment.invoice_title == "Registration fee":
                    payment.student.is_active = True
                db.commit()
                return {"status": "PAID", "message": "Transaction verified securely."}
            else:
                return {"status": "PENDING", "message": "Transaction verification failed or abandoned."}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=401, detail="Invalid Chapa Secret Key during verification.")
        raise HTTPException(status_code=400, detail="Chapa record not found or error pinging gateway.")

