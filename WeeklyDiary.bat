@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ----------------------------------------
echo WeeklyDiary を起動します...
echo ----------------------------------------

echo 仮想環境をチェック・更新しています...
uv sync

echo アプリを立ち上げています...
uv run streamlit run main.py

pause