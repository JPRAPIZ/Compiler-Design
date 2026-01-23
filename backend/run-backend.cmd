@echo off
setlocal EnableExtensions EnableDelayedExpansion

pushd "%~dp0"

set "PORT=8000"
set "APP=api:app"
if not "%~1"=="" set "PORT=%~1"
if not "%~2"=="" set "APP=%~2"

set "PY_LAUNCHER="
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PY_LAUNCHER=py"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PY_LAUNCHER=python"
  )
)

if "%PY_LAUNCHER%"=="" (
  echo [error] Python not found on PATH.
  echo Install Python 3.10+ and make sure it is added to PATH.
  popd
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [setup] Creating venv...
  %PY_LAUNCHER% -m venv venv
  if not exist "venv\Scripts\python.exe" (
    echo [error] Failed to create venv.
    popd
    exit /b 1
  )
)

set "VENV_PY=venv\Scripts\python.exe"

echo [setup] Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip >nul

echo [check] Checking required packages...
"%VENV_PY%" -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if not %ERRORLEVEL%==0 (
  echo [setup] Installing backend dependencies into venv...
  if exist "requirements.txt" (
    "%VENV_PY%" -m pip install -r requirements.txt
  ) else (
    "%VENV_PY%" -m pip install fastapi "uvicorn[standard]" pydantic
  )

  if not %ERRORLEVEL%==0 (
    echo [error] Dependency install failed.
    popd
    exit /b 1
  )
)

echo.
echo [run] Starting backend: %APP% on port %PORT%
echo [run] http://localhost:%PORT%
echo.

"%VENV_PY%" -m uvicorn %APP% --reload --port %PORT%

set "EXITCODE=%ERRORLEVEL%"
popd
exit /b %EXITCODE%
