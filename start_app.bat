@echo off
cd /d "%~dp0"
call .\venv\Scripts\activate.bat
pythonw launch.py