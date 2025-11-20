@echo off
REM permite saltar o smoke:  set SKIP_SMOKE=1 & git commit -m "..."
if "%SKIP_SMOKE%"=="1" (
  echo [pre-commit] SKIP_SMOKE=1 — a saltar testes.
  exit /b 0
)

where pwsh >NUL 2>NUL
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "scripts\smoke.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\smoke.ps1"
)
exit /b %ERRORLEVEL%
