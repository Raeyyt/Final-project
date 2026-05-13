from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    ACCOUNTANT = "ACCOUNTANT"
    DIRECTOR = "DIRECTOR"
    PARENT = "PARENT"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False)
    # Subject specialty for TEACHER (e.g. Chemistry); must match schedule subject_name.
    teaching_title: Mapped[str | None] = mapped_column(String(100), nullable=True)

    students = relationship("Student", back_populates="teacher", foreign_keys="[Student.teacher_id]")
    children = relationship("Student", back_populates="parent", foreign_keys="[Student.parent_id]")
    managed_classes = relationship("ClassRoom", back_populates="teacher")
    attendance_records = relationship(
        "Attendance", back_populates="recorded_by_user"
    )
    payment_records = relationship("Payment", back_populates="recorded_by_user")
    schedules = relationship("SubjectSchedule", back_populates="teacher")
    announcements_authored = relationship(
        "Announcement", back_populates="author"
    )


class ClassRoom(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    students = relationship("Student", back_populates="class_room")
    teacher = relationship("User", back_populates="managed_classes")
    schedules = relationship("SubjectSchedule", back_populates="class_room")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, default="2024-2025")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    class_room = relationship(
        "ClassRoom", back_populates="students", lazy="joined"
    )
    teacher = relationship("User", back_populates="students", foreign_keys=[teacher_id])
    parent = relationship("User", back_populates="children", foreign_keys=[parent_id])
    attendance = relationship("Attendance", back_populates="student")
    payments = relationship("Payment", back_populates="student")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "date", name="uq_student_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        SqlEnum(AttendanceStatus), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attendance", lazy="joined")
    recorded_by_user = relationship("User", back_populates="attendance_records")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING
    )
    transaction_id: Mapped[str] = mapped_column(String(150), nullable=True)
    # Shown on parent portal and Chapa checkout (e.g. "Registration fee", "Tuition").
    invoice_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    student = relationship("Student", back_populates="payments", lazy="joined")
    recorded_by_user = relationship("User", back_populates="payment_records")

class SubjectSchedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)

    class_room = relationship("ClassRoom", back_populates="schedules", lazy="joined")
    teacher = relationship("User", back_populates="schedules", lazy="joined")


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    total_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    pending_dues: Mapped[float] = mapped_column(Float, nullable=False)
    overdue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    report_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    generated_by = relationship("User")


class Announcement(Base):
    """School-wide notices composed by admins; visible to parents (and other signed-in users)."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="announcements_authored")
