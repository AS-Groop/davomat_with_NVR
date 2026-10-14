@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MMTRI Davomat - ornatish
echo.
echo  1. Python kutubxonalari ornatilmoqda...
python -m pip install -r requirements.txt
echo.
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo  2. .env yaratildi - uni Bloknotda ochib DASHBOARD_PASSWORD ni yozing.
) else (
  echo  2. .env allaqachon bor - tegilmadi.
)
if not exist "users.xlsx" (
  echo  3. users.xlsx yoq: users_namuna.xlsx ni toldirib, users.xlsx nomi bilan saqlang.
)
echo.
echo  Tayyor. Keyingi qadam: QOLLANMA.md
pause
