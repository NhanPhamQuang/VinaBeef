@echo off
setlocal
cd /d "%~dp0"
echo [1/3] Checking Python...
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher py.exe missing. Install Python 3.11+ and enable the launcher.
  pause
  exit /b 1
)
echo [2/3] Creating .venv...
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
  if errorlevel 1 goto :failed
)
echo [3/3] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo INFO: Created .env; edit DATABASE_URL before launching if using Aiven.
)
echo.
echo Setup completed. Open run_backend.bat and run_gateway.bat in two terminals.
pause
exit /b 0
:failed
echo.
echo ERROR: Setup failed. Inspect the message ABOVE; window will remain open.
pause
exit /b 1
