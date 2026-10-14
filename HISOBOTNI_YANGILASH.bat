@echo off
chcp 65001 >nul
title Oylik hisobotni qayta hisoblash
cd /d "%~dp0"
echo.
echo  Oylik hisobot qayta hisoblanmoqda...
python analyze_biocontrol_api.py
echo.
pause
