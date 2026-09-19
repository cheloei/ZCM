@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: ZCombine Uninstaller - Windows
:: Removes: user PATH entry, Explorer context menu, Add/Remove Programs entry,
::          and the installation folder itself (self-delete).
:: ============================================================================

set "APP_KEY=ZCombineManager"

:: Resolve the folder this script lives in (which IS the install dir).
pushd "%~dp0"
set "INSTALL_DIR=%CD%"
popd

echo.
echo ============================================================
echo                 ZCombine Uninstaller
echo ============================================================
echo.
echo Install dir : %INSTALL_DIR%
echo.

call :RemoveFromUserPath "%INSTALL_DIR%"
call :RemoveContextMenu
call :RemoveUninstallReg
call :ScheduleFolderDeletion "%INSTALL_DIR%"

echo.
echo [OK] ZCombine has been uninstalled.
echo.
exit /b 0


:: ============================================================================
:: Subroutines
:: ============================================================================

:RemoveFromUserPath
set "REMOVE_PATH=%~1"
for /f "usebackq tokens=2*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do set "CURRENT_PATH=%%B"
if not defined CURRENT_PATH (
    echo [-] User PATH not found. Skipping.
    goto :eof
)

set "NEW_PATH="
for %%p in ("%CURRENT_PATH:;=";"%") do (
    set "ITEM=%%~p"
    if /i not "!ITEM!"=="%REMOVE_PATH%" (
        if defined NEW_PATH (set "NEW_PATH=!NEW_PATH!;!ITEM!") else (set "NEW_PATH=!ITEM!")
    )
)

if defined NEW_PATH (
    reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul 2>&1
    echo [+] Removed from user PATH.
) else (
    reg delete "HKCU\Environment" /v Path /f >nul 2>&1
    echo [+] User PATH emptied.
)
goto :eof


:RemoveContextMenu
reg query "HKCU\Software\Classes\Directory\Background\shell\ZCombine" >nul 2>&1
if errorlevel 1 (
    echo [-] Context menu not found.
    goto :eof
)
reg delete "HKCU\Software\Classes\Directory\Background\shell\ZCombine" /f >nul 2>&1
echo [+] Context menu removed.
goto :eof


:RemoveUninstallReg
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_KEY%" >nul 2>&1
if errorlevel 1 (
    echo [-] Add/Remove Programs entry not found.
    goto :eof
)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_KEY%" /f >nul 2>&1
echo [+] Add/Remove Programs entry removed.
goto :eof


:ScheduleFolderDeletion
:: Fire a detached cmd that waits ~2s, then removes the install folder.
set "TARGET=%~1"
echo [+] Scheduling cleanup of "%TARGET%"...
start "" /min cmd /c "ping 127.0.0.1 -n 3 >nul & rmdir /s /q ""%TARGET%"" 2>nul"
goto :eof