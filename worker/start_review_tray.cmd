@echo off
setlocal
if "%~1"=="" (
  echo Usage: start_review_tray.cmd ^<private-tray-config.json^>
  exit /b 2
)
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo Python virtual environment missing. See TRAY.md.
  exit /b 1
)
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0tray_launcher.pyw" "%~f1"
