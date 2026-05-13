import sys
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, UserRole, ClassRoom, Student, Attendance, AttendanceStatus, Payment, PaymentStatus, SubjectSchedule
from app.security import get_password_hash

def seed_ethiopian_demo():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first():
            print("Admin data already seeded.")
            return

        print("Seeding admin user data...")

        # Create Admin
        admin = User(
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.commit()

        print("Successfully seeded Admin user!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_ethiopian_demo()
