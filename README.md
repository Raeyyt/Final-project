## School Fee & Attendance Management

Modern full-stack web application covering secure authentication, attendance tracking, and school fee workflows tailored for admins, teachers, and accountants.

### Tech Stack
- **Backend:** FastAPI, SQLAlchemy, SQLite (upgrade-ready to Postgres)
- **Frontend:** React + Vite + TypeScript
- **Auth:** OAuth2 password flow with JWT + role-based guards

### Quick Start

#### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m app.seed                                    # loads demo data & users
uvicorn app.main:app --reload --port 8000
```

Environment variables (optional):
```
APP_SECRET_KEY=<override jwt secret>
DATABASE_URL=sqlite:///./school_management.db  # or postgres url
FRONTEND_URL=http://localhost:5173
```

Demo accounts (username / password):
- `admin / admin123`
- `teacher / teacher123`
- `accountant / accountant123`

#### Frontend
```bash
cd frontend
npm install           # already run once, repeat after pulling updates
npm run dev           # http://localhost:5173
```
Set `VITE_API_URL` in `.env` if the backend is hosted elsewhere (defaults to `http://localhost:8000`).

### Key Features
- Secure login and token refresh with automatic session restoration
- Role-scoped navigation & dashboards
- Teacher attendance workflows with conflict protection
- Accountant payment lifecycle (create, update, mark paid)
- Admin-wide analytics dashboard
- Responsive, accessible UI with a clean blue palette

### Testing & Build
- Frontend: `npm run build`
- Backend: light smoke test with `uvicorn app.main:app --port 8000` then hit `/health`

### Folder Overview
```
backend/
  app/
    main.py             # FastAPI entrypoint
    models.py           # SQLAlchemy models & enums
    routers/            # Auth, students, attendance, payments, dashboard
    security.py         # JWT + hashing helpers
    seed.py             # Demo data + default users
frontend/
  src/
    context/            # AuthProvider
    pages/              # Login, Dashboard, Attendance, Payments
    layout/             # App shell + navigation
```

