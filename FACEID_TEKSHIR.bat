@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FaceID ulanishini tekshirish
python faceid_tekshir.py %*
