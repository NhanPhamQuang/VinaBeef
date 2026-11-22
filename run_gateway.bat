@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv is missing. Run setup.bat first.
  pause
  exit /b 1
)
cd edge_gateway
echo Starting offline RFID gateway at http://127.0.0.1:8001
"..\.venv\Scripts\python.exe" -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
if errorlevel 1 goto :failed
exit /b 0
:failed
echo ERROR: Gateway did not start. The traceback is shown above.
pause
exit /b 1
