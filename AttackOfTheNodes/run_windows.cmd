@echo off
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv-win"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "PY_CMD="

if exist "%VENV_PY%" goto :check_deps

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=py -3"
        goto :create_venv
    )
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=python"
        goto :create_venv
    )
)

echo Python 3.12 or newer was not found on PATH.
echo Install Python 3.12 or newer from https://www.python.org/downloads/windows/
echo Make sure "Add python.exe to PATH" is checked.
echo If Windows opens the Microsoft Store instead, disable the python.exe
echo App Execution Alias in Windows Settings, then reopen Command Prompt.
pause
exit /b 1

:create_venv
echo Creating Windows virtual environment in %VENV_DIR%...
%PY_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 goto :fail

:check_deps
echo Checking Python dependencies...
"%VENV_PY%" -c "import textual, rich, backend, frontend" >nul 2>nul
if %errorlevel%==0 goto :launch

echo Installing dependencies. This may take a minute on first launch...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install -r requirements.lock
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install -e .
if errorlevel 1 goto :fail

:launch
echo Launching AttackOfTheNodes...
"%VENV_PY%" main.py
exit /b %errorlevel%

:fail
echo.
echo Setup failed. Check the error above.
pause
exit /b 1
