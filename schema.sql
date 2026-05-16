-- SQLite Database Schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK(role IN ('ADMIN', 'TEACHER', 'ACCOUNTANT', 'DIRECTOR', 'PARENT')),
    teaching_title VARCHAR(100) NULL,
    CONSTRAINT chk_teaching_title CHECK (
        (role = 'TEACHER' AND teaching_title IS NOT NULL AND teaching_title <> '')
        OR
        (role <> 'TEACHER' AND teaching_title IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    teacher_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_classes_teacher_unique ON classes (teacher_id) WHERE teacher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_classes_teacher ON classes (teacher_id);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    teacher_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    parent_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    academic_year VARCHAR(32) NOT NULL DEFAULT '2024-2025',
    is_active BOOLEAN NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_students_class_id ON students (class_id);
CREATE INDEX IF NOT EXISTS idx_students_teacher_id ON students (teacher_id);
CREATE INDEX IF NOT EXISTS idx_students_parent_id ON students (parent_id);
CREATE INDEX IF NOT EXISTS idx_students_year ON students (academic_year);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
    recorded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) NOT NULL CHECK(status IN ('PRESENT', 'ABSENT')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_student_date UNIQUE (student_id, date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance (student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance (date);
CREATE INDEX IF NOT EXISTS idx_attendance_date_student ON attendance (date, student_id);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
    amount_due REAL NOT NULL,
    amount_paid REAL NOT NULL DEFAULT 0,
    due_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'PAID', 'OVERDUE')),
    transaction_id VARCHAR(150) NULL,
    invoice_title VARCHAR(120) NULL,
    recorded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_student ON payments (student_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status);
CREATE INDEX IF NOT EXISTS idx_payments_due_date ON payments (due_date);
CREATE INDEX IF NOT EXISTS idx_payments_updated_at ON payments (updated_at);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    subject_name VARCHAR(100) NOT NULL,
    day_of_week VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL,
    CONSTRAINT uq_teacher_slot UNIQUE (teacher_id, day_of_week, period)
);

CREATE INDEX IF NOT EXISTS idx_schedules_class ON schedules (class_id);
CREATE INDEX IF NOT EXISTS idx_schedules_teacher ON schedules (teacher_id);

CREATE TABLE IF NOT EXISTS financial_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_revenue REAL NOT NULL,
    pending_dues REAL NOT NULL,
    overdue_count INTEGER NOT NULL,
    generated_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    report_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_financial_reports_generated_by ON financial_reports (generated_by_id);
CREATE INDEX IF NOT EXISTS idx_financial_reports_date ON financial_reports (report_date);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    target_class_id INTEGER NULL REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_announcements_author ON announcements (author_id);
CREATE INDEX IF NOT EXISTS idx_announcements_created_at ON announcements (created_at);

INSERT OR IGNORE INTO users (username, full_name, hashed_password, role, teaching_title)
VALUES (
    'admin',
    'System Admin',
    '$2b$12$X3/AWIGk18eyLUTAxq8h3.1brVSgktwonD4rhYVmZnqV.LrIlv60m',
    'ADMIN',
    NULL
);