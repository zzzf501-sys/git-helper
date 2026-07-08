@echo off

where python >nul 2>&1
if %errorlevel% equ 0 (
    python "%~dp0src\git-helper.py"
    pause
    exit /b
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 "%~dp0src\git-helper.py"
    pause
    exit /b
)

for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%PROGRAMFILES%\Python312\python.exe"
    "%PROGRAMFILES%\Python313\python.exe"
) do (
    if exist %%p (
        "%%p" "%~dp0src\git-helper.py"
        pause
        exit /b
    )
)

echo.
echo [Error] Python not found.
echo Please install Python 3.8+ from:
echo https://www.python.org/downloads/
echo (Check "Add Python to PATH" during install)
pause
