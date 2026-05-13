"""SQLite-only legacy migrations (ALTER TABLE). PostgreSQL uses models + create_all."""

from sqlalchemy import inspect, text

from .database import engine


def apply_sqlite_migrations() -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    insp = inspect(engine)
    with engine.begin() as conn:
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "teaching_title" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN teaching_title VARCHAR(100)"))

        conn.execute(
            text(
                "UPDATE users SET teaching_title = 'General Studies' "
                "WHERE role = 'TEACHER' AND (teaching_title IS NULL OR teaching_title = '')"
            )
        )

        student_cols = {c["name"] for c in insp.get_columns("students")}
        if "academic_year" not in student_cols:
            conn.execute(
                text(
                    "ALTER TABLE students ADD COLUMN academic_year VARCHAR(32) "
                    "DEFAULT '2024-2025'"
                )
            )
            conn.execute(
                text("UPDATE students SET academic_year = '2024-2025' WHERE academic_year IS NULL")
            )

        conn.execute(
            text(
                "UPDATE students SET academic_year = '2024-2025' "
                "WHERE academic_year IS NULL OR academic_year = ''"
            )
        )

        if "is_active" not in student_cols:
            conn.execute(
                text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT 1")
            )


def ensure_payments_invoice_title_column() -> None:
    """Add optional invoice_title for Chapa / parent display (SQLite + PostgreSQL)."""
    insp = inspect(engine)
    if not insp.has_table("payments"):
        return
    pay_cols = {c["name"] for c in insp.get_columns("payments")}
    if "invoice_title" in pay_cols:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text("ALTER TABLE payments ADD COLUMN invoice_title VARCHAR(120)")
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS invoice_title VARCHAR(120)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE students ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"
                )
            )


def apply_all_migrations() -> None:
    apply_sqlite_migrations()
    ensure_payments_invoice_title_column()
