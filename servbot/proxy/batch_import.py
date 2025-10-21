"""Batch proxy import and auto-detection utilities."""
from __future__ import annotations

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from .models import ProxyEndpoint, ProviderConfig, ProxyType, IPVersion, RotationType


logger = logging.getLogger(__name__)


@dataclass
class ProxyDetectionResult:
    """Result of auto-detecting proxy information."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    provider: Optional[str] = None
    session: Optional[str] = None
    region: Optional[str] = None
    proxy_type: Optional[ProxyType] = None
    ip_version: Optional[IPVersion] = None
    rotation_type: Optional[RotationType] = None
    scheme: str = "http"
    confidence: float = 1.0  # Detection confidence 0-1


class ProxyDetector:
    """Auto-detect proxy provider, type, and configuration from proxy strings."""

    # Known provider patterns
    PROVIDER_PATTERNS = {
        'mooproxy': [
            r'mooproxy\.net',
            r'_session-[A-Za-z0-9]+',
        ],
        'brightdata': [
            r'lum-superproxy\.io',
            r'zproxy\.lum',
        ],
        'smartproxy': [
            r'smartproxy\.com',
            r'gate\.smartproxy',
        ],
        'oxylabs': [
            r'oxylabs\.io',
            r'pr\.oxylabs',
        ],
        'iproyal': [
            r'iproyal\.com',
        ],
    }

    @classmethod
    def detect_provider(cls, host: str, username: str = None, password: str = None) -> Optional[str]:
        """Detect provider from host/credentials."""
        full_text = f"{host} {username or ''} {password or ''}"

        for provider, patterns in cls.PROVIDER_PATTERNS.items():
            if any(re.search(pattern, full_text, re.IGNORECASE) for pattern in patterns):
                logger.debug(f"Detected provider: {provider} from {host}")
                return provider

        return None

    @classmethod
    def detect_proxy_type(cls, host: str, username: str = None, password: str = None) -> ProxyType:
        """Detect proxy type based on patterns."""
        # Check for residential indicators
        residential_indicators = ['residential', 'resi', 'home', 'dsl', 'cable']
        if any(ind in host.lower() or (password and ind in password.lower()) for ind in residential_indicators):
            return ProxyType.RESIDENTIAL

        # Check for ISP indicators
        isp_indicators = ['isp', 'static-residential']
        if any(ind in host.lower() or (password and ind in password.lower()) for ind in isp_indicators):
            return ProxyType.ISP

        # Check for mobile indicators
        mobile_indicators = ['mobile', '4g', '5g', 'cellular']
        if any(ind in host.lower() or (password and ind in password.lower()) for ind in mobile_indicators):
            return ProxyType.MOBILE

        # Default to datacenter
        return ProxyType.DATACENTER

    @classmethod
    def detect_ip_version(cls, host: str) -> IPVersion:
        """Detect IP version from host."""
        # Check for IPv6 indicators
        if ':' in host.split('.')[0] or 'ipv6' in host.lower() or 'v6' in host.lower():
            return IPVersion.IPV6
        return IPVersion.IPV4

    @classmethod
    def detect_rotation_type(cls, password: str = None, provider: str = None) -> RotationType:
        """Detect rotation type."""
        # Session-based proxies are typically sticky
        if password and '_session-' in password:
            return RotationType.STICKY

        # MooProxy and similar with sessions are sticky
        if provider in ['mooproxy', 'brightdata']:
            return RotationType.STICKY

        return RotationType.STICKY  # Conservative default

    @classmethod
    def extract_session_id(cls, password: str) -> Optional[str]:
        """Extract session ID from password."""
        if not password:
            return None

        # MooProxy format: password_country-XX_session-ID
        match = re.search(r'_session-([A-Za-z0-9_-]+)', password)
        if match:
            return match.group(1)

        return None

    @classmethod
    def extract_region(cls, password: str) -> Optional[str]:
        """Extract region/country code from password."""
        if not password:
            return None

        # MooProxy format: password_country-XX
        match = re.search(r'_country-([A-Z]{2})', password)
        if match:
            return match.group(1)

        return None

    @classmethod
    def parse_proxy_string(cls, proxy_string: str) -> ProxyDetectionResult:
        """Parse proxy string and auto-detect all parameters.

        Supported formats:
        - host:port
        - username:password@host:port
        - host:port:username:password (MooProxy format)
        - scheme://username:password@host:port

        Args:
            proxy_string: Proxy string to parse

        Returns:
            ProxyDetectionResult with detected values
        """
        proxy_string = proxy_string.strip()

        # Default values
        scheme = "http"
        username = None
        password = None
        host = None
        port = None

        # Extract scheme if present
        if "://" in proxy_string:
            scheme, rest = proxy_string.split("://", 1)
            proxy_string = rest

        # Format 1: host:port:username:password (MooProxy/similar)
        if proxy_string.count(':') >= 3:
            parts = proxy_string.split(':', 3)
            if len(parts) == 4:
                host = parts[0]
                try:
                    port = int(parts[1])
                    username = parts[2]
                    password = parts[3]
                    logger.debug(f"Parsed as format host:port:user:pass - {host}:{port}")
                except ValueError:
                    # Try other formats
                    pass

        # Format 2: username:password@host:port
        if host is None and '@' in proxy_string:
            creds, hostport = proxy_string.split('@', 1)
            if ':' in creds:
                username, password = creds.split(':', 1)
            else:
                username = creds

            if ':' in hostport:
                host, port_str = hostport.rsplit(':', 1)
                try:
                    port = int(port_str)
                    logger.debug(f"Parsed as format user:pass@host:port - {host}:{port}")
                except ValueError:
                    logger.warning(f"Invalid port in proxy string: {proxy_string}")
                    return None

        # Format 3: host:port
        if host is None and ':' in proxy_string:
            host, port_str = proxy_string.rsplit(':', 1)
            try:
                port = int(port_str)
                logger.debug(f"Parsed as format host:port - {host}:{port}")
            except ValueError:
                logger.warning(f"Invalid port in proxy string: {proxy_string}")
                return None

        if not host or not port:
            logger.error(f"Could not parse proxy string: {proxy_string}")
            return None

        # Auto-detect provider
        provider = cls.detect_provider(host, username, password)

        # Auto-detect other attributes
        proxy_type = cls.detect_proxy_type(host, username, password)
        ip_version = cls.detect_ip_version(host)
        rotation_type = cls.detect_rotation_type(password, provider)
        session = cls.extract_session_id(password)
        region = cls.extract_region(password)

        result = ProxyDetectionResult(
            host=host,
            port=port,
            username=username,
            password=password,
            provider=provider,
            session=session,
            region=region,
            proxy_type=proxy_type,
            ip_version=ip_version,
            rotation_type=rotation_type,
            scheme=scheme,
            confidence=1.0 if provider else 0.7,  # Lower confidence if provider unknown
        )

        logger.info(
            f"Detected proxy: host={host}:{port} provider={provider} type={proxy_type.value} "
            f"region={region} session={session}"
        )

        return result


class ProxyBatchImporter:
    """Import and manage batches of proxies."""

    @staticmethod
    def import_from_list(
        proxy_strings: List[str],
        provider_name: str = "auto-imported",
        default_proxy_type: Optional[ProxyType] = None,
    ) -> List[ProxyEndpoint]:
        """Import multiple proxies from string list with auto-detection.

        Args:
            proxy_strings: List of proxy strings in various formats
            provider_name: Name for the provider (default: "auto-imported")
            default_proxy_type: Override proxy type detection

        Returns:
            List of ProxyEndpoint objects
        """
        endpoints = []
        detector = ProxyDetector()

        logger.info(f"Starting batch import of {len(proxy_strings)} proxies")

        for i, proxy_str in enumerate(proxy_strings, 1):
            try:
                result = detector.parse_proxy_string(proxy_str)
                if not result:
                    logger.warning(f"Skipped invalid proxy {i}/{len(proxy_strings)}: {proxy_str[:50]}")
                    continue

                endpoint = ProxyEndpoint(
                    scheme=result.scheme,
                    host=result.host,
                    port=result.port,
                    username=result.username,
                    password=result.password,
                    provider=result.provider or provider_name,
                    session=result.session,
                    proxy_type=default_proxy_type or result.proxy_type,
                    ip_version=result.ip_version,
                    rotation_type=result.rotation_type,
                    region=result.region,
                    metadata={
                        'imported': True,
                        'detection_confidence': result.confidence,
                        'batch_index': i,
                    }
                )

                endpoints.append(endpoint)
                logger.debug(f"Imported proxy {i}/{len(proxy_strings)}: {result.host}:{result.port}")

            except Exception as e:
                logger.error(f"Error importing proxy {i}/{len(proxy_strings)}: {e}", exc_info=True)
                continue

        logger.info(f"Successfully imported {len(endpoints)}/{len(proxy_strings)} proxies")
        return endpoints

    @staticmethod
    def import_from_file(
        file_path: str,
        provider_name: str = "auto-imported",
        default_proxy_type: Optional[ProxyType] = None,
    ) -> List[ProxyEndpoint]:
        """Import proxies from a text file (one per line).

        Args:
            file_path: Path to file containing proxy strings
            provider_name: Name for the provider
            default_proxy_type: Override proxy type detection

        Returns:
            List of ProxyEndpoint objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                proxy_strings = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            logger.info(f"Read {len(proxy_strings)} proxies from {file_path}")
            return ProxyBatchImporter.import_from_list(
                proxy_strings,
                provider_name=provider_name,
                default_proxy_type=default_proxy_type,
            )
        except Exception as e:
            logger.error(f"Error reading proxy file {file_path}: {e}", exc_info=True)
            return []

    @staticmethod
    def create_provider_config(
        endpoints: List[ProxyEndpoint],
        name: str,
        price_per_gb: float = 5.0,
        concurrency_limit: Optional[int] = None,
    ) -> ProviderConfig:
        """Create a ProviderConfig from imported endpoints.

        Args:
            endpoints: List of imported endpoints
            name: Provider name
            price_per_gb: Price per GB (default: 5.0)
            concurrency_limit: Max concurrent connections

        Returns:
            ProviderConfig ready for ProxyManager
        """
        # Convert endpoints to entries string
        entries = []
        for ep in endpoints:
            if ep.username and ep.password:
                entry = f"{ep.host}:{ep.port}:{ep.username}:{ep.password}"
            elif ep.username:
                entry = f"{ep.username}@{ep.host}:{ep.port}"
            else:
                entry = f"{ep.host}:{ep.port}"
            entries.append(entry)

        # Use first endpoint to determine proxy type
        proxy_type = endpoints[0].proxy_type.value if endpoints else "residential"
        ip_version = endpoints[0].ip_version.value if endpoints else "ipv4"

        config = ProviderConfig(
            name=name,
            type="static_list" if not any('mooproxy' in str(ep.host) for ep in endpoints) else "mooproxy",
            price_per_gb=price_per_gb,
            concurrency_limit=concurrency_limit,
            options={
                "entries": "\n".join(entries),
                "proxy_type": proxy_type,
                "ip_version": ip_version,
            }
        )

        logger.info(f"Created provider config: {name} with {len(entries)} endpoints")
        return config
