@echo off
REM Jellyfin Log Analyzer - Windows Batch Wrapper
REM This script makes it easy to run the Jellyfin log analyzer on Windows

setlocal enabledelayedexpansion

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0

REM Check if the Python script exists
if not exist "%SCRIPT_DIR%jellyfin_log_analyzer.py" (
    echo Error: jellyfin_log_analyzer.py not found in %SCRIPT_DIR%
    pause
    exit /b 1
)

REM If no arguments provided, show help and common usage examples
if "%~1"=="" (
    echo.
    echo Jellyfin Log Analyzer - Windows
    echo ===============================
    echo.
    echo Common usage examples:
    echo.
    echo   %~nx0 --all                          ^(scan for all error types^)
    echo   %~nx0 --transcoding --playback       ^(scan for specific errors^)
    echo   %~nx0 --networking --max-errors 5    ^(get more errors per type^)
    echo   %~nx0 --help                         ^(show all options^)
    echo.
    echo The script will automatically detect your Jellyfin installation
    echo and find log files in common Windows locations.
    echo.
    pause
    exit /b 0
)

REM Run the Python script with all provided arguments
python "%SCRIPT_DIR%jellyfin_log_analyzer.py" %*

REM If the script failed, pause so user can see the error
if errorlevel 1 (
    echo.
    echo Script execution failed. Press any key to exit.
    pause >nul
)
