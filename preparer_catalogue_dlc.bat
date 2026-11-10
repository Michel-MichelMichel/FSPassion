@echo off
rem FS Passion - prepare le catalogue des DLC avant de publier FSPassion-data
rem 1. recupere la derniere version publiee de FSPassion-data (git pull) ;
rem 2. controle le catalogue dlc_catalog.json, calcule l'empreinte des icones,
rem    passe en "released" les DLC sortis, complete le nom de fichier ("file")
rem    des DLC presents sur ce PC et reconnus seulement par leurs mots-cles ;
rem 3. affiche les commandes pour publier.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Lancez d'abord lancer_dev.bat une fois.
  pause
  exit /b 1
)
if not exist "..\FSPassion-data\.git" (
  echo ..\FSPassion-data n'est pas un clone Git : voir docs\Guide - Sortie d'un DLC.md, etape 0.
  pause
  exit /b 1
)
echo Recuperation de FSPassion-data depuis GitHub...
git -C "..\FSPassion-data" pull --ff-only
if errorlevel 1 (
  echo.
  echo git pull a echoue : modifications locales non publiees ? Voir "git -C ..\FSPassion-data status".
  pause
  exit /b 1
)
echo.
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" tools\prepare_data_repo.py --write --pdlc %*
pause
