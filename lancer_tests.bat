@echo off
rem FS Passion - tests automatiques (pytest), controle du code (ruff)
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Lancez d'abord lancer_dev.bat une fois.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements-dev.txt
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" -m pytest
".venv\Scripts\python.exe" -m ruff check src tests tools
pause
