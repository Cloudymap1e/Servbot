"""Verification code and link parsing.

Extracts OTP codes and verification links from email content using
regex patterns with optional AI fallback.
"""

import re
from typing import List, Optional

# URL extraction regex
_LINK_REGEX = re.compile(r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE)

# OTP/verification code regex patterns (ordered by specificity)
_CODE_PATTERNS = [
    # Vendor-specific formats
    re.compile(r"\bG-?(\d{6})\b", re.IGNORECASE),  # Google: G-123456
    re.compile(r"\bFB-?(\d{6})\b", re.IGNORECASE),  # Facebook: FB-123456
    
    # Generic labeled codes
    re.compile(
        r"\b(?:code|otp|pass(?:code|word)?|verification|auth(?:entication)?|security)[:\s-]*((?!code\b)[A-Z0-9]{4,10})\b",
        re.IGNORECASE,
    ),
    
    # Context-based numeric codes
    re.compile(
        r"(?:verification|security|otp|code)[^\n]{0,40}?\b(\d{6,8})\b",
        re.IGNORECASE,
    ),
    
    # Standalone 6-digit codes (avoid years, amounts)
    re.compile(r"(?<![$€£#])\b(\d{6})\b(?!\s*(?:USD|EUR|CAD|GBP|\$))"),
]


def parse_verification_codes(
    text: str,
    email_subject: str = "",
    email_body: str = "",
    from_addr: str = "",
    use_ai_fallback: bool = True,
) -> List[str]:
    """Extracts verification/OTP codes from text.
    
    Uses regex patterns with optional AI fallback for complex cases.
    
    Args:
        text: Text to extract codes from
        email_subject: Email subject (for AI fallback)
        email_body: Full email body (for AI fallback)
        from_addr: Sender address (for AI fallback)
        use_ai_fallback: Whether to use AI if regex fails
        
    Returns:
        List of unique codes found, preserving order
    """
    if not text:
        return []
    
    found: List[str] = []
    
    # Try regex patterns
    for pattern in _CODE_PATTERNS:
        for match in pattern.findall(text):
            code = match if isinstance(match, str) else match[0]
            
            # Normalize vendor prefixes (G-123456 -> 123456)
            if re.match(r"^[A-Z]-?\d{6}$", code, re.IGNORECASE):
                code = re.sub(r"^[A-Z]-?", "", code)
            
            found.append(code)
    
    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for code in found:
        if code not in seen:
            seen.add(code)
            unique.append(code)
    
    # AI fallback and Groq enhancement
    if use_ai_fallback and email_subject and from_addr:
        ai_code: Optional[str] = None
        try:
            from .ai_parser import extract_with_ai
            ai_result = extract_with_ai(email_subject, email_body or text, from_addr)
            if ai_result and isinstance(ai_result.get('code'), str):
                c = ai_result['code'].strip()
                if c.isdigit() and 4 <= len(c) <= 8:
                    ai_code = c
        except Exception:
            ai_code = None
        # Try Groq if no good code yet or to override with 6-digit
        try:
            from ..ai.groq import extract_with_groq
            g = extract_with_groq(email_subject, email_body or text, from_addr)
            if g and g.get('code'):
                ai_code = g['code']  # enforce 6-digit numeric per groq client
        except Exception:
            pass
        if ai_code:
            # Prefer AI if our first candidate isn't 6-digit
            if not unique or not (unique[0].isdigit() and len(unique[0]) == 6):
                unique.insert(0, ai_code)
            elif ai_code not in unique:
                unique.append(ai_code)
    
    return unique


def parse_verification_links(text: str, email_subject: str = "") -> List[str]:
    """Extracts verification links from text.
    
    Filters URLs to identify likely verification/magic links while
    excluding unsubscribe and settings links.
    
    Args:
        text: Text to extract links from
        email_subject: Email subject (for context)
        
    Returns:
        List of unique verification links
    """
    if not text:
        return []
    
    candidates = _LINK_REGEX.findall(text)
    if not candidates:
        return []
    
    subject_lower = (email_subject or "").lower()
    
    # Keywords indicating verification links
    include_keywords = [
        "verify", "verification", "confirm", "activate", "activation",
        "validate", "validation", "magic", "login", "signin", "sign-in",
        "confirm-email", "email-confirm", "account/confirm", "account/verify",
    ]
    
    # Keywords indicating non-verification links
    exclude_keywords = [
        "unsubscribe", "preferences", "privacy", "terms", "help", "support",
        "facebook.com/l.php",  # Tracking redirectors
    ]
    
    def _is_verification_link(url: str) -> bool:
        """Checks if URL is likely a verification link."""
        url_lower = url.lower()
        
        # Exclude unwanted links
        if any(kw in url_lower for kw in exclude_keywords):
            return False
        
        # Include if URL contains verification keywords
        if any(kw in url_lower for kw in include_keywords):
            return True
        
        # Include if subject hints at verification
        if any(kw in subject_lower for kw in ["verify", "verification", "confirm", "activate"]):
            return True
        
        return False
    
    # Filter and deduplicate
    seen = set()
    filtered: List[str] = []
    for url in candidates:
        if url not in seen and _is_verification_link(url):
            seen.add(url)
            filtered.append(url)
    
    return filtered


def visit_verification_link(url: str, timeout: int = 20) -> bool:
    """Visits a verification link to complete verification.
    
    Args:
        url: Verification URL to visit
        timeout: Request timeout in seconds
        
    Returns:
        True if request succeeds (2xx/3xx), False otherwise
    """
    try:
        # Try requests library first
        try:
            import requests  # type: ignore
            headers = {"User-Agent": "Mozilla/5.0 (Servbot)"}
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            return 200 <= response.status_code < 400
        except ImportError:
            pass
        
        # Fallback to urllib
        import urllib.request
        headers = {"User-Agent": "Mozilla/5.0 (Servbot)"}
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # type: ignore
            status = getattr(resp, "status", 200)
            return 200 <= status < 400
    
    except Exception:
        return False

