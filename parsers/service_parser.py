"""Service identification and normalization.

Identifies services/providers from email metadata and normalizes
service names using aliases and patterns.
"""

from typing import Dict

from .email_parser import domain_from_addr


# Simple domain-to-service mapping for quick lookups
_DOMAIN_MAP: Dict[str, str] = {
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "amazon": "Amazon",
    "paypal": "PayPal",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "stripe": "Stripe",
    "slack": "Slack",
    "discord": "Discord",
    "zoom": "Zoom",
    "dropbox": "Dropbox",
    "box": "Box",
    "okta": "Okta",
    "auth0": "Auth0",
    "cloudflare": "Cloudflare",
}


def identify_service(
    from_addr: str,
    subject: str,
    body: str,
    use_ai_fallback: bool = True,
) -> str:
    """Identifies service/provider from email metadata.
    
    Uses domain matching, keyword detection, and optional AI fallback.
    
    Args:
        from_addr: Sender email address
        subject: Email subject line
        body: Email body text
        use_ai_fallback: Whether to use AI for unknown services
        
    Returns:
        Service name (e.g., "Google", "GitHub") or "Unknown"
    """
    from ..data.services import SERVICES
    
    domain = domain_from_addr(from_addr)
    subject_lower = (subject or "").lower()
    body_lower = (body or "").lower()
    
    # Check against comprehensive service catalog
    for service, hints in SERVICES.items():
        # Check domain indicators
        for d in hints.get("from_domains", []):
            if d and d in domain:
                return service
        
        # Check subject keywords
        for kw in hints.get("subject_keywords", []):
            if kw and kw.lower() in subject_lower:
                return service
        
        # Check body keywords
        for kw in hints.get("body_keywords", []):
            if kw and kw.lower() in body_lower:
                return service
    
    # Try simple domain mapping
    if domain:
        parts = domain.split(".")
        if len(parts) >= 2:
            root = parts[-2]
            if root in _DOMAIN_MAP:
                return _DOMAIN_MAP[root]
            # Fallback: capitalize root
            return root.capitalize()
    
    # Try AI enhancement before returning Unknown
    result = "Unknown"
    if use_ai_fallback:
        try:
            from .ai_parser import extract_with_ai, is_ai_available
            if is_ai_available():
                ai_result = extract_with_ai(subject, body, from_addr)
                if ai_result and ai_result.get('service'):
                    service = ai_result['service']
                    if service and service.lower() != 'unknown':
                        result = service
        except Exception:
            pass
    
    return result


def canonical_service_name(name: str) -> str:
    """Normalizes service name using aliases and known services.
    
    Args:
        name: Service name to normalize
        
    Returns:
        Canonical service name (properly capitalized)
    """
    from ..data.services import SERVICES, ALIASES
    
    n = (name or "").strip()
    if not n:
        return ""
    
    name_lower = n.lower()
    
    # Check aliases first
    if name_lower in ALIASES:
        return ALIASES[name_lower]
    
    # Exact match among known services
    for service in SERVICES.keys():
        if service.lower() == name_lower:
            return service
    
    # Partial match hint
    for service in SERVICES.keys():
        if name_lower in service.lower() or service.lower() in name_lower:
            return service
    
    # Fallback: title-case the provided name
    return n.title()


def services_equal(a: str, b: str) -> bool:
    """Checks if two service names are equivalent.
    
    Args:
        a: First service name
        b: Second service name
        
    Returns:
        True if service names are equivalent, False otherwise
    """
    return canonical_service_name(a) == canonical_service_name(b)

