@echo off
REM Run servbot with Meta tunnel temporarily disabled for direct IMAP access
REM This script requires Administrator privileges

echo ================================================================================
echo SERVBOT - Direct Connection Mode
echo ================================================================================
echo.
echo This will temporarily disable Meta tunnel to allow IMAP connections.
echo Meta tunnel will be re-enabled after servbot exits.
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo [1/3] Disabling Meta tunnel...
netsh interface set interface "Meta" admin=disable
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to disable Meta tunnel. Are you running as Administrator?
    pause
    exit /b 1
)
echo      Done!

echo.
echo [2/3] Running servbot...
echo ================================================================================
echo.
python -m servbot
echo.
echo ================================================================================

echo.
echo [3/3] Re-enabling Meta tunnel...
netsh interface set interface "Meta" admin=enable
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Failed to re-enable Meta tunnel. You may need to do this manually.
) else (
    echo      Done!
)

echo.
echo ================================================================================
echo COMPLETE
echo ================================================================================
echo.
pause
