#!/usr/bin/env python
"""Comprehensive IMAP SSL debugging tool.

This script performs step-by-step diagnostics to identify IMAP SSL connection issues.
"""

import sys
from pathlib import Path

import socket
import ssl
import imaplib
from servbot.data.database import get_accounts

print("=" * 80)
print("IMAP SSL DIAGNOSTIC TOOL")
print("=" * 80)

# Get account
accounts = get_accounts()
if not accounts:
    print("‚ù?No accounts in database")
    sys.exit(1)

account = accounts[0]
email = account['email']
password = account.get('password', '')
imap_server = account.get('imap_server', 'imap.shanyouxiang.com')

print(f"\nüìß Account: {email}")
print(f"üñ•Ô∏? IMAP Server: {imap_server}")
print(f"üîë Password: {'*' * 10} ({len(password)} chars)")

# Test 1: DNS Resolution
print("\n" + "=" * 80)
print("TEST 1: DNS Resolution")
print("=" * 80)
try:
    ip = socket.gethostbyname(imap_server)
    print(f"‚ú?DNS resolved: {imap_server} -> {ip}")
except Exception as e:
    print(f"‚ù?DNS resolution failed: {e}")
    sys.exit(1)

# Test 2: Basic TCP Connection
print("\n" + "=" * 80)
print("TEST 2: Basic TCP Connection (Port 993)")
print("=" * 80)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((imap_server, 993))
    print(f"‚ú?TCP connection successful to {imap_server}:993")
    sock.close()
except Exception as e:
    print(f"‚ù?TCP connection failed: {e}")
    print("\nTrying port 143 (non-SSL IMAP)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((imap_server, 143))
        print(f"‚ú?TCP connection successful to {imap_server}:143")
        print("‚ö†Ô∏è  Port 143 works but port 993 doesn't - server may not support SSL")
        sock.close()
    except Exception as e2:
        print(f"‚ù?Port 143 also failed: {e2}")
    sys.exit(1)

# Test 3: SSL Certificate Check
print("\n" + "=" * 80)
print("TEST 3: SSL Certificate Information")
print("=" * 80)
try:
    context = ssl.create_default_context()
    with socket.create_connection((imap_server, 993), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=imap_server) as ssock:
            cert = ssock.getpeercert()
            print(f"‚ú?SSL handshake successful!")
            print(f"\nüìú Certificate Info:")
            print(f"   Subject: {dict(x[0] for x in cert['subject'])}")
            print(f"   Issuer: {dict(x[0] for x in cert['issuer'])}")
            print(f"   Version: {cert['version']}")
            print(f"   Not Before: {cert.get('notBefore')}")
            print(f"   Not After: {cert.get('notAfter')}")
            print(f"   Serial Number: {cert.get('serialNumber')}")
except ssl.SSLError as e:
    print(f"‚ù?SSL handshake failed: {e}")
    print(f"\nSSL Error details:")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error args: {e.args}")
    
    # Try with different TLS versions
    print("\n" + "-" * 80)
    print("Trying different TLS/SSL versions...")
    print("-" * 80)
    
    for tls_version, protocol in [
        ("TLS 1.2", ssl.PROTOCOL_TLSv1_2),
        ("TLS 1.1", ssl.PROTOCOL_TLSv1_1),
        ("TLS 1.0", ssl.PROTOCOL_TLSv1),
    ]:
        try:
            context = ssl.SSLContext(protocol)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((imap_server, 993), timeout=10) as sock:
                with context.wrap_socket(sock) as ssock:
                    print(f"‚ú?{tls_version} works!")
                    break
        except Exception as e:
            print(f"‚ù?{tls_version} failed: {e}")
    
except Exception as e:
    print(f"‚ù?Unexpected error: {e}")

# Test 4: Try IMAP connection with relaxed SSL
print("\n" + "=" * 80)
print("TEST 4: IMAP Connection (Relaxed SSL)")
print("=" * 80)
try:
    # Create relaxed SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    M = imaplib.IMAP4_SSL(imap_server, 993, ssl_context=ssl_context)
    print(f"‚ú?IMAP4_SSL connection successful!")
    print(f"   Server greeting: {M.welcome}")
    
    # Try login
    print(f"\nüîê Attempting login as {email}...")
    try:
        M.login(email, password)
        print(f"‚ú?Login successful!")
        
        # List folders
        typ, folders = M.list()
        print(f"\nüìÅ Available folders:")
        for folder in folders[:5]:
            print(f"   {folder.decode()}")
        
        M.logout()
        print("\n‚ú?ALL TESTS PASSED - IMAP is working!")
        
    except imaplib.IMAP4.error as e:
        print(f"‚ù?Login failed: {e}")
        print("   (Connection works but credentials may be incorrect)")
        M.logout()
        
except ssl.SSLError as e:
    print(f"‚ù?SSL error even with relaxed settings: {e}")
    print(f"\nThis suggests the server has serious SSL/TLS issues.")
    
    # Try STARTTLS on port 143
    print("\n" + "-" * 80)
    print("Trying STARTTLS on port 143...")
    print("-" * 80)
    try:
        M = imaplib.IMAP4(imap_server, 143)
        print(f"‚ú?Connected to port 143")
        print(f"   Server greeting: {M.welcome}")
        
        # Try STARTTLS
        M.starttls(ssl_context=ssl_context)
        print(f"‚ú?STARTTLS successful!")
        
        # Try login
        M.login(email, password)
        print(f"‚ú?Login successful via STARTTLS!")
        
        # List folders
        typ, folders = M.list()
        print(f"\nüìÅ Available folders:")
        for folder in folders[:5]:
            print(f"   {folder.decode()}")
        
        M.logout()
        print("\n‚ú?STARTTLS METHOD WORKS!")
        print("\nüí° SOLUTION: Use port 143 with STARTTLS instead of port 993")
        
    except Exception as e:
        print(f"‚ù?STARTTLS also failed: {e}")
        
except Exception as e:
    print(f"‚ù?Unexpected error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Alternative approach - try outlook.office365.com
print("\n" + "=" * 80)
print("TEST 5: Try Microsoft Outlook IMAP (outlook.office365.com)")
print("=" * 80)
print("Since this is an Outlook account, testing with Microsoft's IMAP server...")

try:
    ssl_context = ssl.create_default_context()
    M = imaplib.IMAP4_SSL('outlook.office365.com', 993, ssl_context=ssl_context)
    print(f"‚ú?Connected to outlook.office365.com:993")
    print(f"   Server greeting: {M.welcome}")
    
    # Try login
    M.login(email, password)
    print(f"‚ú?Login successful!")
    
    # List folders
    typ, folders = M.list()
    print(f"\nüìÅ Available folders:")
    for folder in folders[:5]:
        print(f"   {folder.decode()}")
    
    M.logout()
    print("\n‚ú?MICROSOFT OUTLOOK IMAP WORKS!")
    print("\nüí° RECOMMENDATION: Use 'outlook.office365.com' instead of 'imap.shanyouxiang.com'")
    
except Exception as e:
    print(f"‚ù?Microsoft Outlook IMAP also failed: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
