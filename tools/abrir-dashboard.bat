@echo off
REM Abre o painel em http://127.0.0.1:8000 (duplo clique neste arquivo).
REM Ctrl+C no terminal encerra o servidor.
REM Opens the dashboard at http://127.0.0.1:8000 (double-click this file).
REM Ctrl+C in the terminal stops the server.
cd /d "%~dp0.."
python -m energydash servir --porta 8000
pause
