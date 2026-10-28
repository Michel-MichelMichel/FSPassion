@echo off
rem FS Passion - lancement en mode developpement
rem Premier lancement : prepare l'environnement Python et installe les dependances.
rem Ensuite : demarre l'application (fenetre seule ; pas de navigateur)
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title FS Passion - developpement

set "PY="
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY=py -3.12"
if not defined PY (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto :nopython

if exist ".venv\Scripts\python.exe" goto :deps
echo Preparation de l'environnement Python, premier lancement...
%PY% -m venv .venv
if errorlevel 1 goto :erreur

:deps
fc /b requirements.txt ".venv\requirements.ok" >nul 2>nul
if not errorlevel 1 goto :run
echo Installation des dependances, une minute environ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :erreur
copy /y requirements.txt ".venv\requirements.ok" >nul

:run
set "PYTHONPATH=%~dp0src"
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" -m fspassion --dev --no-browser %*
if errorlevel 1 goto :erreur
exit /b 0

:nopython
echo.
echo Python 3.12 est introuvable.
echo Installez Python 3.12, 64 bits, depuis python.org
echo en cochant "Add python.exe to PATH", puis relancez ce fichier.
echo.
pause
exit /b 1

:erreur
echo.
echo Une erreur s'est produite. Copiez tout le texte de cette fenetre,
echo et joignez le journal :
echo %LOCALAPPDATA%\FSPassion\logs\fspassion.log
echo.
pause
exit /b 1
