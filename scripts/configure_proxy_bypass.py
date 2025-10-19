#!/usr/bin/env python
"""Configure Windows proxy bypass for IMAP servers.

This script adds IMAP servers to the Windows proxy bypass list so that
IMAP SSL connections can work while keeping the Meta tunnel active for
other traffic.
"""

import sys
import subprocess
import winreg
from pathlib import Path

print("=" * 80)
print("CONFIGURE PROXY BYPASS FOR IMAP")
print("=" * 80)

# IMAP servers that need bypass
IMAP_SERVERS = [
    'imap.shanyouxiang.com',
    'outlook.office365.com',
    'imap.gmail.com',
    'imap-mail.outlook.com',
    'smtp.office365.com',
    '*.shanyouxiang.com',
    '*.office365.com',
]

print("\n📋 IMAP servers to bypass:")
for server in IMAP_SERVERS:
    print(f"   - {server}")

# Method 1: Update Windows Registry
print("\n" + "=" * 80)
print("METHOD 1: Windows Registry Proxy Bypass")
print("=" * 80)

try:
    # Open Internet Settings registry key
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    
    # Read current bypass list
    try:
        current_bypass, _ = winreg.QueryValueEx(key, "ProxyOverride")
        print(f"\n📄 Current bypass list:")
        print(f"   {current_bypass}")
    except FileNotFoundError:
        current_bypass = ""
        print(f"\n📄 No existing bypass list")
    
    # Add IMAP servers to bypass list
    bypass_entries = [s.strip() for s in current_bypass.split(';') if s.strip()]
    
    added = []
    for server in IMAP_SERVERS:
        if server not in bypass_entries:
            bypass_entries.append(server)
            added.append(server)
    
    if added:
        new_bypass = ';'.join(bypass_entries)
        
        print(f"\n➕ Adding {len(added)} server(s) to bypass list:")
        for server in added:
            print(f"   + {server}")
        
        # Write back to registry
        winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, new_bypass)
        
        print(f"\n✅ Registry updated successfully!")
        print(f"\n📄 New bypass list:")
        print(f"   {new_bypass}")
    else:
        print(f"\n✅ All IMAP servers already in bypass list")
    
    winreg.CloseKey(key)
    
except Exception as e:
    print(f"\n❌ Registry update failed: {e}")
    print("\n⚠️  You may need to run this script as Administrator")

# Method 2: Create PAC file for advanced routing
print("\n" + "=" * 80)
print("METHOD 2: Create PAC File (Advanced)")
print("=" * 80)

pac_file_path = Path.home() / ".servbot" / "proxy.pac"
pac_file_path.parent.mkdir(exist_ok=True)

pac_content = '''function FindProxyForURL(url, host) {
    // Direct connection for IMAP servers (bypass proxy)
    if (shExpMatch(host, "*.shanyouxiang.com") ||
        shExpMatch(host, "*.office365.com") ||
        shExpMatch(host, "imap.gmail.com") ||
        shExpMatch(host, "smtp.gmail.com") ||
        shExpMatch(host, "outlook.office365.com") ||
        shExpMatch(host, "imap.shanyouxiang.com")) {
        return "DIRECT";
    }
    
    // Use proxy for everything else
    return "PROXY 127.0.0.1:7897";
}
'''

try:
    pac_file_path.write_text(pac_content)
    print(f"\n✅ PAC file created: {pac_file_path}")
    print(f"\n📝 PAC file content:")
    print(pac_content)
    
    print(f"\n💡 To use this PAC file:")
    print(f"   1. Open Windows Settings")
    print(f"   2. Go to Network & Internet > Proxy")
    print(f"   3. Enable 'Use setup script'")
    print(f"   4. Enter script address: file:///{pac_file_path.as_posix()}")
    print(f"   5. Click Save")
    
except Exception as e:
    print(f"\n❌ PAC file creation failed: {e}")

# Method 3: Set environment variables
print("\n" + "=" * 80)
print("METHOD 3: Environment Variables (Python-specific)")
print("=" * 80)

print("""
Set these environment variables to bypass proxy for Python scripts:

    set NO_PROXY=*.shanyouxiang.com,*.office365.com,imap.gmail.com
    set no_proxy=*.shanyouxiang.com,*.office365.com,imap.gmail.com

Or add them permanently via System Properties > Environment Variables.
""")

# Test the bypass
print("\n" + "=" * 80)
print("TESTING PROXY BYPASS")
print("=" * 80)

print("""
After applying the changes:

1. Close and reopen all applications (or restart)
2. Run the diagnostic again:
   
   python D:\\servbot\\servbot\\debug_imap_ssl.py

3. If it still fails, try Method 2 (PAC file) or temporarily disable Meta:
   
   netsh interface set interface "Meta" admin=disable
""")

print("\n" + "=" * 80)
print("IMPORTANT: Meta Tunnel Behavior")
print("=" * 80)
print("""
The Meta tunnel may override proxy bypass settings. If bypass doesn't work:

Option A: Disable Meta tunnel when using servbot:
   netsh interface set interface "Meta" admin=disable
   
Option B: Configure Meta tunnel directly (if it has settings)
   Check if Meta has a configuration file or control panel

Option C: Contact your IT/network administrator for whitelist
""")
