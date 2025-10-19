from __future__ import annotations

import json
from typing import Optional, Dict, Any

from ..config import load_groq_key

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def is_groq_available() -> bool:
    return OpenAI is not None and load_groq_key() is not None


def _client() -> Optional[OpenAI]:  # type: ignore
    if not is_groq_available():
        return None
    key = load_groq_key()
    try:
        client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        return client
    except Exception:
        return None


def extract_with_groq(email_subject: str, email_body: str, from_addr: str) -> Optional[Dict[str, Any]]:
    """Use Groq to extract service, 6-digit code, and link from email text.
    Returns a dict with keys: service, code, link. Prefers 6-digit numeric code.
    """
    client = _client()
    if not client:
        return None
    prompt = f"""
You are an expert at extracting verification information from emails.
Return ONLY JSON with keys: service, code, link.
Rules:
- code must be a 6-digit numeric string if present.
- link should be a likely verification/magic URL if present.
- service is a short brand name.
FROM: {from_addr}
SUBJECT: {email_subject}
BODY:
{email_body[:4000]}
JSON only:
"""
    try:
        resp = client.responses.create(
            input=prompt,
            model="openai/gpt-oss-20b",
            max_output_tokens=300,
            temperature=0.0,
        )
        text = resp.output_text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(text[start : end + 1])
            code = data.get("code")
            link = data.get("link")
            svc = data.get("service")
            def _ok6(s: Optional[str]) -> Optional[str]:
                if isinstance(s, str) and s.strip().isdigit() and len(s.strip()) == 6:
                    return s.strip()
                return None
            return {"service": svc, "code": _ok6(code), "link": link}
        return None
    except Exception:
        return None
