import json
import subprocess
import sys
from pathlib import Path
from typing import List

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servbot.proxy.database import ProxyDatabase


def run_curl(args: List[str]) -> (int, str, str):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def main():
    preproxy = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:12334"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    db = ProxyDatabase("data/proxies.db")
    eps = db.get_all_proxies(active_only=True)[:count]

    # Baseline via local preproxy only
    code, out, err = run_curl([
        "curl.exe","-sS","--max-time","8","--preproxy", preproxy, "https://httpbin.org/ip"
    ])
    baseline = None
    if code == 0:
        try:
            baseline = json.loads(out).get("origin")
        except Exception:
            baseline = None
    print(f"Baseline via preproxy={preproxy}: {baseline or 'N/A'}")

    for ep in eps:
        proxy_url = f"http://{ep.username}:{ep.password}@{ep.host}:{ep.port}"
        # Check IP
        args_ip = [
            "curl.exe","-sS","--max-time","10","--preproxy", preproxy,
            "--proxy", proxy_url, "https://httpbin.org/ip"
        ]
        code_ip, out_ip, err_ip = run_curl(args_ip)
        origin = None
        if code_ip == 0:
            try:
                origin = json.loads(out_ip).get("origin")
            except Exception:
                origin = None
        # Check headers
        args_hdr = [
            "curl.exe","-sS","--max-time","10","--preproxy", preproxy,
            "--proxy", proxy_url, "https://httpbin.org/get"
        ]
        code_h, out_h, err_h = run_curl(args_hdr)
        xff = None
        if code_h == 0:
            try:
                hdr = json.loads(out_h).get("headers", {})
                xff = hdr.get("X-Forwarded-For")
            except Exception:
                xff = None

        status = "OK" if code_ip == 0 and origin else f"ERR({code_ip})"
        print(f"{ep.session:>10} | {status} | origin={origin or 'N/A'} | XFF={xff or 'N/A'} | baseline_match={'YES' if origin and baseline and origin==baseline else 'NO'}")

    db.close()


if __name__ == "__main__":
    main()