"""Demo showcasing new proxy features: metering, logging, proxy types, and concurrency limits."""

from servbot.proxy import (
    ProxyManager,
    ProviderConfig,
    ProxyType,
    IPVersion,
    RotationType,
)
import logging

# Setup logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def demo_proxy_types():
    """Demo: Different proxy types."""
    print("\n" + "="*60)
    print("DEMO 1: Proxy Types (Residential, Datacenter, ISP, Mobile)")
    print("="*60)

    configs = [
        ProviderConfig(
            name="residential-proxy",
            type="static_list",
            price_per_gb=10.0,
            options={
                "entries": "1.2.3.4:8080",
                "proxy_type": "residential",
                "ip_version": "ipv4",
            }
        ),
        ProviderConfig(
            name="datacenter-proxy",
            type="static_list",
            price_per_gb=0.5,
            options={
                "entries": "5.6.7.8:9090",
                "proxy_type": "datacenter",
                "ip_version": "ipv4",
            }
        ),
        ProviderConfig(
            name="isp-proxy",
            type="static_list",
            price_per_gb=5.0,
            options={
                "entries": "9.10.11.12:3128",
                "proxy_type": "isp",
                "ip_version": "ipv4",
            }
        ),
    ]

    pm = ProxyManager(configs, enable_metering=False)

    for provider_name in ["residential-proxy", "datacenter-proxy", "isp-proxy"]:
        ep = pm.acquire(name=provider_name)
        print(f"\n{provider_name}:")
        print(f"  Type: {ep.proxy_type.value}")
        print(f"  IP Version: {ep.ip_version.value}")
        print(f"  Endpoint: {ep.host}:{ep.port}")


def demo_metering():
    """Demo: Detailed usage metering and cost tracking."""
    print("\n" + "="*60)
    print("DEMO 2: Usage Metering and Cost Tracking")
    print("="*60)

    config = ProviderConfig(
        name="metered-proxy",
        type="static_list",
        price_per_gb=10.0,  # $10 per GB
        options={
            "entries": "1.2.3.4:8080",
            "proxy_type": "residential",
        }
    )

    pm = ProxyManager([config], enable_metering=True)
    meter = pm.get_meter()

    # Acquire and use proxy
    ep = pm.acquire(name="metered-proxy", purpose="web-scraping")

    # Simulate multiple requests
    print("\nSimulating 5 requests...")
    for i in range(5):
        bytes_sent = 1024 * (i + 1)      # Increasing payload
        bytes_received = 4096 * (i + 1)  # Increasing response
        success = i < 4  # Last one fails

        meter.record_request(
            ep,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            success=success
        )
        print(f"  Request {i+1}: sent={bytes_sent}B recv={bytes_received}B success={success}")

    # Release
    pm.release(ep, reason="demo-complete")

    # Get metrics
    print("\n--- Usage Metrics ---")
    metrics = meter.get_metrics()
    for endpoint_id, m in metrics.items():
        print(f"Endpoint: {endpoint_id}")
        print(f"  Requests: {m.requests_count}")
        print(f"  Sent: {m.bytes_sent:,} bytes")
        print(f"  Received: {m.bytes_received:,} bytes")
        print(f"  Total: {m.total_gb:.6f} GB")
        print(f"  Errors: {m.errors_count}")
        print(f"  Success Rate: {m.success_rate:.1f}%")
        print(f"  Cost Estimate: ${m.cost_estimate:.4f}")

    # Get summary
    print("\n--- Summary ---")
    summary = meter.get_summary()
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Total GB: {summary['total_gb']}")
    print(f"Total Cost: ${summary['total_cost_estimate']:.4f}")
    print(f"Success Rate: {summary['overall_success_rate']}%")


def demo_concurrency_limits():
    """Demo: Concurrency limit enforcement."""
    print("\n" + "="*60)
    print("DEMO 3: Concurrency Limit Enforcement")
    print("="*60)

    config = ProviderConfig(
        name="limited-proxy",
        type="static_list",
        price_per_gb=5.0,
        concurrency_limit=2,  # Only 2 concurrent connections allowed
        options={
            "entries": "1.2.3.4:8080",
        }
    )

    pm = ProxyManager([config], enable_metering=False)

    print("\nAcquiring 2 proxies (within limit)...")
    ep1 = pm.acquire(name="limited-proxy")
    print(f"  Acquired 1: {ep1.host}:{ep1.port}")

    ep2 = pm.acquire(name="limited-proxy")
    print(f"  Acquired 2: {ep2.host}:{ep2.port}")

    print("\nAttempting to acquire 3rd proxy (should fail)...")
    try:
        ep3 = pm.acquire(name="limited-proxy")
        print("  ERROR: Should have failed!")
    except RuntimeError as e:
        print(f"  ✓ Correctly blocked: {e}")

    print("\nReleasing one proxy...")
    pm.release(ep1, reason="finished")
    print("  Released proxy 1")

    print("\nNow trying to acquire 3rd proxy again (should succeed)...")
    ep3 = pm.acquire(name="limited-proxy")
    print(f"  ✓ Acquired 3: {ep3.host}:{ep3.port}")

    # Cleanup
    pm.release(ep2)
    pm.release(ep3)


def demo_auto_selection():
    """Demo: Automatic cheapest provider selection."""
    print("\n" + "="*60)
    print("DEMO 4: Automatic Cheapest Provider Selection")
    print("="*60)

    configs = [
        ProviderConfig(
            name="expensive-premium",
            type="static_list",
            price_per_gb=20.0,
            options={"entries": "premium.proxy.com:8080"}
        ),
        ProviderConfig(
            name="cheap-datacenter",
            type="static_list",
            price_per_gb=0.5,
            options={"entries": "cheap.proxy.com:8080"}
        ),
        ProviderConfig(
            name="medium-residential",
            type="static_list",
            price_per_gb=10.0,
            options={"entries": "medium.proxy.com:8080"}
        ),
    ]

    pm = ProxyManager(configs, enable_metering=False)

    print("\nAcquiring proxy without specifying provider (auto-selects cheapest)...")
    ep = pm.acquire()
    print(f"  Selected: {ep.provider}")
    print(f"  Endpoint: {ep.host}:{ep.port}")
    print(f"  Expected: cheap-datacenter (lowest price_per_gb)")


def demo_statistics():
    """Demo: Real-time statistics."""
    print("\n" + "="*60)
    print("DEMO 5: Real-time Statistics and Monitoring")
    print("="*60)

    configs = [
        ProviderConfig(
            name="provider-a",
            type="static_list",
            price_per_gb=5.0,
            concurrency_limit=10,
            options={"entries": "a.proxy.com:8080"}
        ),
        ProviderConfig(
            name="provider-b",
            type="static_list",
            price_per_gb=8.0,
            concurrency_limit=20,
            options={"entries": "b.proxy.com:8080"}
        ),
    ]

    pm = ProxyManager(configs, enable_metering=True)

    # Acquire some proxies
    ep1 = pm.acquire(name="provider-a")
    ep2 = pm.acquire(name="provider-b")

    # Simulate usage
    meter = pm.get_meter()
    meter.record_request(ep1, bytes_sent=1024, bytes_received=2048, success=True)
    meter.record_request(ep2, bytes_sent=512, bytes_received=1024, success=True)

    # Get stats
    print("\n--- Provider Statistics ---")
    stats = pm.get_stats()
    print(f"Total Active Connections: {stats['total_active']}")

    for provider_name, provider_stats in stats['providers'].items():
        print(f"\n{provider_name}:")
        print(f"  Type: {provider_stats['type']}")
        print(f"  Price per GB: ${provider_stats['price_per_gb']}")
        print(f"  Concurrency Limit: {provider_stats['concurrency_limit']}")
        print(f"  Active Connections: {provider_stats['active_connections']}")

    # Usage summary
    if 'usage_summary' in stats:
        print("\n--- Usage Summary ---")
        summary = stats['usage_summary']
        print(f"Total Endpoints: {summary['total_endpoints']}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total GB: {summary['total_gb']}")

    # Cleanup
    pm.release(ep1)
    pm.release(ep2)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROXY MODULE - COMPREHENSIVE FEATURE DEMO")
    print("="*60)

    demo_proxy_types()
    demo_metering()
    demo_concurrency_limits()
    demo_auto_selection()
    demo_statistics()

    print("\n" + "="*60)
    print("ALL DEMOS COMPLETED!")
    print("="*60)
