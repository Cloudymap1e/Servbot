"""Proxy testing utilities."""
from __future__ import annotations

import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import ProxyEndpoint


logger = logging.getLogger(__name__)


@dataclass
class ProxyTestResult:
    """Result of testing a single proxy."""
    endpoint: ProxyEndpoint
    success: bool
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    test_url: str = ""
    test_timestamp: datetime = field(default_factory=datetime.now)
    response_ip: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'host': f"{self.endpoint.host}:{self.endpoint.port}",
            'provider': self.endpoint.provider,
            'session': self.endpoint.session,
            'region': self.endpoint.region,
            'success': self.success,
            'response_time_ms': self.response_time_ms,
            'status_code': self.status_code,
            'error': self.error,
            'test_url': self.test_url,
            'response_ip': self.response_ip,
        }


class ProxyTester:
    """Test proxy endpoints to verify they're working."""

    # Default test URLs
    TEST_URLS = {
        'simple': 'http://httpbin.org/ip',
        'get': 'http://httpbin.org/get',
        'headers': 'http://httpbin.org/headers',
        'delay': 'http://httpbin.org/delay/1',
    }

    @staticmethod
    def test_single_proxy(
        endpoint: ProxyEndpoint,
        test_url: str = None,
        timeout: int = 10,
    ) -> ProxyTestResult:
        """Test a single proxy endpoint.

        Args:
            endpoint: Proxy endpoint to test
            test_url: URL to test against (default: httpbin.org/ip)
            timeout: Request timeout in seconds

        Returns:
            ProxyTestResult with test outcome
        """
        test_url = test_url or ProxyTester.TEST_URLS['simple']

        logger.debug(f"Testing proxy: {endpoint.host}:{endpoint.port} against {test_url}")

        try:
            proxies = endpoint.as_requests_proxies()
            start_time = time.time()

            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={'User-Agent': 'ProxyTester/1.0'}
            )

            response_time_ms = (time.time() - start_time) * 1000

            # Try to extract IP from response
            response_ip = None
            try:
                if 'origin' in response.json():
                    response_ip = response.json()['origin']
            except:
                pass

            result = ProxyTestResult(
                endpoint=endpoint,
                success=response.status_code == 200,
                response_time_ms=round(response_time_ms, 2),
                status_code=response.status_code,
                test_url=test_url,
                response_ip=response_ip,
            )

            if result.success:
                logger.info(
                    f"[OK] Proxy working: {endpoint.host}:{endpoint.port} "
                    f"({response_time_ms:.0f}ms) IP: {response_ip}"
                )
            else:
                logger.warning(
                    f"[FAIL] Proxy returned {response.status_code}: {endpoint.host}:{endpoint.port}"
                )

            return result

        except requests.exceptions.ProxyError as e:
            logger.warning(f"[FAIL] Proxy error: {endpoint.host}:{endpoint.port} - {str(e)[:100]}")
            return ProxyTestResult(
                endpoint=endpoint,
                success=False,
                error=f"ProxyError: {str(e)[:200]}",
                test_url=test_url,
            )

        except requests.exceptions.Timeout:
            logger.warning(f"[FAIL] Proxy timeout: {endpoint.host}:{endpoint.port}")
            return ProxyTestResult(
                endpoint=endpoint,
                success=False,
                error="Timeout",
                test_url=test_url,
            )

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"[FAIL] Connection error: {endpoint.host}:{endpoint.port} - {str(e)[:100]}")
            return ProxyTestResult(
                endpoint=endpoint,
                success=False,
                error=f"ConnectionError: {str(e)[:200]}",
                test_url=test_url,
            )

        except Exception as e:
            logger.error(
                f"[FAIL] Unexpected error testing {endpoint.host}:{endpoint.port}: {e}",
                exc_info=True
            )
            return ProxyTestResult(
                endpoint=endpoint,
                success=False,
                error=f"Error: {str(e)[:200]}",
                test_url=test_url,
            )

    @staticmethod
    def test_batch(
        endpoints: List[ProxyEndpoint],
        test_url: str = None,
        timeout: int = 10,
        max_workers: int = 10,
        progress_callback=None,
    ) -> List[ProxyTestResult]:
        """Test multiple proxies in parallel.

        Args:
            endpoints: List of proxy endpoints to test
            test_url: URL to test against
            timeout: Request timeout in seconds
            max_workers: Max parallel workers
            progress_callback: Optional callback(completed, total) for progress

        Returns:
            List of ProxyTestResult objects
        """
        logger.info(f"Starting batch test of {len(endpoints)} proxies (max_workers={max_workers})")

        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_endpoint = {
                executor.submit(
                    ProxyTester.test_single_proxy,
                    endpoint,
                    test_url,
                    timeout
                ): endpoint
                for endpoint in endpoints
            }

            # Collect results as they complete
            for future in as_completed(future_to_endpoint):
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, len(endpoints))

                except Exception as e:
                    endpoint = future_to_endpoint[future]
                    logger.error(f"Error in test future for {endpoint.host}: {e}")
                    results.append(ProxyTestResult(
                        endpoint=endpoint,
                        success=False,
                        error=f"Future error: {str(e)}",
                        test_url=test_url or '',
                    ))
                    completed += 1

        # Sort by original order
        endpoint_order = {id(ep): i for i, ep in enumerate(endpoints)}
        results.sort(key=lambda r: endpoint_order.get(id(r.endpoint), 999999))

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        avg_time = sum(r.response_time_ms for r in results if r.response_time_ms) / max(successful, 1)

        logger.info(
            f"Batch test complete: {successful}/{len(endpoints)} successful, "
            f"{failed} failed, avg response time: {avg_time:.0f}ms"
        )

        return results

    @staticmethod
    def print_test_summary(results: List[ProxyTestResult]) -> None:
        """Print a formatted summary of test results.

        Args:
            results: List of test results
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print("\n" + "="*80)
        print(f"PROXY TEST SUMMARY - {len(results)} Total")
        print("="*80)

        print(f"\n[OK] Successful: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"[FAIL] Failed: {len(failed)}/{len(results)} ({len(failed)/len(results)*100:.1f}%)")

        if successful:
            avg_time = sum(r.response_time_ms for r in successful) / len(successful)
            min_time = min(r.response_time_ms for r in successful)
            max_time = max(r.response_time_ms for r in successful)
            print(f"\nResponse Times: avg={avg_time:.0f}ms, min={min_time:.0f}ms, max={max_time:.0f}ms")

        # Successful proxies
        if successful:
            print(f"\n{'='*80}")
            print(f"WORKING PROXIES ({len(successful)})")
            print(f"{'='*80}")
            print(f"{'#':<4} {'Host:Port':<35} {'Provider':<15} {'Session':<12} {'Time':<10} {'IP':<20}")
            print("-"*80)

            for i, result in enumerate(successful, 1):
                ep = result.endpoint
                print(
                    f"{i:<4} {ep.host}:{ep.port:<28} "
                    f"{(ep.provider or 'unknown'):<15} "
                    f"{(ep.session or 'N/A')[:12]:<12} "
                    f"{result.response_time_ms:>6.0f}ms   "
                    f"{(result.response_ip or 'N/A')[:20]:<20}"
                )

        # Failed proxies
        if failed:
            print(f"\n{'='*80}")
            print(f"FAILED PROXIES ({len(failed)})")
            print(f"{'='*80}")
            print(f"{'#':<4} {'Host:Port':<35} {'Error':<40}")
            print("-"*80)

            for i, result in enumerate(failed, 1):
                ep = result.endpoint
                error_msg = (result.error or 'Unknown error')[:40]
                print(f"{i:<4} {ep.host}:{ep.port:<28} {error_msg:<40}")

        print("="*80)
