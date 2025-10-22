"""HTTP-based registration utilities (browserless).

Components:
- BrowserLikeSession: HTTP client that mimics a real browser (TLS + headers)
- FormParser: Minimal HTML form parser and filler
- register_http: Orchestrates signup flows using pure HTTP requests
"""

from .agent import BrowserLikeSession
from .forms import FormParser, ParsedForm
from .registrar import register_http

__all__ = [
    "BrowserLikeSession",
    "FormParser",
    "ParsedForm",
    "register_http",
]


