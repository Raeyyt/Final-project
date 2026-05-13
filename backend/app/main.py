from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .migrate import apply_all_migrations
from .routers import auth, students, attendance, payments, dashboard, teachers, accountants, classes, schedules, reports, announcements
from .seed import seed

Base.metadata.create_all(bind=engine)
apply_all_migrations()
seed()

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

