@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Создание виртуального окружения...
    py -m venv .venv
)

echo Установка зависимостей...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Запуск приложения: http://127.0.0.1:5000
python app.py
pause
