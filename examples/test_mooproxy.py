"""Quick test for MooProxy provider modes."""

from servbot.proxy import ProviderConfig, ProxyManager

# Test static mode with pre-generated sessions
static_config = ProviderConfig(
    name="moo-static",
    type="mooproxy",
    price_per_gb=5.0,
    options={
        "entries": """us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-feDzDLCT
us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-5BJ18zsv
us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-6iztzK4d"""
    }
)

# Test dynamic mode with base credentials
dynamic_config = ProviderConfig(
    name="moo-dynamic",
    type="mooproxy",
    price_per_gb=5.0,
    options={
        "host": "us.mooproxy.net",
        "port": "55688",
        "username": "specu1",
        "password": "XJrImxWe7O",
        "country": "US"
    }
)

pm = ProxyManager([static_config, dynamic_config])

print("=== Static Mode (Round-robin) ===")
for i in range(5):
    ep = pm.get("moo-static").acquire()
    print(f"{i+1}. Session: {ep.session}")
    print(f"   Password: {ep.password}")
    print(f"   Requests: {ep.as_requests_proxies()['http']}")
    print()

print("=== Dynamic Mode (New sessions) ===")
for i in range(3):
    ep = pm.get("moo-dynamic").acquire()
    print(f"{i+1}. Session: {ep.session}")
    print(f"   Password: {ep.password}")
    print()

print("=== Dynamic with different region ===")
ep = pm.get("moo-dynamic").acquire(region="GB")
print(f"Session: {ep.session}")
print(f"Password: {ep.password}")
print(f"Playwright: {ep.as_playwright_proxy()}")
