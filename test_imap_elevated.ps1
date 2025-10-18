# PowerShell script to test IMAP with Meta tunnel disabled
# Automatically requests elevation if not running as administrator

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Not running as administrator. Requesting elevation..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "=" * 80
Write-Host "IMAP TEST WITH META TUNNEL DISABLED"
Write-Host "=" * 80
Write-Host ""

# Step 1: Disable Meta tunnel
Write-Host "[Step 1/4] Disabling Meta tunnel..." -ForegroundColor Cyan
try {
    netsh interface set interface "Meta" admin=disable
    Write-Host "  ✓ Meta tunnel disabled" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to disable Meta: $_" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Start-Sleep -Seconds 2

# Step 2: Test IMAP connection
Write-Host ""
Write-Host "[Step 2/4] Testing IMAP connection..." -ForegroundColor Cyan
Write-Host ""
python D:\servbot\servbot\debug_imap_ssl.py

# Step 3: Fetch and display email content
Write-Host ""
Write-Host "[Step 3/4] Fetching email content..." -ForegroundColor Cyan
Write-Host ""
python -c @"
import sys
sys.path.insert(0, 'D:/servbot')
from servbot.data.database import get_accounts
from servbot.clients import IMAPClient

accounts = get_accounts()
if not accounts:
    print('No accounts found')
    sys.exit(1)

account = accounts[0]
email = account['email']
password = account.get('password', '')
imap_server = account.get('imap_server', 'outlook.office365.com')

print(f'Connecting to {email}...')
try:
    client = IMAPClient(imap_server, email, password, 993, use_ssl=True)
    messages = client.fetch_messages(folder='INBOX', unseen_only=False, limit=10)
    
    print(f'\\nFetched {len(messages)} message(s)\\n')
    print('=' * 80)
    
    for i, msg in enumerate(messages[:5], 1):
        print(f'\\nMESSAGE {i}:')
        print(f'Subject: {msg.subject}')
        print(f'From: {msg.from_addr}')
        print(f'Date: {msg.received_date}')
        print(f'\\nContent (first 500 chars):')
        print('-' * 80)
        content = msg.body_text if msg.body_text else msg.body_html
        print(content[:500])
        print('-' * 80)
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
"@

# Step 4: Re-enable Meta tunnel
Write-Host ""
Write-Host "[Step 4/4] Re-enabling Meta tunnel..." -ForegroundColor Cyan
try {
    netsh interface set interface "Meta" admin=enable
    Write-Host "  ✓ Meta tunnel re-enabled" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Failed to re-enable Meta: $_" -ForegroundColor Yellow
    Write-Host "  You may need to re-enable it manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 80
Write-Host "TEST COMPLETE"
Write-Host "=" * 80
Write-Host ""
Read-Host "Press Enter to exit"
