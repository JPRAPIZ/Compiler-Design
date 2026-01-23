@echo off
setlocal EnableExtensions

pushd "%~dp0"

set "BACK_PORT=8000"
if not "%~1"=="" set "BACK_PORT=%~1"

if not exist "backend\run-backend.cmd" (
  echo [error] backend\run-backend.cmd not found. Put this file in repo root.
  echo         Expected: %~dp0backend\run-backend.cmd
  echo.
  pause
  popd
  exit /b 1
)

if not exist "frontend\" (
  echo [error] frontend\ folder not found. Put this file in repo root.
  echo.
  pause
  popd
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [error] npm not found on PATH. Install Node.js
  echo.
  pause
  popd
  exit /b 1
)

echo [backend] Starting on port %BACK_PORT% (separate window)...
start "Compiler Backend" /D "%~dp0backend" cmd /k "title Compiler Backend & call run-backend.cmd %BACK_PORT%"

echo [backend] http://localhost:%BACK_PORT%
echo.

pushd frontend

if not exist "node_modules\" (
  echo [frontend] node_modules not found. Installing dependencies...

  if exist "package-lock.json" (
    call npm ci
    if errorlevel 1 (
      echo [frontend] npm ci failed; falling back to npm install...
      call npm install
    )
  ) else (
    call npm install
  )

  if errorlevel 1 (
    echo [error] Frontend dependency install failed.
    echo.
    pause
    popd
    goto :CLEANUP
  )
) else (
  echo [frontend] node_modules found. Skipping install.
)

echo [frontend] Starting dev server...
echo [frontend] http://localhost:5173
echo.

call npm run dev
set "FRONT_EXIT=%ERRORLEVEL%"

popd

:CLEANUP
echo.
echo [backend] Stopping process listening on port %BACK_PORT%...

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /C:":%BACK_PORT% " ^| findstr /C:"LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)

echo [done]
popd
exit /b %FRONT_EXIT%
