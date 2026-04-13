@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=src
python -m project_invest launch --host 0.0.0.0 --port 8000 --public
endlocal
