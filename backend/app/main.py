from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import DB_PATH
from .routers import auth, students, attendance, payments, dashboard, teachers, accountants, classes, schedules, reports, announcements
import sqlite3
import os

def init_db():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(schema_script)
        conn.commit()
        conn.close()

init_db()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(payments.router)
app.include_router(dashboard.router)
app.include_router(teachers.router)
app.include_router(accountants.router)
app.include_router(classes.router)
app.include_router(schedules.router)
app.include_router(reports.router)
app.include_router(announcements.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

