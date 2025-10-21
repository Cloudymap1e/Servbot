import argparse
import logging
import time
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote, urlencode

# Ensure repository root is on sys.path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from servbot.proxy.database import ProxyDatabase

DEFAULT_TEST_URL = "http://httpbin.org/status/200"  # minimal, no TLS, empty body
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_MAX_WORKERS = 2  # low concurrency to minimize bandwidth spikes


def build_proxy_uri(ep) -> str:
    scheme = getattr(ep, "scheme", None) or "http"
    auth = ""
    if getattr(ep, "username", None):
        user = quote(ep.username or "", safe="")
        pwd = quote(getattr(ep, "password", "") or "", safe="")
        auth = f"{user}:{pwd}@"
    return f"{scheme}://{auth}{ep.host}:{ep.port}"


def _extract_ip_from_response(resp: requests.Response) -> Optional[str]:
    try:
        data = resp.json()
        # httpbin.org/ip => {'origin': 'x.x.x.x'}
        if isinstance(data, dict):
            if 'origin' in data and data['origin']:
                return str(data['origin'])
            if 'ip' in data and data['ip']:
                return str(data['ip'])
            # httpbin.org/get => {'origin': 'x.x.x.x', 'headers': {...}}
            if 'headers' in data and isinstance(data['headers'], dict):
                # Some deployments include X-Real-Ip
                h = {k.lower(): v for k, v in data['headers'].items()}
                if 'x-real-ip' in h:
                    return str(h['x-real-ip'])
        
    except Exception:
        pass
    return None


def test_one(ep, test_url: str, timeout: int) -> Dict:
    # Always provide both schemes so HTTPS targets route via proxy too
    uri = build_proxy_uri(ep)
    proxies = {"http": uri, "https": uri}
    headers = {"Connection": "close"}  # avoid keep-alive to reduce lingering connections
    start = time.perf_counter()
    status_code = None
    try:
        r = requests.get(
            test_url,
            timeout=timeout,
            proxies=proxies,
            allow_redirects=False,  # avoid extra round-trip
            headers=headers,
        )
        status_code = r.status_code
        success = status_code == 200
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        resp_ip = _extract_ip_from_response(r)
        # Try to capture proxy-forwarded headers when using /get or /headers
        forwarded_for = None
        via = None
        real_ip_hdr = None
        try:
            data = r.json()
            if isinstance(data, dict) and 'headers' in data and isinstance(data['headers'], dict):
                h = {k.lower(): v for k, v in data['headers'].items()}
                forwarded_for = h.get('x-forwarded-for')
                via = h.get('via')
                real_ip_hdr = h.get('x-real-ip')
        except Exception:
            pass
        return {
            "endpoint": ep,
            "success": success,
            "response_time_ms": elapsed_ms,
            "status_code": status_code,
            "error": None if success else f"HTTP {status_code}",
            "test_url": test_url,
            "response_ip": resp_ip,
            "x_forwarded_for": forwarded_for,
            "via": via,
            "x_real_ip": real_ip_hdr,
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {
            "endpoint": ep,
            "success": False,
            "response_time_ms": elapsed_ms,
            "status_code": status_code,
            "error": str(e),
            "test_url": test_url,
            "response_ip": None,
        }


def find_db_id(db: ProxyDatabase, ep) -> Optional[int]:
    # Primary: use db_id carried in endpoint.metadata (as required)
    try:
        md = getattr(ep, "metadata", None)
        if isinstance(md, dict):
            db_id = md.get("db_id")
            if db_id:
                return db_id
    except Exception:
        pass

    # Fallback: query by unique key (host, port, username, session)
    try:
        conn = db._get_connection()  # fallback use; safe within this repo's context
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM proxies WHERE host=? AND port=? AND username IS ? AND session IS ?",
            (ep.host, ep.port, getattr(ep, "username", None), getattr(ep, "session", None)),
        )
        row = cur.fetchone()
        return row["id"] if row else None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Minimal-bandwidth proxy tester")
    parser.add_argument(
        "--save-working",
        action="store_true",
        help="Save working proxies to config/working_proxies_mintraffic.txt",
    )
    parser.add_argument(
        "--test-url",
        default=DEFAULT_TEST_URL,
        help=f"URL to test against (default: {DEFAULT_TEST_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Max parallel workers (default: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Also report your current egress IP without upstream proxy (affected by Proxifier rules)",
    )
    parser.add_argument(
        "--label",
        default="default",
        help="A label to tag this run (e.g., proxifier-direct or proxifier-local)",
    )
    parser.add_argument(
        "--save-json",
        default=None,
        help="Optional path to write detailed JSON results (defaults to data/proxy_ipcheck_<label>.json)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("proxy-test-min-traffic")

    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_all_proxies(active_only=True)
        total = len(endpoints)
        if total == 0:
            print("No active proxies found in data/proxies.db")
            return

        print()
        print("=" * 80)
        print("MINIMAL-TRAFFIC PROXY TEST")
        print("=" * 80)
        print(f"\nActive proxies loaded: {total}")
        print(f"Target: {args.test_url}")
        print(f"Timeout: {args.timeout}s | Concurrency: {args.max_workers}")
        print(f"Label: {args.label}")
        print()

        # Baseline egress IP (no upstream proxy; may still be proxified by your local rules)
        baseline_ip: Optional[str] = None
        if args.baseline:
            try:
                r0 = requests.get(args.test_url, timeout=args.timeout, allow_redirects=False, headers={"Connection": "close"})
                baseline_ip = _extract_ip_from_response(r0)
                print(f"Baseline egress IP: {baseline_ip or 'N/A'}")
            except Exception as e:
                print(f"Baseline check failed: {e}")

        done = 0
        success_count = 0
        results: List[Dict] = []
        working_lines: List[str] = []

        def show_progress():
            print(f"Tested: {done}/{total} ({(done/total*100):.0f}%)", end="\r", flush=True)

        with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            future_map = {ex.submit(test_one, ep, args.test_url, args.timeout): ep for ep in endpoints}
            for fut in as_completed(future_map):
                res = fut.result()
                results.append(res)
                done += 1
                if res["success"]:
                    success_count += 1
                    ep = res["endpoint"]
                    working_lines.append(build_proxy_uri(ep))
                show_progress()

        print()  # newline after progress

        # Record results to DB (tag run via label in test_url)
        def _with_label(url: str, label: str) -> str:
            if not label:
                return url
            sep = '&' if ('?' in url) else '?'
            return f"{url}{sep}{urlencode({'label': label})}"

        for res in results:
            ep = res["endpoint"]
            proxy_id = find_db_id(db, ep)
            if proxy_id:
                db.record_test_result(
                    proxy_id=proxy_id,
                    success=res["success"],
                    response_time_ms=res["response_time_ms"],
                    status_code=res["status_code"],
                    error_message=res["error"],
                    test_url=_with_label(res["test_url"], args.label),
                    response_ip=res["response_ip"],
                )
            else:
                log.warning(f"Could not determine db_id for {ep.host}:{ep.port}")

        failed_count = total - success_count
        print(f"Summary: tested={total}, success={success_count}, failed={failed_count}")

        # Optionally save working proxies to file
        if args.save_working and working_lines:
            out_path = Path("config/working_proxies_mintraffic.txt")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("\n".join(working_lines) + "\n", encoding="utf-8")
            print(f"Saved {len(working_lines)} working proxies to {out_path.as_posix()}")

        # Save JSON results if requested (or default path with label)
        out_json = args.save_json or str(Path("data") / f"proxy_ipcheck_{args.label}.json")
        try:
            Path(out_json).parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "label": args.label,
                "test_url": args.test_url,
                "timeout": args.timeout,
                "max_workers": args.max_workers,
                "baseline_ip": baseline_ip,
                "summary": {"tested": total, "success": success_count, "failed": failed_count},
                "results": [
                    {
                        "host": f"{r['endpoint'].host}:{r['endpoint'].port}",
                        "provider": getattr(r['endpoint'], 'provider', None),
                        "session": getattr(r['endpoint'], 'session', None),
                        "success": r["success"],
                        "status_code": r["status_code"],
                        "response_time_ms": r["response_time_ms"],
                        "response_ip": r["response_ip"],
                        "x_forwarded_for": r.get("x_forwarded_for"),
                        "via": r.get("via"),
                        "x_real_ip": r.get("x_real_ip"),
                        "error": r["error"],
                    }
                    for r in results
                ],
            }
            Path(out_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved detailed JSON: {out_json}")
        except Exception as e:
            print(f"Failed to save JSON results: {e}")

        print()

    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()