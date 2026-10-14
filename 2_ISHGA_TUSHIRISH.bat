@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MMTRI Davomat - TIZIM (oynani yopmang)
python start_all.py
pause
