@echo off
setlocal
set "PYTHONUTF8=1"
call "%~dp0instalar.bat" --se-necessario
if errorlevel 1 exit /b %errorlevel%
"%~dp0.venv\Scripts\python.exe" "%~dp0interface.py"
