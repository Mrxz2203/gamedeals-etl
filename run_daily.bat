@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" run_pipeline.py >> data\pipeline.log 2>&1