@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

rem cmd.exe cannot use a UNC path as its working directory. Launched from
rem one (\\wsl.localhost\... or \\server\share), it prints a warning, falls
rem back to C:\Windows, and the venv creation below then tries to write into
rem the Windows directory and fails with Access denied. Stop with a useful
rem message instead of that confusing trail.
if "%SCRIPT_DIR:~0,2%"=="\\" (
    echo ERROR: This script lives on a UNC path:
    echo   %SCRIPT_DIR%
    echo.
    echo cmd.exe cannot run from UNC paths, including \\wsl.localhost shares.
    echo Clone the repository to a local Windows drive and run it there:
    echo.
    echo   git clone https://github.com/makinster/node_workflow C:\src\node_workflow
    echo.
    echo Note: OS window placement needs a native Windows Python. Running
    echo main.py with the WSL interpreter reports Linux and silently uses the
    echo fallback window manager, which does no placement at all.
    pause
    exit /b 1
)

cd /d "%SCRIPT_DIR%"
if errorlevel 1 goto :fail

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
rem win32gui is part of the optional [windows] extra (pywin32). Including it
rem here means an existing .venv-win created before the extra was added
rem reinstalls instead of silently running without window placement.
"%VENV_PY%" -c "import textual, rich, backend, frontend, win32gui" >nul 2>nul
if %errorlevel%==0 goto :launch

echo Installing dependencies. This may take a minute on first launch...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install -r requirements.lock
if errorlevel 1 goto :fail
rem The [windows] extra pulls in pywin32, which powers OS window placement
rem and control (see docs/FILE_OUTPUT_BUILD_PLAN.md, D5). Without it files
rem still open, but placement/focus/close degrade to logged warnings.
"%VENV_PY%" -m pip install -e ".[windows]"
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
