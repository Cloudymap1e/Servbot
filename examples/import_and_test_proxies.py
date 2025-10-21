"""Import 38 MooProxy proxies, save to SQL, and test them all."""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.proxy import ProxyBatchImporter, ProxyTester
from servbot.proxy.database import ProxyDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# All 38 proxies (28 new + 10 existing)
ALL_PROXIES = [
    # Existing 10
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-feDzDLCT",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-5BJ18zsv",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-6iztzK4d",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-ABC123",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-XYZ789",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-DEF456",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-GHI012",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-JKL345",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-MNO678",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-PQR901",
    # New 28
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-BwKSYmdm",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-16CajDSJ",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-GuPnZGGz",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-gfwTfPSA",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-7avtydlI",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-3wq3omeQ",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-mhXkw9e6",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-9ZtSoQ9U",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-3bwijDbq",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-WrUTum4e",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-GGnrMFtr",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-INMK6T46",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-BXj4Ay3K",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-t3T5Ig3q",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-OZ7tapqU",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-WnD9KN5u",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-7Ibn7vR8",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-0jknuMyN",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-YI8fqOmD",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-uHJajIUY",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-pIX3Tlzu",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-K8o9Carv",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-9GjFQnbj",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-YXRvX76q",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-CSqvnWBc",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-FP9taPZy",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-mO9fxNkW",
    "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-ZkOpiBYN",
]

def main():
    print("\n" + "="*80)
    print("MOOPROXY IMPORT, SQL STORAGE & TESTING")
    print("="*80)
    print(f"\nTotal proxies: {len(ALL_PROXIES)}")

    # Step 1: Import and auto-detect
    print("\n" + "-"*80)
    print("STEP 1: Import & Auto-Detection")
    print("-"*80)

    endpoints = ProxyBatchImporter.import_from_list(
        ALL_PROXIES,
        provider_name="mooproxy-batch",
    )

    print(f"\nImported: {len(endpoints)}/{len(ALL_PROXIES)} proxies")
    if endpoints:
        sample = endpoints[0]
        print(f"\nDetection Results:")
        print(f"  Provider: {sample.provider}")
        print(f"  Type: {sample.proxy_type.value if sample.proxy_type else 'N/A'}")
        print(f"  Region: {sample.region}")
        print(f"  Session: {sample.session}")

    # Step 2: Save to SQL database
    print("\n" + "-"*80)
    print("STEP 2: Save to SQL Database")
    print("-"*80)

    db = ProxyDatabase("data/proxies.db")

    proxy_ids = db.add_proxies_batch(endpoints)
    print(f"\nSaved to database: {len(proxy_ids)}/{len(endpoints)} proxies")

    # Show database stats
    stats = db.get_database_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total Proxies: {stats['total_proxies']}")
    print(f"  Active Proxies: {stats['active_proxies']}")
    print(f"  By Provider: {stats['by_provider']}")

    # Step 3: Test proxies (with shorter timeout and fewer at a time)
    print("\n" + "-"*80)
    print("STEP 3: Testing Proxies")
    print("-"*80)
    print("\nNOTE: Testing with 5-second timeout. If proxies don't respond,")
    print("they may be inactive/expired or require valid subscription.")
    print()

    def progress(done, total):
        print(f"Tested: {done}/{total} ({done/total*100:.0f}%)", end='\r')

    # Test with shorter timeout
    results = ProxyTester.test_batch(
        endpoints,
        timeout=5,  # Shorter timeout
        max_workers=5,  # Fewer workers
        progress_callback=progress
    )

    print()  # New line after progress

    # Step 4: Save test results to database
    print("\n" + "-"*80)
    print("STEP 4: Save Test Results to Database")
    print("-"*80)

    for result in results:
        # Find proxy ID from metadata
        proxy_id = result.endpoint.metadata.get('db_id') if result.endpoint.metadata else None

        if not proxy_id:
            # Find by host/port/username/session
            all_proxies_in_db = db.get_all_proxies(active_only=False)
            for p in all_proxies_in_db:
                if (p.host == result.endpoint.host and
                    p.port == result.endpoint.port and
                    p.username == result.endpoint.username and
                    p.session == result.endpoint.session):
                    proxy_id = p.metadata.get('db_id')
                    break

        if proxy_id:
            db.record_test_result(
                proxy_id=proxy_id,
                success=result.success,
                response_time_ms=result.response_time_ms,
                status_code=result.status_code,
                error_message=result.error,
                test_url=result.test_url,
                response_ip=result.response_ip
            )

    print(f"Saved {len(results)} test results to database")

    # Step 5: Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    print(f"\nProxies Imported: {len(endpoints)}")
    print(f"Saved to Database: {len(proxy_ids)}")
    print(f"Tests Run: {len(results)}")
    print(f"  Working: {successful}")
    print(f"  Failed: {failed}")

    if successful > 0:
        print(f"\n[OK] {successful} proxies are working!")

        # Show working proxies
        print("\nWorking Proxies:")
        for i, result in enumerate([r for r in results if r.success], 1):
            ep = result.endpoint
            print(f"  {i}. {ep.host}:{ep.port} - Session: {ep.session} - {result.response_time_ms:.0f}ms")

    else:
        print("\n[WARNING] No proxies responded successfully.")
        print("\nPossible reasons:")
        print("  1. Proxies require active paid subscription")
        print("  2. Credentials are expired/invalid")
        print("  3. Network connectivity issues")
        print("  4. MooProxy service may be down")
        print("\nThe proxies are stored in the database and can be tested later.")

    # Show how to query database
    print("\n" + "-"*80)
    print("DATABASE USAGE")
    print("-"*80)
    print("\nTo query proxies from database:")
    print("  from servbot.proxy.database import ProxyDatabase")
    print("  db = ProxyDatabase('data/proxies.db')")
    print("  proxies = db.get_all_proxies()")
    print("  working = db.get_working_proxies()")
    print("  stats = db.get_database_stats()")

    db.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
