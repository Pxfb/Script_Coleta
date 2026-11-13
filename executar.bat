@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
call "%~dp0instalar.bat" --se-necessario
if errorlevel 1 exit /b %errorlevel%
"%~dp0.venv\Scripts\python.exe" "%~dp0executar.py" %*
exit /b %errorlevel%
