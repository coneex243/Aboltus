@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Установка зависимостей Аболтус

echo ============================================================
echo      Установка зависимостей для ассистента Аболтус
echo ============================================================
echo.

set PYTHON_EXEC=python

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXEC=".venv\Scripts\python.exe"
    echo [ИНФО] Установка в виртуальное окружение .venv
) else (
    where python >nul 2>nul
    if errorlevel 1 goto NO_PYTHON
    echo [ИНФО] Установка в системный Python
)

echo.
echo [1/2] Обновление менеджера пакетов pip...
%PYTHON_EXEC% -m pip install --upgrade pip

echo.
echo [2/2] Установка пакетов из requirements.txt...
%PYTHON_EXEC% -m pip install -r requirements.txt

if errorlevel 1 goto FAIL

echo.
echo ============================================================
echo [УСПЕХ] Все зависимости успешно установлены!
echo Теперь вы можете запускать проект через START.bat
echo ============================================================
echo.
pause
exit /b 0

:FAIL
echo.
echo ============================================================
echo [ОШИБКА] Произошла ошибка при установке зависимостей.
echo Проверьте подключение к интернету и версию Python.
echo ============================================================
echo.
pause
exit /b 1

:NO_PYTHON
echo [ОШИБКА] Python не найден в вашей системе!
echo Установите Python с python.org и поставьте галочку "Add to PATH".
echo.
pause
exit /b 1
