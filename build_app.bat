@echo off
title Build NHGCC Oshodi Church Desktop Application
echo =======================================================================
echo   BUILDING NHGCC OSHODI CHURCH DESKTOP APPLICATION (.EXE)
echo =======================================================================
echo.

where pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] PyInstaller not found. Installing pyinstaller...
    python -m pip install pyinstaller
)

echo [*] Compiling Windows Executable with PyInstaller...
pyinstaller --noconfirm nhgcc_desktop.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================================
    echo   [SUCCESS] BUILD COMPLETE!
    echo   Executable is ready at: dist\NHGCC_Church_Database.exe
    echo =======================================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the error messages above.
)
pause
