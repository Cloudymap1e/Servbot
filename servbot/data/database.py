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
            card TEXT,               -- DEPRECATED: do not store API cards in DB
            imap_server TEXT,
            refresh_token TEXT,      -- Microsoft Graph API OAuth refresh token
            client_id TEXT,          -- Microsoft Graph API OAuth client ID
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

    # LEGACY TABLE: graph_accounts is deprecated
    # New accounts should store credentials in the accounts table
    # This table is kept for backward compatibility
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            refresh_token TEXT,      -- Microsoft Graph API OAuth refresh token
            client_id TEXT,          -- Microsoft Graph API OAuth client ID
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_mailbox ON messages(mailbox);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_verifications_message ON verifications(message_id);")

    # New table: flashmail_cards metadata (no secrets stored)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS flashmail_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT UNIQUE NOT NULL,
            storage TEXT DEFAULT 'keyring',
            last_known_balance INTEGER DEFAULT 0,
            last_checked_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_default INTEGER DEFAULT 0
        );
        """
    )

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_flashmail_cards_alias ON flashmail_cards(alias);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_flashmail_cards_default ON flashmail_cards(is_default);")

    # New table: registrations (stores service site account results and artifacts)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            website_url TEXT,
            mailbox_email TEXT NOT NULL,
            service_username TEXT,
            service_password TEXT,
            status TEXT DEFAULT 'success',
            error TEXT,
            cookies_json TEXT,
            storage_state_json TEXT,
            user_agent TEXT,
            profile_dir TEXT,
            debug_dir TEXT,
            artifacts_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_registrations_service_mailbox ON registrations(service, mailbox_email);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_registrations_created_at ON registrations(created_at);"
    )

    conn.commit()
    conn.close()


def ensure_db() -> None:
    """Ensures database is initialized and migrated."""
    init_db()
    migrate_email_txt_to_db()
    migrate_graph_accounts_to_accounts()
    migrate_normalize_flashmail_passwords()


def infer_type_from_email(email: str) -> str:
    e = (email or "").lower()
    if any(e.endswith("@" + d) for d in ("outlook.com", "live.com", "msn.com")):
        return "outlook"
    if e.endswith("@hotmail.com"):
        return "hotmail"
    return "other"


def upsert_account(
    *,
    email: str,
    password: str = "",
    type: Optional[str] = None,
    source: Optional[str] = None,
    card: Optional[str] = None,
    imap_server: Optional[str] = None,
    refresh_token: Optional[str] = None,
    client_id: Optional[str] = None,
    update_only_if_provided: bool = False,
) -> int:
    """Upsert an account into the database.
    
    Args:
        email: Email address (required, unique key)
        password: Account password
        type: Account type (outlook, hotmail, other)
        source: Source of account (flashmail, manual, file)
        card: API card/key if from provisioning service
        imap_server: IMAP server address
        refresh_token: OAuth refresh token (for Microsoft Graph)
        client_id: OAuth client ID (for Microsoft Graph)
        update_only_if_provided: If True, only update fields that are explicitly provided (not None/empty)
                                If False, all fields are updated, allowing NULL to clear values
    
    Returns:
        Account ID
    """
    if not email:
        raise ValueError("email is required")
    acc_type = type or infer_type_from_email(email)

    # Normalize Flashmail-style combined password if present: password----refresh_token----client_id
    pw = password or ""
    pw_clean = pw
    rt = refresh_token
    cid = client_id
    if "----" in pw:
        parts = [p.strip() for p in pw.split("----")]
        if len(parts) >= 1:
            pw_clean = parts[0]
        if len(parts) >= 3:
            # Only fill if not explicitly provided
            rt = rt or parts[1]
            cid = cid or parts[2]

    conn = _connect()
    cur = conn.cursor()
    
    if update_only_if_provided:
        # Legacy mode: only update non-empty values (for backward compatibility)
        cur.execute(
            """
            INSERT INTO accounts(email, password, type, source, card, imap_server, refresh_token, client_id)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
                password=CASE WHEN excluded.password != '' THEN excluded.password ELSE accounts.password END,
                type=COALESCE(excluded.type, accounts.type),
                source=COALESCE(excluded.source, accounts.source),
                card=COALESCE(excluded.card, accounts.card),
                imap_server=COALESCE(excluded.imap_server, accounts.imap_server),
                refresh_token=COALESCE(excluded.refresh_token, accounts.refresh_token),
                client_id=COALESCE(excluded.client_id, accounts.client_id)
            ;
            """,
            (email, pw_clean, acc_type, source, card, imap_server, rt, cid),
        )
    else:
        # New mode: direct update allows NULL to clear values
        cur.execute(
            """
            INSERT INTO accounts(email, password, type, source, card, imap_server, refresh_token, client_id)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
                password=excluded.password,
                type=excluded.type,
                source=excluded.source,
                card=excluded.card,
                imap_server=excluded.imap_server,
                refresh_token=excluded.refresh_token,
                client_id=excluded.client_id
            ;
            """,
            (email, pw_clean, acc_type, source, card, imap_server, rt, cid),
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
    query = "SELECT id, email, password, type, source, card, imap_server, refresh_token, client_id, created_at, last_seen_at FROM accounts"
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


def migrate_graph_accounts_to_accounts() -> None:
    """Migrates data from deprecated graph_accounts table to accounts table.
    
    This is a one-time migration for accounts that were stored in the legacy
    graph_accounts table. The credentials are moved to the main accounts table.
    
    This function is idempotent and safe to run multiple times.
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        
        # Check if graph_accounts table has any data
        cur.execute("SELECT COUNT(*) FROM graph_accounts")
        count = cur.fetchone()
        if not count or count[0] == 0:
            conn.close()
            return  # Nothing to migrate
        
        # Get all graph accounts
        cur.execute("""
            SELECT email, refresh_token, client_id, added_at
            FROM graph_accounts
            ORDER BY added_at DESC
        """)
        graph_accounts = cur.fetchall()
        
        migrated = 0
        for row in graph_accounts:
            email, refresh_token, client_id, added_at = row
            
            # Check if account already exists in accounts table
            cur.execute("SELECT id, refresh_token, client_id FROM accounts WHERE email = ?", (email,))
            existing = cur.fetchone()
            
            if existing:
                # Account exists - only update if it doesn't have Graph credentials
                if not existing[1] or not existing[2]:  # No refresh_token or client_id
                    cur.execute("""
                        UPDATE accounts
                        SET refresh_token = ?, client_id = ?
                        WHERE email = ?
                    """, (refresh_token, client_id, email))
                    migrated += 1
            else:
                # Account doesn't exist - create it with Graph credentials
                # Infer type from email domain
                acc_type = infer_type_from_email(email)
                cur.execute("""
                    INSERT INTO accounts (email, password, type, source, refresh_token, client_id)
                    VALUES (?, '', ?, 'migrated', ?, ?)
                """, (email, acc_type, refresh_token, client_id))
                migrated += 1
        
        conn.commit()
        conn.close()
        
        if migrated > 0:
            print(f"Migrated {migrated} account(s) from graph_accounts to accounts table.")
            
    except Exception as e:
        # Don't fail initialization if migration fails
        print(f"Warning: Graph accounts migration failed: {e}")
        pass


def migrate_normalize_flashmail_passwords() -> None:
    """Normalize accounts.password to store only the true password for Flashmail.

    If accounts.password contains the combined format
    "password----refresh_token----client_id", split and persist:
    - accounts.password = password
    - accounts.refresh_token = refresh_token (if empty)
    - accounts.client_id = client_id (if empty)
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT email, password, refresh_token, client_id
            FROM accounts
            WHERE password LIKE '%----%'
            """
        )
        rows = cur.fetchall()
        updated = 0
        for email, pw, rt, cid in rows:
            if not pw or '----' not in pw:
                continue
            parts = [p.strip() for p in pw.split('----')]
            pw_clean = parts[0] if parts else pw
            new_rt = rt or (parts[1] if len(parts) >= 2 else None)
            new_cid = cid or (parts[2] if len(parts) >= 3 else None)
            cur.execute(
                """
                UPDATE accounts
                SET password = ?,
                    refresh_token = COALESCE(?, refresh_token),
                    client_id = COALESCE(?, client_id)
                WHERE email = ?
                """,
                (pw_clean, new_rt, new_cid, email)
            )
            updated += 1
        conn.commit()
        conn.close()
        if updated:
            print(f"Normalized Flashmail-style passwords for {updated} account(s).")
    except Exception as e:
        # Do not fail initialization
        print(f"Warning: Flashmail password normalization failed: {e}")
        return


# Flashmail cards metadata (no secrets)

def add_flashmail_card(alias: str, storage: str = 'keyring') -> bool:
    """Add a flashmail card metadata row if not exists."""
    if not alias:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO flashmail_cards(alias, storage)
        VALUES(?, ?)
        ON CONFLICT(alias) DO UPDATE SET storage=excluded.storage
        """,
        (alias, storage),
    )
    conn.commit()
    conn.close()
    return True


def list_flashmail_cards() -> List[Dict[str, Any]]:
    """List all flashmail card aliases and metadata."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT alias, storage, last_known_balance, last_checked_at, is_default, created_at
        FROM flashmail_cards
        ORDER BY is_default DESC, alias ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_default_flashmail_card(alias: str) -> bool:
    if not alias:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE flashmail_cards SET is_default = 0")
    cur.execute("UPDATE flashmail_cards SET is_default = 1 WHERE alias = ?", (alias,))
    conn.commit()
    conn.close()
    return True


def update_flashmail_card_balance(alias: str, balance: int, checked_at: Optional[str] = None) -> bool:
    if not alias:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE flashmail_cards
        SET last_known_balance = ?,
            last_checked_at = COALESCE(?, datetime('now'))
        WHERE alias = ?
        """,
        (int(balance), checked_at, alias),
    )
    conn.commit()
    conn.close()
    return True


def remove_flashmail_card(alias: str) -> bool:
    if not alias:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM flashmail_cards WHERE alias = ?", (alias,))
    conn.commit()
    conn.close()
    return True


# Registrations table helpers

def save_registration(
    *,
    service: str,
    website_url: str = "",
    mailbox_email: str,
    service_username: str = "",
    service_password: str = "",
    status: str = "success",
    error: str = "",
    cookies_json: str = "",
    storage_state_json: str = "",
    user_agent: str = "",
    profile_dir: str = "",
    debug_dir: str = "",
    artifacts_json: str = "",
) -> int:
    if not service or not mailbox_email:
        return 0
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO registrations(
            service, website_url, mailbox_email, service_username, service_password,
            status, error, cookies_json, storage_state_json, user_agent, profile_dir,
            debug_dir, artifacts_json, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
        """,
        (
            service,
            website_url,
            mailbox_email,
            service_username,
            service_password,
            status,
            error,
            cookies_json,
            storage_state_json,
            user_agent,
            profile_dir,
            debug_dir,
            artifacts_json,
        ),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return int(rid)


def update_registration_status(registration_id: int, status: str, error: str | None = None) -> bool:
    if not registration_id or not status:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE registrations
        SET status = ?, error = COALESCE(?, error), updated_at = datetime('now')
        WHERE id = ?
        """,
        (status, error, registration_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def list_registrations(service: str | None = None, mailbox_email: str | None = None) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    q = "SELECT id, service, website_url, mailbox_email, service_username, status, created_at, updated_at FROM registrations"
    params: list[Any] = []
    wh: list[str] = []
    if service:
        wh.append("service = ?")
        params.append(service)
    if mailbox_email:
        wh.append("mailbox_email = ?")
        params.append(mailbox_email)
    if wh:
        q += " WHERE " + " AND ".join(wh)
    q += " ORDER BY created_at DESC"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_registration(service: str, mailbox_email: str) -> Optional[Dict[str, Any]]:
    if not service or not mailbox_email:
        return None
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM registrations
        WHERE service = ? AND mailbox_email = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (service, mailbox_email),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
