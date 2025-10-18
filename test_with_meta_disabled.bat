@echo off
REM Test IMAP connection with Meta tunnel disabled
REM Run as Administrator

echo ================================================================================
echo TEST: IMAP Connection with Meta Disabled
echo ================================================================================
echo.

echo [Step 1] Disabling Meta tunnel...
netsh interface set interface "Meta" admin=disable
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Need Administrator privileges!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)
echo Done!

echo.
echo [Step 2] Testing IMAP connection...
echo ================================================================================
echo.
python D:\servbot\servbot\debug_imap_ssl.py
echo.
echo ================================================================================

echo.
echo [Step 3] Re-enabling Meta tunnel...
netsh interface set interface "Meta" admin=enable
echo Done!

echo.
echo ================================================================================
echo Test complete! Check the results above.
echo ================================================================================
echo.
echo If IMAP connection succeeded, you can use: run_with_direct_connection.bat
echo.
pause
