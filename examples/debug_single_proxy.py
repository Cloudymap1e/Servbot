"""Debug proxy connection - test with a single proxy."""
import requests
import logging

logging.basicConfig(level=logging.DEBUG)

# Test one proxy directly
proxy_string = "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-BwKSYmdm"

# Parse it
parts = proxy_string.split(":")
host = parts[0]
port = parts[1]
username = parts[2]
password = ":".join(parts[3:])  # In case password contains colons

print("="*80)
print("DEBUGGING MOOPROXY CONNECTION")
print("="*80)
print(f"Host: {host}")
print(f"Port: {port}")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"Password length: {len(password)}")

# Build proxy URL
proxy_url = f"http://{username}:{password}@{host}:{port}"
print(f"\nProxy URL: {proxy_url}")

proxies = {
    "http": proxy_url,
    "https": proxy_url
}

print("\n" + "="*80)
print("TESTING CONNECTION")
print("="*80)

# Try different test URLs
test_urls = [
    "http://httpbin.org/ip",
    "http://ipinfo.io/json",
    "http://api.ipify.org?format=json",
]

for test_url in test_urls:
    print(f"\nTesting: {test_url}")
    try:
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=30,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        print(f"  SUCCESS! Status: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        break
    except requests.exceptions.ProxyError as e:
        print(f"  ProxyError: {e}")
    except requests.exceptions.Timeout:
        print(f"  Timeout after 30s")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")

print("\n" + "="*80)
