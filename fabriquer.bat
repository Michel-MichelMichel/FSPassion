@echo off
rem FS Passion - fabrication : executable, version portable, installeur
rem Resultat dans build\release\ : FSPassion-X.Y.Z-setup.exe, FSPassion-X.Y.Z-portable.zip, SHA256SUMS.txt
rem L installeur demande Inno Setup 6 : https://jrsoftware.org/isdl.php
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title FS Passion - fabrication
if not exist ".venv\Scripts\python.exe" (
  echo Lancez d'abord lancer_dev.bat une fois.
  pause
  exit /b 1
)
fc /b requirements-build.txt ".venv\requirements-build.ok" >nul 2>nul
if not errorlevel 1 goto :build
echo Installation des outils de fabrication, une minute environ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements-build.txt
if errorlevel 1 goto :erreur
copy /y requirements-build.txt ".venv\requirements-build.ok" >nul
:build
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" tools\build.py %*
if errorlevel 1 goto :erreur
echo.
echo Fabrication terminee : dossier build\release
explorer "build\release"
pause
exit /b 0
:erreur
echo.
echo La fabrication a echoue. Copiez tout le texte de cette fenetre pour l'analyser.
pause
exit /b 1
