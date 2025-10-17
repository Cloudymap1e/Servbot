"""Email message parsing utilities.

Provides functions to parse email messages and extract text content.
"""

import email
import email.message
import email.utils
import re
from typing import List, Tuple

# HTML parsing regexes
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[\t\x0b\x0c\r]+")


def html_to_text(html: str) -> str:
    """Converts HTML to plain text.
    
    Basic implementation without heavy dependencies. Removes tags and
    decodes common HTML entities.
    
    Args:
        html: HTML string to convert
        
    Returns:
        Plain text version of HTML
    """
    if not html:
        return ""
    
    # Remove script and style tags
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    
    # Remove HTML tags
    text = _TAG_RE.sub(" ", html)
    
    # Decode HTML entities
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    
    # Normalize whitespace
    text = _WS_RE.sub(" ", text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def parse_addresses(addr_header: str) -> List[str]:
    """Parses email addresses from header field.
    
    Args:
        addr_header: Email header string (e.g., from From: header)
        
    Returns:
        List of normalized email addresses (lowercase)
    """
    addrs = []
    for name, addr in email.utils.getaddresses([addr_header or ""]):
        if addr:
            addrs.append(addr.lower())
    return addrs


def domain_from_addr(addr: str) -> str:
    """Extracts domain from email address.
    
    Args:
        addr: Email address
        
    Returns:
        Domain portion (lowercase) or empty string if invalid
    """
    try:
        return addr.split("@", 1)[1].lower()
    except Exception:
        return ""


def extract_text_from_message(msg: email.message.Message) -> Tuple[str, str]:
    """Extracts text content from email message.
    
    Handles both multipart and single-part messages, extracting both
    plain text and HTML content.
    
    Args:
        msg: Email message object
        
    Returns:
        Tuple of (plain_text, html_as_text)
    """
    plain_parts: List[str] = []
    html_parts: List[str] = []
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            
            # Skip attachments
            if "attachment" in disp:
                continue
            
            if ctype in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = ""
                
                if ctype == "text/plain":
                    plain_parts.append(text)
                elif ctype == "text/html":
                    html_parts.append(text)
    else:
        # Single-part message
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
        except Exception:
            text = ""
        
        if (msg.get_content_type() or "").lower() == "text/html":
            html_parts.append(text)
        else:
            plain_parts.append(text)
    
    # Combine parts
    plain = "\n".join(p.strip() for p in plain_parts if p)
    html = "\n".join(html_to_text(h) for h in html_parts if h)
    
    return plain, html

