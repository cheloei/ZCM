@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: ZCombine - Project File Aggregator for AI Assistance
:: GitHub => https://github.com/cheloei/ZCM
:: Version => 1.0.0
:: ----------------------------------------------------------------------------
:: Purpose:
::   Recursively scans a directory, collects specified file types (excluding
::   common build/ dependency folders), strips empty lines, and merges all
::   non‑empty files into a single text file. The output is formatted with
::   clear file separators, making it easy to feed to an AI model or LLM for
::   code review, documentation, or refactoring.
::
:: Usage:
::   Simply run the script from the root of your project. It will produce
::   'zcm_output.txt' in the current directory.
::
:: Configuration (edit the variables below):
::   TARGET_FILES  : space‑separated list of file extensions/patterns to include
::   SEARCH_PATH   : root directory to scan (default: current directory)
::   IGNORE_DIRS   : folders to skip (e.g., node_modules, .git, dist)
::   OUTPUT_FILE   : name of the resulting merged file
::
:: Requirements:
::   - Windows (Batch script)
::   - PowerShell (for file reading, filtering, and writing with UTF‑8 no BOM)
::   - The script must be run with sufficient permissions to read all target
::     files and write to the output directory.
:: ============================================================================
:: ----------------------------------------
:: User‑configurable settings
:: ----------------------------------------
set "TARGET_FILES={{target}}"
set "SEARCH_PATH=."
set "IGNORE_DIRS={{ignore}}"
set "OUTPUT_FILE=zcm_output.txt"

:: Counters for reporting
set /a ADDED_FILES=0
set /a IGNORED_FILES=0

:: Temporary file to hold the list of files to process
set "TEMP_LIST=%TEMP%\zcombine_%RANDOM%.tmp"

:: ----------------------------------------
:: Display banner and configuration
:: ----------------------------------------
echo.
echo ============================================================
echo                         ZCombine
echo ============================================================
echo.
echo Search path : %SEARCH_PATH%
echo File types  : %TARGET_FILES%
echo Ignored     : %IGNORE_DIRS%
echo Output file : %OUTPUT_FILE%
echo.
echo ------------------------------------------------------------

:: Clean up any previous outputs and temporary files
if exist "%OUTPUT_FILE%" del /q "%OUTPUT_FILE%"
if exist "%TEMP_LIST%" del /q "%TEMP_LIST%"

:: ----------------------------------------
:: Step 1: Build the file list (recursive)
::   - For each file matching TARGET_FILES under SEARCH_PATH
::   - Skip the output file itself
::   - Skip any file that resides inside one of IGNORE_DIRS
::   - Append the full path to the temporary list
:: ----------------------------------------
for /r "%SEARCH_PATH%" %%F in (%TARGET_FILES%) do (

    set "FILE_PATH=%%~fF"
    set "IGNORE_FILE=0"

    :: Exclude the output file itself
    if /i "%%~nxF"=="%OUTPUT_FILE%" (
        set "IGNORE_FILE=1"
    )

    :: Exclude files inside ignored directories (case‑insensitive substring match)
    if !IGNORE_FILE!==0 (
        for %%I in (%IGNORE_DIRS%) do (
            set "TEST_PATH=!FILE_PATH:\%%I\=!"
            if not "!TEST_PATH!"=="!FILE_PATH!" (
                set "IGNORE_FILE=1"
            )
        )
    )

    :: Count ignored vs. included files
    if !IGNORE_FILE!==1 (
        set /a IGNORED_FILES+=1
    ) else (
        echo %%~fF>>"%TEMP_LIST%"
    )
)

:: ----------------------------------------
:: Step 2: Process each file via PowerShell
::   - Read the list of file paths
::   - For each non‑empty file:
::       * Compute relative path (relative to SEARCH_PATH)
::       * Read its content (UTF‑8)
::       * Strip blank lines (lines that contain only whitespace)
::       * If any non‑empty lines remain, write a header and the lines to the output
::       * Increment the added counter
::   - Write the final output with UTF‑8 encoding (no BOM)
::   - Save the added count to a temporary file for later display
:: ----------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$root = (Get-Location).Path + [IO.Path]::DirectorySeparatorChar;" ^
    "$output = Join-Path (Get-Location) '%OUTPUT_FILE%';" ^
    "$result = [Text.StringBuilder]::new();" ^
    "$files = Get-Content -LiteralPath '%TEMP_LIST%' -Encoding Default;" ^
    "$added = 0;" ^
    "foreach ($file in $files) {" ^
    "    if ([string]::IsNullOrWhiteSpace($file)) { continue }" ^
    "    $content = [IO.File]::ReadAllText($file, [Text.Encoding]::UTF8);" ^
    "    if ([string]::IsNullOrWhiteSpace($content)) { continue }" ^
    "    $relative = $file.Substring($root.Length).Replace('\','\');" ^
    "    $lines = $content -split '\r?\n' | Where-Object { $_.Trim() -ne '' };" ^
    "    if ($lines.Count -eq 0) { continue }" ^
    "    [void]$result.AppendLine('===== File: ""' + $relative + '"" =====');" ^
    "    foreach ($line in $lines) { [void]$result.AppendLine($line) }" ^
    "    [void]$result.AppendLine();" ^
    "    [void]$result.AppendLine();" ^
    "    $added++;" ^
    "    Write-Host ('[Added] ""' + $relative + '""')" ^
    "}" ^
    "[IO.File]::WriteAllText($output, $result.ToString(), [Text.UTF8Encoding]::new($false));" ^
    "Set-Content -LiteralPath '%TEMP_LIST%.count' -Value $added -Encoding ASCII"

:: ----------------------------------------
:: Step 3: Retrieve the added count from the temporary file
:: ----------------------------------------
if exist "%TEMP_LIST%.count" (
    set /p ADDED_FILES=<"%TEMP_LIST%.count"
)

:: ----------------------------------------
:: Step 4: Clean up temporary files
:: ----------------------------------------
if exist "%TEMP_LIST%" del /q "%TEMP_LIST%"
if exist "%TEMP_LIST%.count" del /q "%TEMP_LIST%.count"

:: ----------------------------------------
:: Step 5: Display final report
:: ----------------------------------------
echo.
echo ============================================================
echo                       FINAL REPORT
echo ============================================================
echo.
echo Search path     : %SEARCH_PATH%
echo Target files    : %TARGET_FILES%
echo Added files     : %ADDED_FILES%
echo Ignored files   : %IGNORED_FILES%
echo Output file     : %OUTPUT_FILE%
echo.
echo ------------------------------------------------------------
echo Search and combine completed.
echo ------------------------------------------------------------
echo.

pause
exit /b