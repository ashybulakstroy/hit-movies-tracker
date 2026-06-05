@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python generate_page.py --refresh
pause
