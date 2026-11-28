@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 1
if "%~1"=="" (
  "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\Setup-Auto.ps1"
  goto auto_done
)
if not exist "bootstrap\python.exe" (
  echo Missing verified local bootstrap runtime. See PORTABLE.md.
  popd
  exit /b 2
)
if not exist "temp" mkdir "temp"
set "TEMP=%CD%\temp"
set "TMP=%TEMP%"
set "PYTHONHOME="
set "PYTHONPATH="
"bootstrap\python.exe" -E -s -B "vrs_portable.py" setup %*
set "VRS_RC=%ERRORLEVEL%"
popd
exit /b %VRS_RC%

:auto_done
set "VRS_RC=%ERRORLEVEL%"
echo.
pause
popd
exit /b %VRS_RC%
