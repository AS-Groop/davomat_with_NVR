@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CLOUDFLARE TUNNEL - oynani yopmang
set CF=
if exist "cloudflared.exe" set CF=cloudflared.exe
if exist "cloudflared\cloudflared.exe" if "%CF%"=="" set CF=cloudflared\cloudflared.exe
if "%CF%"=="" (
  echo cloudflared.exe topilmadi. Uni shu papkaga joylang:
  echo https://github.com/cloudflare/cloudflared/releases  ^(cloudflared-windows-amd64.exe^)
  pause
  exit /b 1
)
start "TUNNEL Dashboard 8080" cmd /k "%CF%" tunnel --url http://localhost:8080
timeout /t 3 >nul
start "TUNNEL Ilova 8090" cmd /k "%CF%" tunnel --url http://localhost:8090
echo Ikkita oyna ochildi - har birida https://....trycloudflare.com havola chiqadi.
echo Oynalarni YOPMANG.
pause
