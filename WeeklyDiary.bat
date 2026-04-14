@echo off
@chcp 65001 > nul
setlocal
cd /d %~dp0

echo ----------------------------------------
echo [INFO] Starting MyAutoDiary...
echo ----------------------------------------

:: Check and sync virtual environment
echo [PREP] Checking virtual environment...
uv sync

:: Launch the app using python -m streamlit to bypass execution policies
echo [RUN] Launching Streamlit app...
uv run python -m streamlit run main.py

if %errorlevel% neq 0 (
echo.
echo [ERROR] Failed to launch the app.
pause
)

endlocal