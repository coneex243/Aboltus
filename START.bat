@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Ассистент Аболтус - Запуск

echo ============================================================
echo           Запуск голосового ассистента Аболтус
echo ============================================================
echo.

:: 1. Проверяем наличие виртуального окружения
if exist ".venv\Scripts\python.exe" goto RUN_VENV

:: 2. Проверяем системный Python
where python >nul 2>nul
if errorlevel 1 goto NO_PYTHON

:: 3. Проверяем, установлены ли основные библиотеки
python -c "import customtkinter, psutil, requests" >nul 2>nul
if errorlevel 1 goto NEED_INSTALL

:: Все библиотеки на месте - запуск через глобальный Python
echo [ИНФО] Запуск через системный Python...
echo.
python aboltus.py
goto AFTER_RUN

:RUN_VENV
echo [ИНФО] Запуск через виртуальное окружение .venv...
echo.
".venv\Scripts\python.exe" aboltus.py
goto AFTER_RUN

:NEED_INSTALL
echo [ВНИМАНИЕ] Необходимые библиотеки еще не установлены!
echo [ИНФО] Начинаю автоматическую установку зависимостей...
echo.
call INSTALL.bat
if errorlevel 1 goto INSTALL_FAILED
echo.
echo [ИНФО] Повторный запуск ассистента...
if exist ".venv\Scripts\python.exe" goto RUN_VENV
python aboltus.py
goto AFTER_RUN

:NO_PYTHON
echo [ОШИБКА] Python не найден в вашей системе!
echo Пожалуйста, установите Python версии 3.10-3.12 с официального сайта:
echo https://www.python.org/downloads/
echo.
echo ВАЖНО: При установке обязательно отметьте галочку:
echo "Add Python to PATH"
echo.
pause
exit /b 1

:INSTALL_FAILED
echo [ОШИБКА] Не удалось автоматически установить библиотеки.
echo Запустите INSTALL.bat вручную и проверьте подключение к интернету.
pause
exit /b 1

:AFTER_RUN
if errorlevel 1 (
    echo.
    echo ============================================================
    echo [ВНИМАНИЕ] Программа завершилась с ошибкой.
    echo ============================================================
    pause
)
