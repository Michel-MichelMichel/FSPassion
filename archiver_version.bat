@echo off
rem FS Passion - archive complete de la version en cours
rem Copie le projet dans un dossier d'archives vX.Y.Z (à côté du projet) (version lue dans pyproject.toml).
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Lancez d'abord lancer_dev.bat une fois.
  pause
  exit /b 1
)
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" tools\archive_version.py %*
pause
