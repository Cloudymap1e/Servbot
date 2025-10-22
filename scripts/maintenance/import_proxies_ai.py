#!/usr/bin/env python
from __future__ import annotations

"""
AI-assisted batch proxy importer.

Usage:
  py -3 scripts/maintenance/import_proxies_ai.py --file path/to/proxies.txt --provider mybatch --limit 100
  py -3 scripts/maintenance/import_proxies_ai.py --string "us.mooproxy.net:55688:specu1:Xxx_country-US_session-ABC" --provider mooproxy

- Reads proxy lines from --file or a single --string
- Uses simple parsing + AI hints to normalize to host:port:username:password
- Imports into data/proxies.db (deduped)

Requires Cerebras and/or Groq keys configured for best parsing, but works without.
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Optional

from servbot.proxy.batch_import import ProxyBatchImporter
from servbot.proxy.database import ProxyDatabase
from servbot.proxy.models import ProxyEndpoint
from servbot.parsers.ai_parser import is_ai_available as cerebras_available
from servbot.ai.groq import is_groq_available


def _read_lines(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith('#')]


def _ai_enhance_line(line: str) -> str:
    # Heuristic cleanup first
    s = line.strip()
    s = s.replace(" ", "")
    # If looks like JSON, try to extract fields
    if s.startswith('{') and s.endswith('}'):
        try:
            data = json.loads(s)
            host = data.get('host') or data.get('ip') or ''
            port = data.get('port') or ''
            user = data.get('username') or data.get('user') or ''
            pwd = data.get('password') or data.get('pass') or ''
            if host and port:
                if user and pwd:
                    return f"{host}:{port}:{user}:{pwd}"
                return f"{host}:{port}"
        except Exception:
            pass
    # If no AI, return as-is
    if not (cerebras_available() or is_groq_available()):
        return s
    # Use Groq (preferred for short prompts)
    try:
        if is_groq_available():
            from servbot.ai.groq import _client as groq_client
            client = groq_client()
            if client:
                prompt = f"""
Normalize the following proxy credential into one of these formats:
- host:port
- host:port:username:password
- username:password@host:port
Input: {s}
Return ONLY the normalized string, no commentary.
"""
                resp = client.responses.create(
                    input=prompt,
                    model="openai/gpt-oss-20b",
                    max_output_tokens=80,
                    temperature=0.0,
                )
                out = (resp.output_text or '').strip()
                # Extract first line
                out = out.splitlines()[0].strip()
                # basic sanity
                if ':' in out:
                    return out
    except Exception:
        pass
    # Fallback: return original cleaned
    return s


def import_proxies(lines: List[str], provider: str, limit: Optional[int] = None) -> int:
    cleaned = []
    for ln in lines[: limit or len(lines)]:
        try:
            cleaned.append(_ai_enhance_line(ln))
        except Exception:
            cleaned.append(ln.strip())
    endpoints = ProxyBatchImporter.import_from_list(cleaned, provider_name=provider)
    if not endpoints:
        print("No endpoints parsed.")
        return 0
    db = ProxyDatabase("data/proxies.db")
    added = 0
    try:
        for ep in endpoints:
            try:
                db.add_proxy(ep)
                added += 1
            except Exception:
                continue
    finally:
        db.close()
    print(f"Imported {added}/{len(endpoints)} endpoints into DB under provider '{provider}'.")
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', type=str, help='Path to proxies file')
    ap.add_argument('--string', type=str, help='Single proxy string to import')
    ap.add_argument('--provider', type=str, default='ai-imported')
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    lines: List[str] = []
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"File not found: {p}")
            return 1
        lines = _read_lines(p)
    elif args.string:
        lines = [args.string]
    else:
        print('Provide --file or --string')
        return 1

    import_proxies(lines, provider=args.provider, limit=args.limit)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
