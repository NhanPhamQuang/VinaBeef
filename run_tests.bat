@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv is missing. Run setup.bat first.
  pause
  exit /b 1
)
cd backend
"..\.venv\Scripts\python.exe" -m pytest -q
set STATUS=%ERRORLEVEL%
echo.
if not "%STATUS%"=="0" echo TESTS FAILED: check errors above.
pause
exit /b %STATUS%
