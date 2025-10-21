"""Test all 38 MooProxy proxies (28 new + 10 existing)."""
import logging
from servbot.proxy import ProxyBatchImporter, ProxyTester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Existing 10 proxies
EXISTING_PROXIES = [
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
]

# New 28 proxies from user
NEW_PROXIES = [
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

def progress_callback(completed, total):
    """Print progress updates."""
    percentage = (completed / total) * 100
    print(f"Progress: {completed}/{total} ({percentage:.1f}%) - Testing proxies...")

def main():
    print("\n" + "="*80)
    print("TESTING ALL 38 MOOPROXY PROXIES")
    print("="*80)

    # Combine all proxies
    all_proxies = EXISTING_PROXIES + NEW_PROXIES
    print(f"\nTotal proxies to test: {len(all_proxies)}")
    print(f"  - Existing: {len(EXISTING_PROXIES)}")
    print(f"  - New: {len(NEW_PROXIES)}")

    # Import and auto-detect
    print("\n" + "-"*80)
    print("STEP 1: Importing and Auto-Detecting Proxies")
    print("-"*80)

    endpoints = ProxyBatchImporter.import_from_list(
        all_proxies,
        provider_name="mooproxy-batch",
    )

    print(f"\nSuccessfully imported: {len(endpoints)}/{len(all_proxies)} proxies")

    # Show detection results
    print("\nAuto-Detection Results:")
    if endpoints:
        sample = endpoints[0]
        print(f"  Provider: {sample.provider}")
        print(f"  Proxy Type: {sample.proxy_type.value if sample.proxy_type else 'N/A'}")
        print(f"  IP Version: {sample.ip_version.value if sample.ip_version else 'N/A'}")
        print(f"  Rotation Type: {sample.rotation_type.value if sample.rotation_type else 'N/A'}")
        print(f"  Region: {sample.region or 'N/A'}")
        print(f"  Session Format: {sample.session or 'N/A'}")

    # Test all proxies
    print("\n" + "-"*80)
    print("STEP 2: Testing All Proxies")
    print("-"*80)
    print(f"\nTesting {len(endpoints)} proxies in parallel...")
    print("This may take a few minutes...\n")

    results = ProxyTester.test_batch(
        endpoints,
        timeout=15,  # 15 second timeout per proxy
        max_workers=10,  # Test 10 proxies at a time
        progress_callback=progress_callback,
    )

    # Print summary
    ProxyTester.print_test_summary(results)

    # Save working proxies to file
    working_proxies = [r.endpoint for r in results if r.success]
    if working_proxies:
        print(f"\n{'='*80}")
        print("SAVING WORKING PROXIES")
        print(f"{'='*80}")

        output_file = "config/working_mooproxy_proxies.txt"
        try:
            with open(output_file, 'w') as f:
                for ep in working_proxies:
                    f.write(f"{ep.host}:{ep.port}:{ep.username}:{ep.password}\n")
            print(f"\n✓ Saved {len(working_proxies)} working proxies to: {output_file}")
        except Exception as e:
            print(f"\n✗ Error saving proxies: {e}")

    # Summary stats
    print(f"\n{'='*80}")
    print("FINAL STATISTICS")
    print(f"{'='*80}")
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    success_rate = (successful / len(results) * 100) if results else 0

    print(f"Total Tested: {len(results)}")
    print(f"Working: {successful} ({success_rate:.1f}%)")
    print(f"Failed: {failed} ({100-success_rate:.1f}%)")

    if successful > 0:
        avg_time = sum(r.response_time_ms for r in results if r.success) / successful
        print(f"Average Response Time: {avg_time:.0f}ms")

    print(f"\n{'='*80}")
    print("TEST COMPLETE!")
    print(f"{'='*80}\n")

    return results

if __name__ == "__main__":
    main()
