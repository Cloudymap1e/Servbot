"""Data management including services catalog and database operations."""

from .services import SERVICES, ALIASES
from .database import (
    ensure_db,
    upsert_account,
    save_message,
    save_verification,
    get_accounts,
    get_latest_verifications,
    find_verification,
    get_graph_account,
    upsert_graph_account,
    save_registration,
    update_registration_status,
    list_registrations,
    get_registration,
)

__all__ = [
    'SERVICES',
    'ALIASES',
    'ensure_db',
    'upsert_account',
    'save_message',
    'save_verification',
    'get_accounts',
    'get_latest_verifications',
    'find_verification',
    'get_graph_account',
    'upsert_graph_account',
    'save_registration',
    'update_registration_status',
    'list_registrations',
    'get_registration',
]

