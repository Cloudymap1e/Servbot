"""SQL database storage for proxies."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from .models import ProxyEndpoint, ProxyType, IPVersion, RotationType


logger = logging.getLogger(__name__)


class ProxyDatabase:
    """SQLite database for storing and managing proxies."""

    def __init__(self, db_path: str = "data/proxies.db"):
        """Initialize proxy database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_database()
        logger.info(f"Proxy database initialized: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Proxies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT,
                password TEXT,
                provider TEXT,
                session TEXT,
                proxy_type TEXT,
                ip_version TEXT,
                rotation_type TEXT,
                region TEXT,
                scheme TEXT DEFAULT 'http',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(host, port, username, session)
            )
        """)

        # Proxy test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxy_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_id INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                response_time_ms REAL,
                status_code INTEGER,
                error_message TEXT,
                test_url TEXT,
                response_ip TEXT,
                tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE CASCADE
            )
        """)

        # Proxy usage stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxy_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_id INTEGER NOT NULL,
                requests_count INTEGER DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0,
                bytes_received INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE CASCADE,
                UNIQUE(proxy_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proxies_provider ON proxies(provider)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proxies_active ON proxies(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proxy_tests_proxy_id ON proxy_tests(proxy_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proxy_stats_proxy_id ON proxy_stats(proxy_id)")

        conn.commit()
        logger.debug("Database tables and indexes created/verified")

    def add_proxy(self, endpoint: ProxyEndpoint) -> int:
        """Add a proxy endpoint to database.

        Args:
            endpoint: ProxyEndpoint to add

        Returns:
            Database ID of inserted proxy
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO proxies (
                    host, port, username, password, provider, session,
                    proxy_type, ip_version, rotation_type, region, scheme
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                endpoint.host,
                endpoint.port,
                endpoint.username,
                endpoint.password,
                endpoint.provider,
                endpoint.session,
                endpoint.proxy_type.value if endpoint.proxy_type else None,
                endpoint.ip_version.value if endpoint.ip_version else None,
                endpoint.rotation_type.value if endpoint.rotation_type else None,
                endpoint.region,
                endpoint.scheme,
            ))

            conn.commit()
            proxy_id = cursor.lastrowid

            # Initialize stats
            cursor.execute("""
                INSERT INTO proxy_stats (proxy_id) VALUES (?)
            """, (proxy_id,))
            conn.commit()

            logger.info(f"Added proxy to database: {endpoint.host}:{endpoint.port} (ID: {proxy_id})")
            return proxy_id

        except sqlite3.IntegrityError:
            # Proxy already exists
            cursor.execute("""
                SELECT id FROM proxies
                WHERE host=? AND port=? AND username=? AND session=?
            """, (endpoint.host, endpoint.port, endpoint.username, endpoint.session))
            row = cursor.fetchone()
            if row:
                logger.debug(f"Proxy already exists: {endpoint.host}:{endpoint.port} (ID: {row['id']})")
                return row['id']
            raise

    def add_proxies_batch(self, endpoints: List[ProxyEndpoint]) -> List[int]:
        """Add multiple proxies in batch.

        Args:
            endpoints: List of ProxyEndpoint objects

        Returns:
            List of database IDs
        """
        logger.info(f"Adding {len(endpoints)} proxies to database")
        ids = []
        for endpoint in endpoints:
            try:
                proxy_id = self.add_proxy(endpoint)
                ids.append(proxy_id)
            except Exception as e:
                logger.error(f"Error adding proxy {endpoint.host}:{endpoint.port}: {e}")
                continue

        logger.info(f"Successfully added {len(ids)}/{len(endpoints)} proxies")
        return ids

    def get_proxy(self, proxy_id: int) -> Optional[ProxyEndpoint]:
        """Get proxy by ID.

        Args:
            proxy_id: Database ID

        Returns:
            ProxyEndpoint or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM proxies WHERE id=?", (proxy_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_endpoint(row)

    def get_all_proxies(self, active_only: bool = True) -> List[ProxyEndpoint]:
        """Get all proxies from database.

        Args:
            active_only: Only return active proxies

        Returns:
            List of ProxyEndpoint objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if active_only:
            cursor.execute("SELECT * FROM proxies WHERE is_active=1 ORDER BY id")
        else:
            cursor.execute("SELECT * FROM proxies ORDER BY id")

        rows = cursor.fetchall()
        return [self._row_to_endpoint(row) for row in rows]

    def get_proxies_by_provider(self, provider: str) -> List[ProxyEndpoint]:
        """Get proxies filtered by provider.

        Args:
            provider: Provider name

        Returns:
            List of ProxyEndpoint objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM proxies WHERE provider=? AND is_active=1 ORDER BY id
        """, (provider,))

        rows = cursor.fetchall()
        return [self._row_to_endpoint(row) for row in rows]

    def record_test_result(self, proxy_id: int, success: bool, response_time_ms: Optional[float] = None,
                          status_code: Optional[int] = None, error_message: Optional[str] = None,
                          test_url: str = "", response_ip: Optional[str] = None):
        """Record a proxy test result.

        Args:
            proxy_id: Database ID of proxy
            success: Whether test succeeded
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            error_message: Error message if failed
            test_url: URL that was tested
            response_ip: IP address from response
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO proxy_tests (
                proxy_id, success, response_time_ms, status_code,
                error_message, test_url, response_ip
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (proxy_id, success, response_time_ms, status_code,
              error_message, test_url, response_ip))

        conn.commit()
        logger.debug(f"Recorded test result for proxy {proxy_id}: success={success}")

    def update_proxy_status(self, proxy_id: int, is_active: bool):
        """Update proxy active status.

        Args:
            proxy_id: Database ID
            is_active: New active status
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE proxies SET is_active=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (is_active, proxy_id))

        conn.commit()
        logger.info(f"Updated proxy {proxy_id} status: active={is_active}")

    def get_proxy_stats(self, proxy_id: int) -> Optional[Dict]:
        """Get usage statistics for a proxy.

        Args:
            proxy_id: Database ID

        Returns:
            Dictionary with stats or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM proxy_stats WHERE proxy_id=?", (proxy_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return dict(row)

    def get_test_history(self, proxy_id: int, limit: int = 10) -> List[Dict]:
        """Get test history for a proxy.

        Args:
            proxy_id: Database ID
            limit: Max number of results

        Returns:
            List of test result dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM proxy_tests
            WHERE proxy_id=?
            ORDER BY tested_at DESC
            LIMIT ?
        """, (proxy_id, limit))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_working_proxies(self) -> List[ProxyEndpoint]:
        """Get proxies that passed their last test.

        Returns:
            List of working ProxyEndpoint objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.* FROM proxies p
            INNER JOIN (
                SELECT proxy_id, success
                FROM proxy_tests pt1
                WHERE tested_at = (
                    SELECT MAX(tested_at)
                    FROM proxy_tests pt2
                    WHERE pt2.proxy_id = pt1.proxy_id
                )
            ) latest ON p.id = latest.proxy_id
            WHERE latest.success = 1 AND p.is_active = 1
            ORDER BY p.id
        """)

        rows = cursor.fetchall()
        return [self._row_to_endpoint(row) for row in rows]

    def get_database_stats(self) -> Dict:
        """Get overall database statistics.

        Returns:
            Dictionary with stats
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}

        # Total proxies
        cursor.execute("SELECT COUNT(*) as count FROM proxies")
        stats['total_proxies'] = cursor.fetchone()['count']

        # Active proxies
        cursor.execute("SELECT COUNT(*) as count FROM proxies WHERE is_active=1")
        stats['active_proxies'] = cursor.fetchone()['count']

        # Proxies by provider
        cursor.execute("""
            SELECT provider, COUNT(*) as count
            FROM proxies
            WHERE is_active=1
            GROUP BY provider
        """)
        stats['by_provider'] = {row['provider']: row['count'] for row in cursor.fetchall()}

        # Total tests
        cursor.execute("SELECT COUNT(*) as count FROM proxy_tests")
        stats['total_tests'] = cursor.fetchone()['count']

        # Success rate
        cursor.execute("""
            SELECT
                SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successful,
                COUNT(*) as total
            FROM proxy_tests
        """)
        row = cursor.fetchone()
        if row['total'] > 0:
            stats['success_rate'] = (row['successful'] / row['total']) * 100
        else:
            stats['success_rate'] = 0.0

        return stats

    def _row_to_endpoint(self, row: sqlite3.Row) -> ProxyEndpoint:
        """Convert database row to ProxyEndpoint.

        Args:
            row: SQLite row

        Returns:
            ProxyEndpoint object
        """
        return ProxyEndpoint(
            scheme=row['scheme'],
            host=row['host'],
            port=row['port'],
            username=row['username'],
            password=row['password'],
            provider=row['provider'],
            session=row['session'],
            proxy_type=ProxyType(row['proxy_type']) if row['proxy_type'] else None,
            ip_version=IPVersion(row['ip_version']) if row['ip_version'] else None,
            rotation_type=RotationType(row['rotation_type']) if row['rotation_type'] else None,
            region=row['region'],
            metadata={'db_id': row['id'], 'is_active': bool(row['is_active'])}
        )

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
