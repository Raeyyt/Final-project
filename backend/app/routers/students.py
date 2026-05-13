from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
import pandas as pd
import io
from sqlalchemy.orm import Session

from .. import schemas
from ..academic import current_academic_year_label
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import ClassRoom, Payment, PaymentStatus, Student, User, UserRole

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/meta/defaults")
def enrollment_defaults(current_user: User = Depends(get_current_user)):
    """Current academic year label for new registrations."""
    return {"default_academic_year": current_academic_year_label()}


@router.get("/meta/academic-years")
def list_distinct_academic_years(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    rows = db.query(Student.academic_year).distinct().all()
    years = sorted({r[0] for r in rows if r[0]}, reverse=True)
    return {"academic_years": years}


@router.get("/", response_model=list[schemas.StudentRead])
def list_students(
    db: Session = Depends(get_db),
    academic_year: str | None = Query(
        None, description="Filter by academic year (admin/director only)"
    ),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.TEACHER,
            UserRole.ACCOUNTANT,
            UserRole.DIRECTOR,
            UserRole.PARENT,
        )
    ),
):
    query = db.query(Student)
    if current_user.role == UserRole.TEACHER:
        query = query.join(ClassRoom).filter(ClassRoom.teacher_id == current_user.id)
    elif current_user.role == UserRole.PARENT:
        query = query.filter(Student.parent_id == current_user.id)

    if (
        academic_year
        and academic_year.strip()
        and current_user.role in (UserRole.ADMIN, UserRole.DIRECTOR)
    ):
        query = query.filter(Student.academic_year == academic_year.strip())

    return query.all()


@router.post("/", response_model=schemas.StudentCreatedRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    class_room = db.get(ClassRoom, payload.class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Class not found")
    if not class_room.teacher_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign student to a class with no assigned teacher",
        )

    ay = (payload.academic_year or "").strip() or current_academic_year_label()

    student = Student(
        first_name=payload.first_name,
        last_name=payload.last_name,
        class_id=payload.class_id,
        teacher_id=class_room.teacher_id,
        parent_id=payload.parent_id,
        academic_year=ay,
        is_active=not payload.create_registration_invoice,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    registration_payment_id = None
    if payload.create_registration_invoice:
        due = payload.registration_due_date or (date.today() + timedelta(days=14))
        payment = Payment(
            student_id=student.id,
            amount_due=float(payload.registration_fee_amount),
            amount_paid=0.0,
            due_date=due,
            status=PaymentStatus.PENDING,
            recorded_by=current_user.id,
            invoice_title="Registration fee",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        registration_payment_id = payment.id

    base = schemas.StudentRead.model_validate(student)
    return schemas.StudentCreatedRead(
        **base.model_dump(),
        registration_payment_id=registration_payment_id,
    )


@router.post(
    "/{student_id}/re-enroll",
    response_model=schemas.StudentRead,
)
def re_enroll_student(
    student_id: int,
    payload: schemas.StudentReEnroll,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    class_room = db.get(ClassRoom, payload.class_id)
    if not class_room:
        raise HTTPException(status_code=404, detail="Target class not found")
    if not class_room.teacher_id:
        raise HTTPException(
            status_code=400,
            detail="Target class has no assigned teacher",
        )

    student.class_id = payload.class_id
    student.teacher_id = class_room.teacher_id
    student.academic_year = payload.academic_year.strip()

    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.patch("/{student_id}", response_model=schemas.StudentRead)
def update_student(
    student_id: int,
    payload: schemas.StudentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "class_id" in update_data:
        class_room = db.get(ClassRoom, update_data["class_id"])
        if not class_room:
            raise HTTPException(status_code=404, detail="Target class not found")
        if not class_room.teacher_id:
            raise HTTPException(
                status_code=400,
                detail="Target class has no assigned teacher",
            )

        student.class_id = update_data["class_id"]
        student.teacher_id = class_room.teacher_id

    if "first_name" in update_data:
        student.first_name = update_data["first_name"]
    if "last_name" in update_data:
        student.last_name = update_data["last_name"]
    if "parent_id" in update_data:
        student.parent_id = update_data["parent_id"]
    if "academic_year" in update_data and update_data["academic_year"] is not None:
        student.academic_year = update_data["academic_year"].strip()

    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=schemas.StudentRead)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.TEACHER,
            UserRole.ACCOUNTANT,
            UserRole.DIRECTOR,
            UserRole.PARENT,
        )
    ),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == UserRole.TEACHER and student.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this student")
    if current_user.role == UserRole.PARENT and student.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this child")
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
    return None

@router.post("/bulk-upload", status_code=status.HTTP_201_CREATED)
def bulk_upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
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
            class_room = None
            
            if class_identifier.isdigit():
                class_room = db.get(ClassRoom, int(class_identifier))
                
            if not class_room:
                class_room = db.query(ClassRoom).filter(ClassRoom.name == class_identifier).first()
                
            if not class_room:
                skipped_reasons.append(f"Class '{class_identifier}' not found")
                continue
            if not class_room.teacher_id:
                skipped_reasons.append(f"Class '{class_identifier}' has no assigned teacher")
                continue
            
            ay = current_academic_year_label()
            if "academic_year" in df.columns and pd.notna(row["academic_year"]):
                ay = str(row["academic_year"]).strip()
                
            student = Student(
                first_name=str(row["first_name"]).strip(),
                last_name=str(row["last_name"]).strip(),
                class_id=class_room.id,
                teacher_id=class_room.teacher_id,
                academic_year=ay,
                is_active=True
            )
            db.add(student)
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

