@echo off
REM Safe wrapper for clean-scan.py
REM Forwards all arguments to Python script
chcp 65001 >nul
python "%~dp0clean-scan.py" %*