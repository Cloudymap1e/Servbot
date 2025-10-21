"""Comprehensive tests for proxy module."""
import pytest
from servbot.proxy import (
    ProxyEndpoint,
    ProviderConfig,
    ProxyManager,
    ProxyType,
    IPVersion,
    RotationType,
)
from servbot.proxy.meter import ProxyMeter, ProxyUsageMetrics


class TestProxyModels:
    """Test proxy data models."""

    def test_proxy_endpoint_creation(self):
        """Test basic ProxyEndpoint creation."""
        endpoint = ProxyEndpoint(
            scheme="http",
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
            provider="test-provider",
            session="session123",
            proxy_type=ProxyType.RESIDENTIAL,
            ip_version=IPVersion.IPV4,
            rotation_type=RotationType.ROTATING,
            region="US",
        )

        assert endpoint.scheme == "http"
        assert endpoint.host == "proxy.example.com"
        assert endpoint.port == 8080
        assert endpoint.username == "user"
        assert endpoint.password == "pass"
        assert endpoint.proxy_type == ProxyType.RESIDENTIAL
        assert endpoint.ip_version == IPVersion.IPV4
        assert endpoint.rotation_type == RotationType.ROTATING
        assert endpoint.region == "US"

    def test_proxy_endpoint_requests_format(self):
        """Test requests library proxy format."""
        endpoint = ProxyEndpoint(
            scheme="http",
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
        )

        proxies = endpoint.as_requests_proxies()
        expected = "http://user:pass@proxy.example.com:8080"
        assert proxies["http"] == expected
        assert proxies["https"] == expected

    def test_proxy_endpoint_playwright_format(self):
        """Test Playwright proxy format."""
        endpoint = ProxyEndpoint(
            scheme="http",
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
        )

        proxy = endpoint.as_playwright_proxy()
        assert proxy["server"] == "http://proxy.example.com:8080"
        assert proxy["username"] == "user"
        assert proxy["password"] == "pass"

    def test_proxy_type_enum(self):
        """Test ProxyType enum values."""
        assert ProxyType.RESIDENTIAL.value == "residential"
        assert ProxyType.DATACENTER.value == "datacenter"
        assert ProxyType.ISP.value == "isp"
        assert ProxyType.MOBILE.value == "mobile"

    def test_ip_version_enum(self):
        """Test IPVersion enum values."""
        assert IPVersion.IPV4.value == "ipv4"
        assert IPVersion.IPV6.value == "ipv6"

    def test_rotation_type_enum(self):
        """Test RotationType enum values."""
        assert RotationType.ROTATING.value == "rotating"
        assert RotationType.STICKY.value == "sticky"


class TestStaticListProvider:
    """Test StaticListProvider."""

    def test_static_list_basic(self):
        """Test basic static list provider."""
        config = ProviderConfig(
            name="test-static",
            type="static_list",
            price_per_gb=0.0,
            options={
                "entries": "1.2.3.4:8080, 5.6.7.8:9090",
                "proxy_type": "datacenter",
            },
        )

        pm = ProxyManager([config], enable_metering=False)
        ep = pm.acquire(name="test-static")

        assert ep.provider == "test-static"
        assert ep.proxy_type == ProxyType.DATACENTER
        assert ep.host in ["1.2.3.4", "5.6.7.8"]

    def test_static_list_with_auth(self):
        """Test static list with authentication."""
        config = ProviderConfig(
            name="test-static-auth",
            type="static_list",
            options={
                "entries": "user:pass@1.2.3.4:8080",
            },
        )

        pm = ProxyManager([config], enable_metering=False)
        ep = pm.acquire(name="test-static-auth")

        assert ep.username == "user"
        assert ep.password == "pass"
        assert ep.host == "1.2.3.4"
        assert ep.port == 8080

    def test_static_list_round_robin(self):
        """Test round-robin cycling."""
        config = ProviderConfig(
            name="test-rr",
            type="static_list",
            options={
                "entries": "1.1.1.1:8080, 2.2.2.2:8080, 3.3.3.3:8080",
            },
        )

        pm = ProxyManager([config], enable_metering=False)
        provider = pm.get("test-rr")

        # Acquire 6 times, should cycle twice through 3 endpoints
        hosts = [provider.acquire().host for _ in range(6)]
        assert hosts == ["1.1.1.1", "2.2.2.2", "3.3.3.3", "1.1.1.1", "2.2.2.2", "3.3.3.3"]


class TestMooProxyProvider:
    """Test MooProxyProvider."""

    def test_mooproxy_static_mode(self):
        """Test MooProxy static mode with pre-generated sessions."""
        config = ProviderConfig(
            name="test-moo-static",
            type="mooproxy",
            options={
                "entries": "us.mooproxy.net:55688:user:pass_country-US_session-ABC",
            },
        )

        pm = ProxyManager([config], enable_metering=False)
        ep = pm.acquire(name="test-moo-static")

        assert ep.host == "us.mooproxy.net"
        assert ep.port == 55688
        assert ep.username == "user"
        assert ep.session == "ABC"
        assert ep.region == "US"

    def test_mooproxy_dynamic_mode(self):
        """Test MooProxy dynamic mode with session generation."""
        config = ProviderConfig(
            name="test-moo-dynamic",
            type="mooproxy",
            options={
                "host": "us.mooproxy.net",
                "port": "55688",
                "username": "testuser",
                "password": "testpass",
                "country": "US",
            },
        )

        pm = ProxyManager([config], enable_metering=False)
        ep1 = pm.acquire(name="test-moo-dynamic")
        ep2 = pm.acquire(name="test-moo-dynamic")

        # Different sessions should be generated
        assert ep1.session != ep2.session
        assert ep1.host == "us.mooproxy.net"
        assert "_session-" in ep1.password
        assert "_country-US" in ep1.password


class TestProxyManager:
    """Test ProxyManager functionality."""

    def test_manager_initialization(self):
        """Test ProxyManager initialization with multiple providers."""
        configs = [
            ProviderConfig(
                name="cheap",
                type="static_list",
                price_per_gb=1.0,
                options={"entries": "1.2.3.4:8080"},
            ),
            ProviderConfig(
                name="expensive",
                type="static_list",
                price_per_gb=10.0,
                options={"entries": "5.6.7.8:9090"},
            ),
        ]

        pm = ProxyManager(configs)
        assert len(pm._providers) == 2
        assert "cheap" in pm._providers
        assert "expensive" in pm._providers

    def test_auto_select_cheapest(self):
        """Test automatic selection of cheapest provider."""
        configs = [
            ProviderConfig(
                name="expensive",
                type="static_list",
                price_per_gb=10.0,
                options={"entries": "5.6.7.8:9090"},
            ),
            ProviderConfig(
                name="cheap",
                type="static_list",
                price_per_gb=1.0,
                options={"entries": "1.2.3.4:8080"},
            ),
        ]

        pm = ProxyManager(configs, enable_metering=False)
        ep = pm.acquire()  # Should select cheapest

        assert ep.provider == "cheap"

    def test_concurrency_limit(self):
        """Test concurrency limit enforcement."""
        config = ProviderConfig(
            name="limited",
            type="static_list",
            price_per_gb=1.0,
            concurrency_limit=2,
            options={"entries": "1.2.3.4:8080"},
        )

        pm = ProxyManager([config], enable_metering=False)

        # Acquire 2 (should succeed)
        ep1 = pm.acquire(name="limited")
        ep2 = pm.acquire(name="limited")

        # Try to acquire 3rd (should fail)
        with pytest.raises(RuntimeError, match="Concurrency limit reached"):
            pm.acquire(name="limited")

        # Release one and try again (should succeed)
        pm.release(ep1)
        ep3 = pm.acquire(name="limited")
        assert ep3 is not None

    def test_release_tracking(self):
        """Test proxy release tracking."""
        config = ProviderConfig(
            name="test-release",
            type="static_list",
            options={"entries": "1.2.3.4:8080"},
        )

        pm = ProxyManager([config])
        ep = pm.acquire(name="test-release")

        # Release should not raise
        pm.release(ep, reason="test complete")
        assert True  # If we got here, release worked

    def test_get_stats(self):
        """Test statistics retrieval."""
        configs = [
            ProviderConfig(
                name="provider1",
                type="static_list",
                price_per_gb=5.0,
                concurrency_limit=10,
                options={"entries": "1.2.3.4:8080"},
            ),
        ]

        pm = ProxyManager(configs)
        stats = pm.get_stats()

        assert "providers" in stats
        assert "provider1" in stats["providers"]
        assert stats["providers"]["provider1"]["price_per_gb"] == 5.0
        assert stats["providers"]["provider1"]["concurrency_limit"] == 10


class TestProxyMeter:
    """Test ProxyMeter usage tracking."""

    def test_meter_initialization(self):
        """Test meter initialization."""
        meter = ProxyMeter()
        assert meter is not None
        assert len(meter._metrics) == 0

    def test_record_acquire(self):
        """Test recording proxy acquisition."""
        meter = ProxyMeter()
        endpoint = ProxyEndpoint(
            scheme="http",
            host="1.2.3.4",
            port=8080,
            provider="test-provider",
            proxy_type=ProxyType.DATACENTER,
            region="US",
        )

        meter.record_acquire(endpoint)
        metrics = meter.get_metrics()

        assert len(metrics) == 1
        key = "test-provider:1.2.3.4:8080"
        assert key in metrics
        assert metrics[key].provider == "test-provider"

    def test_record_request(self):
        """Test recording proxy requests."""
        meter = ProxyMeter()
        endpoint = ProxyEndpoint(
            scheme="http",
            host="1.2.3.4",
            port=8080,
            provider="test-provider",
        )

        meter.record_request(endpoint, bytes_sent=1024, bytes_received=2048, success=True)
        meter.record_request(endpoint, bytes_sent=512, bytes_received=1024, success=True)

        metrics = meter.get_metrics()
        key = "test-provider:1.2.3.4:8080"

        assert metrics[key].requests_count == 2
        assert metrics[key].bytes_sent == 1536
        assert metrics[key].bytes_received == 3072
        assert metrics[key].errors_count == 0

    def test_record_errors(self):
        """Test recording failed requests."""
        meter = ProxyMeter()
        endpoint = ProxyEndpoint(
            scheme="http",
            host="1.2.3.4",
            port=8080,
            provider="test-provider",
        )

        meter.record_request(endpoint, success=True)
        meter.record_request(endpoint, success=False)
        meter.record_request(endpoint, success=False)

        metrics = meter.get_metrics()
        key = "test-provider:1.2.3.4:8080"

        assert metrics[key].requests_count == 3
        assert metrics[key].errors_count == 2
        assert metrics[key].success_rate == pytest.approx(33.33, rel=0.1)

    def test_cost_estimation(self):
        """Test cost estimation."""
        meter = ProxyMeter()
        meter.register_provider_price("test-provider", 5.0)  # $5 per GB

        endpoint = ProxyEndpoint(
            scheme="http",
            host="1.2.3.4",
            port=8080,
            provider="test-provider",
        )

        # Send 1GB of data
        one_gb = 1024 * 1024 * 1024
        meter.record_request(endpoint, bytes_sent=one_gb // 2, bytes_received=one_gb // 2)

        metrics = meter.get_metrics()
        key = "test-provider:1.2.3.4:8080"

        assert metrics[key].total_gb == pytest.approx(1.0, rel=0.01)
        assert metrics[key].cost_estimate == pytest.approx(5.0, rel=0.01)

    def test_get_summary(self):
        """Test getting aggregated summary."""
        meter = ProxyMeter()

        ep1 = ProxyEndpoint(
            scheme="http", host="1.1.1.1", port=8080, provider="provider1"
        )
        ep2 = ProxyEndpoint(
            scheme="http", host="2.2.2.2", port=8080, provider="provider2"
        )

        meter.record_request(ep1, bytes_sent=1024, bytes_received=2048)
        meter.record_request(ep2, bytes_sent=512, bytes_received=1024)

        summary = meter.get_summary()

        assert summary["total_endpoints"] == 2
        assert summary["total_requests"] == 2
        assert "by_provider" in summary
        assert "provider1" in summary["by_provider"]
        assert "provider2" in summary["by_provider"]


class TestIntegration:
    """Integration tests for complete proxy workflow."""

    def test_full_workflow_with_metering(self):
        """Test complete workflow: acquire, use, release with metering."""
        config = ProviderConfig(
            name="test-provider",
            type="static_list",
            price_per_gb=10.0,
            options={
                "entries": "1.2.3.4:8080",
                "proxy_type": "datacenter",
            },
        )

        pm = ProxyManager([config], enable_metering=True)

        # Acquire
        ep = pm.acquire(name="test-provider", purpose="testing")
        assert ep.proxy_type == ProxyType.DATACENTER

        # Simulate usage
        meter = pm.get_meter()
        meter.record_request(ep, bytes_sent=1024, bytes_received=2048, success=True)

        # Release
        pm.release(ep, reason="test complete")

        # Check stats
        stats = pm.get_stats()
        assert "usage_summary" in stats
        assert stats["usage_summary"]["total_requests"] == 1

    def test_multiple_providers_with_failover(self):
        """Test using multiple providers."""
        configs = [
            ProviderConfig(
                name="primary",
                type="static_list",
                price_per_gb=1.0,
                options={"entries": "1.1.1.1:8080"},
            ),
            ProviderConfig(
                name="backup",
                type="static_list",
                price_per_gb=2.0,
                options={"entries": "2.2.2.2:8080"},
            ),
        ]

        pm = ProxyManager(configs)

        # Should get primary (cheaper)
        ep1 = pm.acquire()
        assert ep1.provider == "primary"

        # Can still get specific provider
        ep2 = pm.acquire(name="backup")
        assert ep2.provider == "backup"
