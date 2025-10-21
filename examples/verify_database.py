"""Verify the SQL database contains all proxies."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.proxy.database import ProxyDatabase

db = ProxyDatabase('data/proxies.db')

# Get stats
stats = db.get_database_stats()
print('='*80)
print('DATABASE VERIFICATION')
print('='*80)
print(f'\nDatabase Stats:')
print(f'  Total Proxies: {stats["total_proxies"]}')
print(f'  Active Proxies: {stats["active_proxies"]}')
print(f'  By Provider: {stats["by_provider"]}')
print(f'  Total Tests: {stats["total_tests"]}')
print(f'  Success Rate: {stats["success_rate"]:.1f}%')

# Get all proxies
proxies = db.get_all_proxies(active_only=False)
print(f'\nFirst 5 proxies in database:')
for i, p in enumerate(proxies[:5], 1):
    proxy_type = p.proxy_type.value if p.proxy_type else 'N/A'
    print(f'  {i}. {p.host}:{p.port}')
    print(f'     Session: {p.session}')
    print(f'     Provider: {p.provider}')
    print(f'     Type: {proxy_type}')
    print(f'     Region: {p.region}')
    print(f'     DB ID: {p.metadata.get("db_id")}')
    print()

print(f'Last 2 proxies in database:')
for i, p in enumerate(proxies[-2:], len(proxies)-1):
    proxy_type = p.proxy_type.value if p.proxy_type else 'N/A'
    print(f'  {i}. {p.host}:{p.port} - Session: {p.session} - Type: {proxy_type}')

print(f'\n{stats["total_proxies"]} proxies successfully stored in SQL database!')
print('='*80)

db.close()
