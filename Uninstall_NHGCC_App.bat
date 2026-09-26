@echo off
title Uninstall NHGCC Oshodi Church Management System
echo Removing Desktop and Start Menu Shortcuts...
del /f /q "C:\Users\Home\Desktop\NHGCC Oshodi Church Database.lnk" 2>nul
del /f /q "C:\Users\Home\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\NHGCC Oshodi Church Database.lnk" 2>nul
echo Uninstall complete. Your church database backup remains in %LOCALAPPDATA%\NHGCC_Church_Database.
pause
