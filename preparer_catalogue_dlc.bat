@echo off
rem FS Passion - prepare le catalogue des DLC avant de publier FSPassion-data
rem Controle le catalogue dlc_catalog.json du dépôt de données (FSPassion-data), calcule l'empreinte des icones,
rem date le catalogue du jour et en copie un exemplaire dans assets\fallback.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Lancez d'abord lancer_dev.bat une fois.
  pause
  exit /b 1
)
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" tools\prepare_data_repo.py --write --snapshot %*
pause
