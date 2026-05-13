"""Optional DB bootstrap: only creates the default admin when the user table is empty."""

from sqlalchemy.orm import Session

from .database import SessionLocal, Base, engine
from .models import (
    Announcement,
    Attendance,
    ClassRoom,
    FinancialReport,
    Payment,
    Student,
    SubjectSchedule,
    User,
    UserRole,
)
from .security import get_password_hash


def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        admin = User(
            username="admin",
            full_name="System Admin",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()


def purge_non_admin_data() -> None:
    """Delete all school records and all users except username ``admin``."""
    db: Session = SessionLocal()
    try:
        db.query(Announcement).delete(synchronize_session=False)
        db.query(Attendance).delete(synchronize_session=False)
        db.query(Payment).delete(synchronize_session=False)
        db.query(SubjectSchedule).delete(synchronize_session=False)
        db.query(FinancialReport).delete(synchronize_session=False)
        db.query(Student).delete(synchronize_session=False)
        db.query(ClassRoom).delete(synchronize_session=False)
        removed_users = (
            db.query(User).filter(User.username != "admin").delete(synchronize_session=False)
        )
        db.commit()
        print(f"Purge complete. Removed linked data and {removed_users} non-admin user(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--purge":
        purge_non_admin_data()
    else:
        seed()
