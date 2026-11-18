@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1"
set "install_result=%errorlevel%"
echo.
pause
exit /b %install_result%
