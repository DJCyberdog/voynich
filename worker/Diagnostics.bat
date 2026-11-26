@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 1
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
"bootstrap\python.exe" -E -s -B "vrs_portable.py" diagnostics %*
set "VRS_RC=%ERRORLEVEL%"
popd
exit /b %VRS_RC%
