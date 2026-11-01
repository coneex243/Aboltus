@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Настройка виртуального окружения Аболтус

echo ============================================================
echo    Создание изолированного окружения .venv для Аболтус
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 goto NO_PYTHON

if exist ".venv\Scripts\python.exe" goto VENV_EXISTS

echo [1/3] Создание виртуального окружения .venv...
python -m venv .venv
if errorlevel 1 goto VENV_FAIL
echo [OK] Виртуальное окружение успешно создано.
goto INSTALL_DEPS

:VENV_EXISTS
echo [ИНФО] Папка .venv уже существует. Пропускаю создание.

:INSTALL_DEPS
echo.
echo [2/3] Обновление pip в .venv...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo [3/3] Установка библиотек из requirements.txt в .venv...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto DEPS_FAIL

echo.
echo ============================================================
echo [УСПЕХ] Изолированное окружение полностью настроено!
echo Для запуска ассистента дважды кликните по START.bat
echo ============================================================
echo.
pause
exit /b 0

:NO_PYTHON
echo [ОШИБКА] Python не найден в вашей системе!
echo Установите Python с сайта python.org с галочкой "Add to PATH".
echo.
pause
exit /b 1

:VENV_FAIL
echo [ОШИБКА] Не удалось создать виртуальное окружение .venv.
echo.
pause
exit /b 1

:DEPS_FAIL
echo [ОШИБКА] Сбой при установке библиотек в .venv.
echo.
pause
exit /b 1
