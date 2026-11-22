@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv is missing. Run setup.bat first.
  pause
  exit /b 1
)
cd backend
echo [1/2] Applying Alembic migrations...
"..\.venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto :failed
echo [2/2] Starting FastAPI at http://127.0.0.1:8000
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
if errorlevel 1 goto :failed
exit /b 0
:failed
echo ERROR: Backend did not start. The traceback is shown above.
pause
exit /b 1
