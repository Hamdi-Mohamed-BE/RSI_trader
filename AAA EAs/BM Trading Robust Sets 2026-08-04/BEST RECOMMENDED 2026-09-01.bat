@echo off
setlocal
title BM Trading - Best Recommended 2026-09-01

echo Applying the locked 13-EA recommended portfolio...
echo - 9 EAs use Dynamic 50-20 stop management
echo - 4 EAs retain their original exits
echo - Research session filters are disabled
echo - Engineered Liquidity BTC, US100 Fabio ORB and XAU Markov are excluded
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Install-BMTradingPortfolio.ps1" -AccountProfile AUTO -SafetyMode STANDARD %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The best-recommended installer stopped without starting the portfolio.
) else (
  echo Best Recommended 2026-09-01 installation finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
