"""Core business logic and models for servbot email verification system."""

from .models import Verification, EmailAccount
from .verification import (
    fetch_verification_codes,
    get_verification_for_service,
    get_latest_verification,
)

__all__ = [
    'Verification',
    'EmailAccount',
    'fetch_verification_codes',
    'get_verification_for_service',
    'get_latest_verification',
]

