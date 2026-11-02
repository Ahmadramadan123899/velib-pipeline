@echo off
REM Runs once an hour (Task Scheduler "VelibWeather"): gets the Paris weather and saves it.

cd /d "%~dp0"
REM go to the project folder

if not exist logs mkdir logs

.venv\Scripts\python.exe src\fetch_weather.py >> logs\weather.log 2>&1
REM output and errors go to logs\weather.log