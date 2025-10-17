"""
SQLite-backed local database for accounts, messages, and verifications.

- Stores provisioned email accounts (from Flashmail API or other sources)
- Stores fetched email messages and extracted verification values (codes/links)
- Optionally stores Microsoft Graph credentials
- Migrates legacy data/email.txt on first run (non-destructive)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from ..constants import DEFAULT_MESSAGE_PREVIEW_LENGTH, DEFAULT_VERIFICATION_HOURS

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "servbot.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT,
            type TEXT,               -- outlook | hotmail | other
            source TEXT,             -- flashmail | file | manual | other
            card TEXT,               -- source API card if any
            imap_server TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,        -- imap | graph
            mailbox TEXT NOT NULL,         -- the email address
            provider_msg_id TEXT NOT NULL, -- stable id per provider
            subject TEXT,
            from_addr TEXT,
            received_date TEXT,
            body_preview TEXT,
            body_html TEXT,
            body_text TEXT,
            is_read INTEGER,
            service TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, mailbox, provider_msg_id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            service TEXT,
            value TEXT,
            is_link INTEGER,               -- 0 code, 1 link
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            refresh_token TEXT,
            client_id TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_mailbox ON messages(mailbox);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_verifications_message ON verifications(message_id);")

    conn.commit()
    conn.close()


def ensure_db() -> None:
    init_db()
    migrate_email_txt_to_db()


def infer_type_from_email(email: str) -> str:
    e = (email or "").lower()
    if any(e.endswith("@" + d) for d in ("outlook.com", "live.com", "msn.com")):
        return "outlook"
    if e.endswith("@hotmail.com"):
        return "hotmail"
    return "other"


def upsert_account(*, email: str, password: str = "", type: Optional[str] = None, source: Optional[str] = None, card: Optional[str] = None, imap_server: Optional[str] = None) -> int:
    if not email:
        raise ValueError("email is required")
    acc_type = type or infer_type_from_email(email)

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO accounts(email, password, type, source, card, imap_server)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET
            password=excluded.password,
            type=COALESCE(excluded.type, accounts.type),
            source=COALESCE(excluded.source, accounts.source),
            card=COALESCE(excluded.card, accounts.card),
            imap_server=COALESCE(excluded.imap_server, accounts.imap_server)
        ;
        """,
        (email, password, acc_type, source, card, imap_server),
    )
    conn.commit()
    cur.execute("SELECT id FROM accounts WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0


def save_message(
    *,
    mailbox: str,
    provider: str,
    provider_msg_id: str,
    subject: str = "",
    from_addr: str = "",
    received_date: str = "",
    body_text: str = "",
    body_html: str = "",
    is_read: Optional[bool] = None,
    service: str = "",
) -> int:
    if not mailbox or not provider or not provider_msg_id:
        return 0
    preview = (body_text or "").strip().replace("\r", " ").replace("\n", " ")
    if len(preview) > DEFAULT_MESSAGE_PREVIEW_LENGTH:
        preview = preview[:DEFAULT_MESSAGE_PREVIEW_LENGTH]

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages(provider, mailbox, provider_msg_id, subject, from_addr, received_date, body_preview, body_html, body_text, is_read, service)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(provider, mailbox, provider_msg_id) DO UPDATE SET
            subject=excluded.subject,
            from_addr=excluded.from_addr,
            received_date=excluded.received_date,
            body_preview=excluded.body_preview,
            body_html=excluded.body_html,
            body_text=excluded.body_text,
            is_read=COALESCE(excluded.is_read, messages.is_read),
            service=excluded.service
        ;
        """,
        (
            provider,
            mailbox,
            provider_msg_id,
            subject,
            from_addr,
            received_date,
            preview,
            body_html,
            body_text,
            1 if is_read else 0 if is_read is not None else None,
            service,
        ),
    )
    conn.commit()
    cur.execute(
        "SELECT id FROM messages WHERE provider=? AND mailbox=? AND provider_msg_id=?",
        (provider, mailbox, provider_msg_id),
    )
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0


def save_verification(*, message_id: int, service: str, value: str, is_link: bool) -> int:
    if not message_id or not value:
        return 0
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO verifications(message_id, service, value, is_link) VALUES(?,?,?,?)",
        (message_id, service, value, 1 if is_link else 0),
    )
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return int(vid)


def get_graph_account() -> Optional[Dict[str, str]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT email, refresh_token, client_id FROM graph_accounts ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"email": row[0], "refresh_token": row[1], "client_id": row[2]}


def upsert_graph_account(*, email: str, refresh_token: str, client_id: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO graph_accounts(email, refresh_token, client_id)
        VALUES(?,?,?)
        ON CONFLICT(email) DO UPDATE SET
            refresh_token=excluded.refresh_token,
            client_id=excluded.client_id
        ;
        """,
        (email, refresh_token, client_id),
    )
    conn.commit()
    cur.execute("SELECT id FROM graph_accounts WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0


def migrate_email_txt_to_db() -> None:
    txt = DATA_DIR / "email.txt"
    if not txt.exists():
        return
    try:
        content = txt.read_text(errors="ignore")
    except Exception:
        return

    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        email = ""
        password = ""
        acc_type: Optional[str] = None
        refresh_token = ""
        client_id = ""
        
        # try common separators
        for sep in ("----", ":", ",", "|"):
            if sep in s:
                parts = [p.strip() for p in s.split(sep) if p.strip()]
                if len(parts) >= 2:
                    email, password = parts[0], parts[1]
                    # Check for Graph API format: email----password----refresh_token----client_id
                    if sep == "----" and len(parts) == 4:
                        refresh_token, client_id = parts[2], parts[3]
                        # Store Graph credentials
                        if refresh_token and client_id:
                            try:
                                upsert_graph_account(
                                    email=email,
                                    refresh_token=refresh_token,
                                    client_id=client_id
                                )
                            except Exception:
                                pass
                    elif len(parts) >= 3:
                        acc_type = parts[2]
                break
        if not email or not password:
            # try whitespace split
            parts = s.split()
            if len(parts) >= 2:
                email, password = parts[0], parts[1]
                if len(parts) >= 3:
                    acc_type = parts[2]
        if email and password:
            upsert_account(email=email, password=password, type=acc_type, source="file")


def get_accounts(source: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve accounts from the database, optionally filtered by source."""
    conn = _connect()
    cur = conn.cursor()
    query = "SELECT id, email, password, type, source, card, imap_server, created_at, last_seen_at FROM accounts"
    params: List[Any] = []
    if source:
        query += " WHERE source = ?"
        params.append(source)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_verifications(mailbox: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve the latest verification codes/links for a given mailbox."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.id, v.service, v.value, v.is_link, v.created_at
        FROM verifications v
        JOIN messages m ON v.message_id = m.id
        WHERE m.mailbox = ?
        ORDER BY v.created_at DESC
        LIMIT ?
        """,
        (mailbox, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def find_verification(service: str, mailbox: Optional[str] = None, since_hours: int = DEFAULT_VERIFICATION_HOURS) -> Optional[Dict[str, Any]]:
    """
    Find the latest verification for a specific service, optionally for a mailbox
    and within a certain timeframe.
    """
    conn = _connect()
    cur = conn.cursor()
    
    query = """
        SELECT v.id, v.service, v.value, v.is_link, v.created_at, m.mailbox
        FROM verifications v
        JOIN messages m ON v.message_id = m.id
        WHERE v.service LIKE ?
          AND v.created_at >= datetime('now', '-' || ? || ' hours')
    """
    params: List[Any] = [f"%{service}%", since_hours]

    if mailbox:
        query += " AND m.mailbox = ?"
        params.append(mailbox)
    
    query += " ORDER BY v.created_at DESC LIMIT 1"
    
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
