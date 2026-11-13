@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
where py >nul 2>nul
if not errorlevel 1 goto launcher
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.12 ou superior e adicione ao PATH.
  exit /b 1
)
python "%~dp0instalar.py" %*
exit /b %errorlevel%
:launcher
py -3 "%~dp0instalar.py" %*
exit /b %errorlevel%
