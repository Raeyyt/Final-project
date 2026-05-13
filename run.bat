@echo off
setlocal
cd /d "%~dp0"

REM PostgreSQL runs in Docker (see docker-compose.yml). The API defaults to localhost:5432.
where docker >nul 2>&1
if errorlevel 1 (
  echo.
  echo [WARNING] Docker was not found on PATH. The backend expects PostgreSQL at 127.0.0.1:5432
  echo           unless you set DATABASE_URL in backend\.env ^(e.g. SQLite^).
  echo           Install Docker Desktop or start Postgres manually, then re-run this script.
  echo.
) else (
  echo Starting PostgreSQL container ^(docker compose^)...
  docker compose up -d
  if errorlevel 1 docker-compose up -d
  echo Waiting a few seconds for the database to accept connections...
  timeout /t 6 /nobreak >nul
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating virtual environment...
  where py >nul 2>&1 && (py -m venv backend\.venv) || (python -m venv backend\.venv)
  cd /d backend
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  cd /d ..
)

start "Backend" cmd /k "cd /d backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

start "Frontend" cmd /k "cd /d "mik frontend" && python -m http.server 8080"

timeout /t 3 >nul
start "" http://localhost:8080/loginpag/login.html

exit /b 0
