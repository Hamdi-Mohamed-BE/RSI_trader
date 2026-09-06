@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting Administrator access...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%~1' -Verb RunAs"
  exit /b
)

set "DNS_HOST=%~1"
if not defined DNS_HOST set "DNS_HOST=calyx.duckdns.org"

echo.
echo Calyx DNS and HTTPS configuration
echo Hostname: %DNS_HOST%
echo VPS IP:   51.91.121.15
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Configure-DnsHttps.ps1" -DnsHostname "%DNS_HOST%" -ExpectedIp "51.91.121.15"
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
  echo Configuration did not finish. Read the message above, correct it, then run this BAT again.
) else (
  echo Configuration completed successfully.
)
echo.
pause
exit /b %RESULT%
