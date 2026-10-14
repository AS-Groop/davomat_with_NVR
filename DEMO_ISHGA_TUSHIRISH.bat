@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MMTRI Davomat - DEMO
echo.
echo  DEMO rejim: qurilmasiz, oylab topilgan 23 xodim bilan.
echo  Haqiqiy users.xlsx bolsa - unga tegilmaydi, demo ishlamaydi.
echo.
if exist "users.xlsx" (
  echo  users.xlsx allaqachon bor. Demo uchun uni boshqa joyga olib qoying.
  pause
  exit /b 1
)
copy "demo\users.xlsx" "users.xlsx" >nul
if not exist ".env" copy ".env.example" ".env" >nul
set FACEID_SOURCE=demo
echo  Ilova: http://localhost:8090   Dashboard: http://localhost:8080
echo  HR sifatida kirish: 90751163726516  (dastlabki parol - JSHSHIR oxirgi 6 raqami)
echo.
python start_all.py
pause
