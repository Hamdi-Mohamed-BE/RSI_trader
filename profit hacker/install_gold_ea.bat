@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT=%~dp0"
set "EA_SOURCE=%PROJECT%mt5\Experts\GoldTrendRiderEA.mq5"
set "PRESET_SOURCE=%PROJECT%mt5\Presets\GoldTrendRider_Conservative.set"
set "METAEDITOR=C:\Program Files\MetaTrader 5\MetaEditor64.exe"
set "TERMINAL_DATA="

if not exist "%EA_SOURCE%" (
  echo EA source was not found:
  echo %EA_SOURCE%
  pause
  exit /b 1
)

for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
  if not defined TERMINAL_DATA if exist "%%~fD\MQL5\Experts" set "TERMINAL_DATA=%%~fD"
)

if not defined TERMINAL_DATA (
  echo No MetaTrader 5 data folder was found.
  echo Start MetaTrader 5 once, close it, and run this installer again.
  pause
  exit /b 1
)

if not exist "%TERMINAL_DATA%\MQL5\Profiles\Tester" mkdir "%TERMINAL_DATA%\MQL5\Profiles\Tester"

copy /y "%EA_SOURCE%" "%TERMINAL_DATA%\MQL5\Experts\GoldTrendRiderEA.mq5" >nul
copy /y "%PRESET_SOURCE%" "%TERMINAL_DATA%\MQL5\Profiles\Tester\GoldTrendRider_Conservative.set" >nul

if not exist "%METAEDITOR%" (
  echo EA and preset installed, but MetaEditor was not found at:
  echo %METAEDITOR%
  echo Open MetaEditor and compile GoldTrendRiderEA.mq5 manually.
  pause
  exit /b 0
)

set "EA_TARGET=%TERMINAL_DATA%\MQL5\Experts\GoldTrendRiderEA.mq5"
set "COMPILE_LOG=%TEMP%\GoldTrendRiderEA.compile.log"
del /q "%COMPILE_LOG%" >nul 2>&1

"%METAEDITOR%" /compile:"%EA_TARGET%" /log:"%COMPILE_LOG%"

powershell.exe -NoProfile -Command "if (Select-String -LiteralPath '%COMPILE_LOG%' -SimpleMatch 'Result: 0 errors' -Quiet) { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo The EA was installed, but compilation reported a problem.
  echo Compile log: %COMPILE_LOG%
  type "%COMPILE_LOG%"
  pause
  exit /b 1
)

echo.
echo GoldTrendRiderEA installed and compiled successfully.
echo In MT5, refresh Navigator and attach it to your broker's gold chart on M15.
echo Keep Algo Trading off until demo backtesting and forward testing are complete.
echo.
pause
exit /b 0
