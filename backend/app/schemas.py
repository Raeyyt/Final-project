from datetime import date as dt_date, datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, model_validator, Field

from .models import UserRole, AttendanceStatus, PaymentStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str
    role: UserRole


class UserBase(BaseModel):
    username: str
    full_name: str
    role: UserRole
    teaching_title: Optional[str] = None


class UserCreate(UserBase):
    password: str
    id: Optional[int] = None

    @model_validator(mode="after")
    def teaching_title_for_teacher_only(self):
        if self.role == UserRole.TEACHER:
            t = (self.teaching_title or "").strip()
            if not t:
                raise ValueError("Teaching title (subject specialty) is required for teachers")
            self.teaching_title = t
        else:
            self.teaching_title = None
        return self


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    old_password: str
    username: Optional[str] = None
    new_password: Optional[str] = None


class ClassBase(BaseModel):
    name: str
    description: Optional[str] = None
    teacher_id: Optional[int] = None


class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    teacher_id: Optional[int] = None


class ClassRead(ClassBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    class_id: int
    teacher_id: Optional[int] = None
    parent_id: Optional[int] = None
    academic_year: Optional[str] = None


class StudentCreate(StudentBase):
    """When ``create_registration_invoice`` is true, parent and fee amount are required."""

    create_registration_invoice: bool = False
    registration_fee_amount: Optional[float] = None
    registration_due_date: Optional[dt_date] = None

    @model_validator(mode="after")
    def registration_invoice_requires_parent_and_amount(self):
        if self.create_registration_invoice:
            if self.parent_id is None:
                raise ValueError(
                    "Link a parent account before creating a registration invoice so they can pay in the parent portal."
                )
            if self.registration_fee_amount is None or self.registration_fee_amount <= 0:
                raise ValueError("Registration fee amount must be greater than zero.")
        return self


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    class_id: Optional[int] = None
    parent_id: Optional[int] = None
    academic_year: Optional[str] = None


class StudentReEnroll(BaseModel):
    """Move an existing learner to a new class and/or academic year."""

    class_id: int
    academic_year: str

class StudentRead(StudentBase):
    id: int
    is_active: bool
    class_room: ClassRead

    model_config = ConfigDict(from_attributes=True)


class StudentCreatedRead(StudentRead):
    """Returned from POST /students/ when a registration invoice may have been created."""

    registration_payment_id: Optional[int] = None


class AttendanceBase(BaseModel):
    student_id: int
    status: AttendanceStatus
    date: dt_date | None = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceRead(AttendanceBase):
    id: int
    recorded_by: int
    created_at: datetime
    student: StudentRead

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    student_id: int
    amount_due: float
    amount_paid: float
    due_date: dt_date
    status: PaymentStatus
    invoice_title: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount_paid: Optional[float] = None
    status: Optional[PaymentStatus] = None


class PaymentRead(PaymentBase):
    id: int
    transaction_id: Optional[str] = None
    recorded_by: int
    updated_at: datetime
    student: StudentRead

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_students: int
    total_classes: int
    attendance_today: int
    payments_pending: int
    payments_overdue: int

class ClassMetricRead(BaseModel):
    class_name: str
    total_students: int
    present_today: int
    absent_today: int

class AttendanceTrendRead(BaseModel):
    date: dt_date
    present_count: int
    absent_count: int


class AnalyticsWindowRead(BaseModel):
    """Aggregated attendance for a calendar window (whole school)."""

    key: str
    label: str
    period_start: dt_date
    period_end: dt_date
    records_marked: int
    present: int
    absent: int
    absence_pct: float
    attendance_pct: float


class SchoolAttendanceAnalyticsRead(BaseModel):
    """Admin / director attendance overview."""

    as_of: dt_date
    enrolled_students: int
    windows: List[AnalyticsWindowRead]
    daily_trend: List[AttendanceTrendRead]


class ScheduleBase(BaseModel):
    class_id: int
    teacher_id: int
    subject_name: str
    day_of_week: str
    period: str

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleRead(ScheduleBase):
    id: int
    class_room: ClassRead
    teacher: UserRead

    model_config = ConfigDict(from_attributes=True)

class FinancialReportBase(BaseModel):
    total_revenue: float
    pending_dues: float
    overdue_count: int

class FinancialReportCreate(FinancialReportBase):
    pass

class FinancialReportRead(FinancialReportBase):
    id: int
    report_date: datetime
    generated_by: UserRead

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=4000)


class AnnouncementRead(BaseModel):
    id: int
    title: str
    body: str
    created_at: datetime
    author_name: str

    model_config = ConfigDict(from_attributes=True)

class DailyAttendanceSummaryRead(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    status: Optional[AttendanceStatus] = None

class AbsentReportRead(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    absent_count: int

class ConsecutiveAbsenceRead(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    consecutive_absent_days: int

