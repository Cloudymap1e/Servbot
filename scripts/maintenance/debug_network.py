#!/usr/bin/env python
"""Network diagnostic to check for DNS hijacking or proxy interference."""

import socket

print("=" * 80)
print("NETWORK DIAGNOSTIC - DNS & Connectivity Check")
print("=" * 80)

servers_to_test = [
    ("google.com", "Normal website"),
    ("imap.gmail.com", "Gmail IMAP"),
    ("outlook.office365.com", "Microsoft Outlook IMAP"),
    ("imap.shanyouxiang.com", "Shanyouxiang IMAP (Flashmail)"),
]

print("\n📡 DNS Resolution Test:")
print("-" * 80)
for hostname, description in servers_to_test:
    try:
        ip = socket.gethostbyname(hostname)
        print(f"  {hostname:30s} -> {ip:20s} ({description})")
        
        # Check if IP is in suspicious ranges
        octets = [int(x) for x in ip.split('.')]
        if octets[0] == 198 and octets[1] in [18, 19]:
            print(f"    ⚠️  WARNING: IP is in TEST-NET-2 range (198.18.0.0/15) - likely proxy/firewall")
        elif octets[0] == 10 or (octets[0] == 172 and 16 <= octets[1] <= 31) or (octets[0] == 192 and octets[1] == 168):
            print(f"    ⚠️  WARNING: Private IP address - likely local network/proxy")
            
    except Exception as e:
        print(f"  {hostname:30s} -> FAILED: {e}")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print("""
If you see the same IP (especially 198.18.x.x) for multiple different servers,
this indicates DNS hijacking or a transparent proxy is intercepting your traffic.

POSSIBLE CAUSES:
1. VPN software redirecting traffic
2. Corporate/school network with content filtering
3. Antivirus software with "HTTPS scanning" enabled
4. Firewall blocking IMAP/SSL traffic
5. ISP-level filtering or proxy

SOLUTIONS TO TRY:
1. Disable VPN temporarily and retry
2. Disable antivirus "HTTPS scanning" or "SSL inspection"
3. Try from a different network (mobile hotspot, different WiFi)
4. Check Windows Firewall settings
5. Check if there's a proxy configured in Windows (Settings > Network & Internet > Proxy)
6. Try using a different DNS server (e.g., Google DNS: 8.8.8.8)
""")
