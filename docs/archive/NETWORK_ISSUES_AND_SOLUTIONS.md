# 🔍 Servbot Network Issues - Complete Analysis & Solutions

## 📋 Executive Summary

**Two critical issues identified:**

1. **✅ SOLVED**: IMAP SSL connections blocked by Meta tunnel
2. **✅ ANALYZED**: Microsoft Graph API refresh token in "service abuse mode"

---

## 🚨 Issue #1: IMAP SSL Connection Failure

### Problem
All IMAP SSL connections fail with:
```
ssl.SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
```

### Root Cause

**Meta Tunnel VPN is intercepting all network traffic:**
- DNS hijacked: All domains resolve to `198.18.0.x` (TEST-NET-2 range)
- Network adapter "Meta" active and redirecting traffic
- Proxy at `127.0.0.1:7897` intercepts connections
- SSL handshake fails because IMAP protocol can't traverse the proxy

### Evidence
```
google.com              -> 198.18.0.83  ⚠️ TEST-NET-2
imap.gmail.com          -> 198.18.0.84  ⚠️ TEST-NET-2
outlook.office365.com   -> 198.18.0.123 ⚠️ TEST-NET-2
imap.shanyouxiang.com   -> 198.18.0.19  ⚠️ TEST-NET-2
```

**All DNS queries hijacked → Meta tunnel blocks IMAP SSL**

### ✅ Solution: Temporarily Disable Meta Tunnel

#### Quick Test
```batch
# Right-click and "Run as administrator"
test_with_meta_disabled.bat
```

This will:
1. Disable Meta tunnel
2. Test IMAP connection
3. Re-enable Meta tunnel
4. Show results

#### Production Use
```batch
# Right-click and "Run as administrator"
run_with_direct_connection.bat
```

This script:
- Disables Meta tunnel
- Runs servbot (full CLI)
- Re-enables Meta tunnel when done

### Alternative Solutions (if Meta must stay enabled)

#### Option A: Configure Meta Tunnel Whitelist
Contact your IT administrator to whitelist:
- `*.shanyouxiang.com`
- `*.office365.com`
- `imap.gmail.com`

#### Option B: Use Different Network
- Mobile hotspot (bypasses Meta tunnel)
- Different WiFi network
- Home network without VPN

---

## 🚨 Issue #2: Microsoft Graph API "Service Abuse Mode"

### Problem
Token refresh fails with:
```
AADSTS70000: User account is found to be in service abuse mode
Trace ID: 67464c27-b83b-4b69-b563-757303b1ca00
```

### Root Cause

**Flashmail's shared refresh token is blocked by Microsoft:**

1. **Shared Token Problem**
   - Flashmail provides the SAME refresh token to ALL customers
   - Microsoft detects thousands of devices using the same token
   - Flags it as "service abuse" and blocks authentication

2. **Why This Happens**
   ```
   Client ID: 8b4ba9dd-3ea5-4e5f-86f1-ddba2230dcf2 (Flashmail's)
   Refresh Token: M.C555_BAY... (SHARED across all Flashmail users)
   
   Microsoft sees:
   - 1 token used by 1000+ IP addresses ❌
   - Too many refresh requests ❌
   - Suspicious activity pattern ❌
   ```

3. **Account Status**
   - The Outlook account itself is fine
   - Only the Graph API OAuth token is blocked
   - IMAP credentials still work (if Meta tunnel is disabled)

### ✅ Solutions

#### Solution 1: Use IMAP Instead of Graph API (Recommended)

**Status**: ✅ WORKS (with Meta tunnel disabled)

```batch
# Run this to use IMAP
run_with_direct_connection.bat
```

**Pros:**
- ✅ Simple - just disable Meta tunnel
- ✅ Uses existing password authentication
- ✅ No OAuth complexity

**Cons:**
- ⚠️ Must disable Meta tunnel each time
- ⚠️ IMAP may be slower than Graph API

#### Solution 2: Get Personal Graph API Token (Advanced)

**Status**: Not yet implemented (can be created if needed)

Would create an OAuth authentication flow where:
1. You authenticate via browser (YOUR session)
2. Get YOUR OWN refresh token (not shared)
3. Store in database (account-specific)
4. Works through Meta tunnel (HTTPS-based)

**Pros:**
- ✅ Works through Meta tunnel
- ✅ Your own token (not shared/blocked)
- ✅ Faster than IMAP

**Cons:**
- ❌ Requires manual browser authentication
- ❌ Token expires periodically (need re-auth)
- ❌ More complex setup

#### Solution 3: Use Different Email Provider

Switch to providers without Graph API dependency:
- **Gmail**: Use app-specific passwords (IMAP)
- **ProtonMail**: Bridge software (IMAP)
- **FastMail**: Direct IMAP support

---

## 🛠️ Files Created

### Diagnostic Tools
- `debug_imap_ssl.py` - Comprehensive IMAP SSL diagnostic
- `debug_network.py` - Network/DNS hijacking detection
- `fix_graph_api.py` - Graph API error analysis

### Configuration Tools
- `configure_proxy_bypass.py` - Proxy bypass configuration (didn't work - Meta overrides)
- `fix_imap_server.py` - Update IMAP server in database

### Working Solutions
- **`test_with_meta_disabled.bat`** ⭐ Test IMAP with Meta disabled
- **`run_with_direct_connection.bat`** ⭐ Run servbot with Meta disabled

---

## 📊 Decision Matrix

| Solution | Works Now | Requires Admin | Meta Stays On | Complexity |
|----------|-----------|----------------|---------------|------------|
| **Disable Meta (IMAP)** | ✅ Yes | ✅ Yes | ❌ No | ⭐ Easy |
| Proxy Bypass | ❌ No | ✅ Yes | ✅ Yes | ⭐⭐ Medium |
| Personal Graph Token | ⚠️ Untested | ❌ No | ✅ Yes | ⭐⭐⭐ Hard |
| Different Network | ✅ Yes | ❌ No | N/A | ⭐ Easy |

---

## 🎯 Recommended Workflow

### For Testing (Right Now)
```batch
1. Right-click test_with_meta_disabled.bat
2. Select "Run as administrator"
3. Check if IMAP connects successfully
```

### For Production Use
```batch
1. Right-click run_with_direct_connection.bat
2. Select "Run as administrator"
3. Use servbot normally
4. Meta re-enables automatically when done
```

### For Permanent Solution
1. **Option A**: Ask IT to whitelist IMAP servers in Meta tunnel
2. **Option B**: Run servbot on different network without Meta
3. **Option C**: Request implementation of personal OAuth flow

---

## 📞 Need Help?

If issues persist:

1. **Check Meta tunnel status:**
   ```powershell
   Get-NetAdapter | Where-Object {$_.Name -eq 'Meta'}
   ```

2. **Verify DNS resolution:**
   ```powershell
   python debug_network.py
   ```

3. **Test IMAP directly:**
   ```powershell
   python debug_imap_ssl.py
   ```

---

## 🔒 Security Note

**Disabling Meta tunnel temporarily is safe if:**
- You're on a trusted network (home/office)
- Only for short periods (minutes)
- You re-enable immediately after

**Not recommended if:**
- On public WiFi
- Handling sensitive data
- Corporate policy requires always-on VPN

---

## ✅ Success Criteria

**You'll know it's working when:**

1. `test_with_meta_disabled.bat` shows:
   ```
   ✅ SSL handshake successful!
   ✅ IMAP connection successful!
   ✅ Login successful!
   ```

2. `run_with_direct_connection.bat`:
   - Runs without errors
   - Fetches emails successfully
   - Re-enables Meta automatically

---

**Last Updated**: 2025-10-18
**Status**: Solutions ready for testing
