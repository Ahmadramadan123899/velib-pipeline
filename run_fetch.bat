@echo off
REM Don't print each command as it runs

cd /d "%~dp0"
REM %~dp0 = the folder this .bat file is in -> go to the project root (/d also switches drive if needed)

if not exist logs mkdir logs
REM Create a logs folder the first time

.venv\Scripts\python.exe src\fetch_snapshot.py >> logs\fetch.log 2>&1
REM Use the venv's Python directly (no need to "activate").
REM >> appends normal output to the log; 2>&1 sends errors there too.