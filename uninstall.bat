@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: ZCombine Uninstaller - Batch version
:: ============================================================

set "APP_KEY=ZCombineManager"
set "INSTALL_DIR=%LOCALAPPDATA%\%APP_KEY%"

echo.
echo ========================================
echo      ZCombine Uninstaller
echo ========================================
echo.

:: 1. Remove from User PATH
call :RemoveFromUserPath "%INSTALL_DIR%"

:: 2. Remove Context Menu
call :RemoveContextMenu

:: 3. Remove Uninstall Registry Key
call :RemoveUninstallReg

:: 4. Broadcast environment change (using a temp PowerShell script)
call :BroadcastEnvChange

:: 5. Delete installation folder (with delay)
echo [+] Cleanup complete. Removing installed files...
call :DelayedDelete "%INSTALL_DIR%"

echo.
echo ZCombine Manager has been uninstalled.
exit /b

:: ============================================================
:: Subroutines
:: ============================================================

:RemoveFromUserPath
set "REMOVE_PATH=%~1"
set "REG_KEY=HKCU\Environment"
set "REG_VAL=Path"

:: Read current PATH from registry
for /f "usebackq tokens=2*" %%A in (`reg query "%REG_KEY%" /v "%REG_VAL%" 2^>nul`) do (
    set "CURRENT_PATH=%%B"
)

if not defined CURRENT_PATH (
    echo [-] PATH not found in registry. Skipping.
    goto :eof
)

:: Remove the target directory from PATH
set "NEW_PATH="
for %%p in ("%CURRENT_PATH:;=";"%") do (
    set "ITEM=%%~p"
    if /i not "!ITEM!"=="%REMOVE_PATH%" (
        if defined NEW_PATH (
            set "NEW_PATH=!NEW_PATH!;!ITEM!"
        ) else (
            set "NEW_PATH=!ITEM!"
        )
    )
)

:: Write back to registry (REG_EXPAND_SZ)
if defined NEW_PATH (
    reg add "%REG_KEY%" /v "%REG_VAL%" /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul 2>&1
    echo [+] Removed from User PATH.
) else (
    :: If PATH becomes empty, delete the value
    reg delete "%REG_KEY%" /v "%REG_VAL%" /f >nul 2>&1
    echo [+] PATH was emptied and removed from registry.
)
goto :eof

:RemoveContextMenu
set "MENU_PATH=HKCU\Software\Classes\Directory\Background\shell\ZCombine"

reg query "%MENU_PATH%" >nul 2>&1
if errorlevel 1 (
    echo [-] Context menu entry not found.
    goto :eof
)

reg delete "%MENU_PATH%\command" /f >nul 2>&1
reg delete "%MENU_PATH%" /f >nul 2>&1
echo [+] Context menu removed.
goto :eof

:RemoveUninstallReg
set "UNINST_PATH=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_KEY%"

reg query "%UNINST_PATH%" >nul 2>&1
if errorlevel 1 (
    echo [-] Uninstall registry entry not found.
    goto :eof
)

reg delete "%UNINST_PATH%" /f >nul 2>&1
echo [+] Removed from Installed Apps registry.
goto :eof

:BroadcastEnvChange
:: Create a temporary PowerShell script to broadcast environment change
set "PS_SCRIPT=%TEMP%\broadcast_env_%RANDOM%.ps1"
(
echo Add-Type -TypeDefinition @"
echo using System;
echo using System.Runtime.InteropServices;
echo public class EnvBroadcast {
echo     [DllImport("user32.dll", SetLastError = true)]
echo     public static extern IntPtr SendMessageTimeout(
echo         IntPtr hWnd, uint Msg, IntPtr wParam, string lParam,
echo         uint fuFlags, uint uTimeout, out IntPtr lpdwResult);
echo }
echo "@
echo 
echo $HWND_BROADCAST = [IntPtr]0xFFFF;
echo $WM_SETTINGCHANGE = 0x001A;
echo $SMTO_ABORTIFHUNG = 0x0002;
echo $result = [IntPtr]::Zero;
echo [EnvBroadcast]::SendMessageTimeout(
echo     $HWND_BROADCAST, $WM_SETTINGCHANGE, [IntPtr]::Zero,
echo     "Environment", $SMTO_ABORTIFHUNG, 5000, [ref]$result
echo ) ^| Out-Null
) > "%PS_SCRIPT%"

:: Execute the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" >nul 2>&1
if errorlevel 1 (
    echo [-] Failed to broadcast environment change.
) else (
    echo [+] Environment changes broadcasted.
)

:: Clean up temp file
del "%PS_SCRIPT%" 2>nul
goto :eof

:DelayedDelete
set "TARGET_DIR=%~1"

:: Use a separate cmd process to delete after a short delay
start /min cmd /c "ping 127.0.0.1 -n 3 >nul & rmdir /s /q "%TARGET_DIR%" 2>nul & if exist "%TARGET_DIR%" (echo [-] Could not delete all files. You may need to remove manually.) else (echo [+] Folder deleted.)"
goto :eof