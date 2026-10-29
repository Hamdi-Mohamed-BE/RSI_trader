@echo off
rem Scan a QR code with the Telegram app to log in, then choose the channel. Run once; the login is saved in state\.
call "%~dp0Start Signals.bat" --login %*
