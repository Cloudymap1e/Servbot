from __future__ import annotations
import json, sqlite3
from pathlib import Path

def _db_path() -> str:
    try:
        from servbot.data import database as db  # type: ignore
        return str(db.DB_PATH)
    except Exception:
        return str(Path(__file__).resolve().parent/'data'/'servbot.db')

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def _ensure(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS event_log (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, status TEXT, service TEXT, details_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()

def log_event(event_type: str, status: str = 'info', *, service: str = '', details: dict | None = None) -> int:
    if not event_type:
        return 0
    conn = _connect(); _ensure(conn)
    c = conn.cursor()
    c.execute('INSERT INTO event_log(event_type,status,service,details_json) VALUES(?,?,?,?)', (event_type, status, service, json.dumps(details or {})))
    conn.commit(); i = c.lastrowid; conn.close(); return int(i)

def get_recent_events(limit: int = 50) -> list[dict]:
    conn = _connect(); _ensure(conn)
    c = conn.cursor(); c.execute('SELECT * FROM event_log ORDER BY created_at DESC, id DESC LIMIT ?', (int(limit),))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_event_stats() -> dict:
    conn = _connect(); _ensure(conn)
    c = conn.cursor(); c.execute('SELECT event_type, COUNT(*) FROM event_log GROUP BY event_type'); by_type = dict(c.fetchall())
    c.execute('SELECT status, COUNT(*) FROM event_log GROUP BY status'); by_status = dict(c.fetchall()); conn.close()
    return {'by_type': {k:int(v) for k,v in by_type.items()}, 'by_status': {k:int(v) for k,v in by_status.items()}}
